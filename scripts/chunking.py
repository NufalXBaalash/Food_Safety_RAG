#!/home/nothing/Code/Agentic-Testing/.venv/bin/python
"""
Stage 2 — Adaptive Chunking
============================
Reads converted Markdown files from data/markdown/{cluster}/,
runs adaptive_chunk_markdown() on each, and enriches every chunk's
metadata with cluster identity, chunk index, and a stable chunk_id.

Returns a flat list of chunk dicts ready for deduplication → embedding → indexing.

Usage (standalone):
    python scripts/chunking.py --cluster "الشيكولاتة"
    python scripts/chunking.py --cluster "الشيكولاتة" "الكيمياء"
    python scripts/chunking.py          # chunks ALL clusters
"""

import sys
import os
import json
import time
import logging
import argparse
import hashlib
from pathlib import Path

# ── resolve project root ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tqdm import tqdm                                              # noqa: E402
from utils.chunking import adaptive_chunk_markdown                 # noqa: E402
from config.settings import settings, get_raw_dir, get_markdown_dir, get_cluster_name_map  # noqa: E402

# ── paths (resolved dynamically per country) ─────────────────────────────────
MANIFEST_ROOT = None  # accessed via get_markdown_dir() at call time

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _stable_chunk_id(cluster: str, source_file: str, chunk_index: int) -> str:
    """SHA-256–based stable ID that survives re-runs and file renames."""
    raw = f"{cluster}:{source_file}:{chunk_index}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def _load_cluster_meta(cluster_name: str) -> dict:
    """Load the library metadata written by download_drive.py, if present."""
    meta_path = get_raw_dir() / cluster_name / "metadata.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"name": cluster_name, "id": -1, "type": "pdf"}


def _fmt_size(path: Path) -> str:
    """Return human-readable file size string."""
    kb = path.stat().st_size / 1024
    if kb >= 1024:
        return f"{kb/1024:.1f} MB"
    return f"{kb:.0f} KB"


# ─────────────────────────────────────────────────────────────────────────────
# Core chunking logic
# ─────────────────────────────────────────────────────────────────────────────

def chunk_cluster(cluster_name: str, display_name: str | None = None) -> list[dict]:
    """
    Chunk all Markdown files that belong to one cluster.

    Enriches every chunk with:
        cluster, cluster_id, file_type, source_file (original PDF name),
        source_md (.md name), chunk_index, chunk_id

    Progress is shown via a tqdm bar with per-file size and elapsed time.

    Args:
        cluster_name: Name of the cluster folder on disk (e.g. "الشيكولاتة")
        display_name: English name used for metadata and chunk IDs
                      (defaults to cluster_name if not provided)

    Returns:
        Flat list of enriched chunk dicts — empty list if nothing to chunk.
    """
    name = display_name or cluster_name

    cluster_md = get_markdown_dir() / cluster_name
    if not cluster_md.exists():
        log.warning(f"[SKIP] No markdown directory for: {cluster_name}")
        return []

    meta       = _load_cluster_meta(cluster_name)
    cluster_id = meta.get("id", -1)
    file_type  = meta.get("type", "pdf")

    md_files = sorted(cluster_md.glob("*.md"))
    if not md_files:
        log.info(f"[EMPTY] No .md files in: {cluster_name}")
        return []

    log.info(f"\n{'═'*60}")
    log.info(f"  Chunking: {name}  ({len(md_files)} .md files)")
    log.info(f"{'═'*60}")

    all_chunks   = []
    cluster_t0   = time.perf_counter()

    # tqdm bar — one tick per .md file; postfix shows live stats
    with tqdm(
        md_files,
        desc=f"  [{name}] chunking",
        unit="file",
        dynamic_ncols=True,
        colour="cyan",
    ) as bar:
        for md_path in bar:
            file_size = _fmt_size(md_path)
            bar.set_postfix_str(f"{md_path.name[:40]}  ({file_size})", refresh=True)

            t0 = time.perf_counter()

            raw_chunks = adaptive_chunk_markdown(
                file_path=md_path,
                min_size=settings.CHUNK_MIN_SIZE,
                max_size=settings.CHUNK_MAX_SIZE,
                overlap=settings.CHUNK_OVERLAP,
            )

            elapsed = time.perf_counter() - t0

            # Filter out error/warning-only chunks
            valid = [c for c in raw_chunks if c.get("text", "").strip()]

            for idx, chunk in enumerate(valid):
                chunk_id = _stable_chunk_id(name, md_path.name, idx)
                chunk["metadata"].update({
                    "cluster":     name,
                    "cluster_id":  cluster_id,
                    "file_type":   file_type,
                    "source_file": md_path.stem + "." + file_type,
                    "source_md":   md_path.name,
                    "chunk_index": idx,
                    "chunk_id":    chunk_id,
                })

            all_chunks.extend(valid)

            # Update bar postfix to show result
            bar.set_postfix_str(
                f"{md_path.name[:30]}  ({file_size}) → {len(valid)} chunks  [{elapsed:.1f}s]",
                refresh=True,
            )
            # Also write a plain log line so it's visible in file logs
            log.debug(
                f"  {md_path.name}: {len(valid)} chunks  "
                f"size={file_size}  elapsed={elapsed:.2f}s"
            )

    total_elapsed = time.perf_counter() - cluster_t0
    log.info(
        f"  ✓ {name}: {len(all_chunks)} chunks total  "
        f"({len(md_files)} files in {total_elapsed:.1f}s)"
    )
    return all_chunks


def run_chunking(cluster_names: list[str] | None = None) -> dict[str, list[dict]]:
    """
    Run Stage 2 over one, several, or all clusters.

    Returns:
        Dict mapping cluster_name -> list of chunk dicts
    """
    if cluster_names is None:
        markdown_dir = get_markdown_dir()
        cluster_names = sorted(
            d.name for d in markdown_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        log.info(f"Auto-discovered {len(cluster_names)} clusters in data/markdown/{settings.COUNTRY}/")

    result = {}
    for cluster in cluster_names:
        english = get_cluster_name_map().get(cluster, cluster)
        result[english] = chunk_cluster(cluster, display_name=english)

    total = sum(len(v) for v in result.values())
    log.info(f"\n✅ Stage 2 complete — {total} total chunks across {len(result)} clusters")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stage 2: Chunk converted Markdown files"
    )
    parser.add_argument(
        "--cluster",
        nargs="+",
        metavar="NAME",
        help="Cluster folder name(s) to chunk. Omit to chunk all.",
    )
    args = parser.parse_args()
    results = run_chunking(args.cluster)

    # Print a brief summary
    print("\n── Chunking Summary ──────────────────────────────────────────")
    for name, chunks in results.items():
        print(f"  {name}: {len(chunks)} chunks")
