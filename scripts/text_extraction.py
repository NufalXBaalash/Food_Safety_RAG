#!/home/nothing/Code/Agentic-Testing/.venv/bin/python
"""
Stage 1 — Batch Markdown Conversion
====================================
Walks data/raw/{cluster}/ and converts every PDF / DOCX / DOC to Markdown,
writing results to data/markdown/{cluster}/{stem}.md.

Each run is fully resumable:  files that already have a .md counterpart are
skipped automatically.  Progress is persisted to data/markdown/conversion_manifest.json
after every single file so a crash mid-batch never loses work.

Usage (standalone):
    python scripts/text_extraction.py --cluster "الشيكولاتة"
    python scripts/text_extraction.py --cluster "الشيكولاتة" "الكيمياء"
    python scripts/text_extraction.py          # converts ALL clusters
"""

import sys
import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

# ── resolve project root ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.markdown_conversion import convert_to_markdown  # noqa: E402
from config.settings import get_raw_dir, get_markdown_dir  # noqa: E402

# ── paths (resolved dynamically per country) ─────────────────────────────────
MANIFEST_ROOT = PROJECT_ROOT / "data" / "markdown"

SUPPORTED_EXT = {".pdf", ".docx", ".doc"}

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Manifest helpers (append-safe, fault-tolerant)
# ─────────────────────────────────────────────────────────────────────────────

def _load_manifest() -> dict:
    manifest_path = get_markdown_dir() / "conversion_manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("Manifest corrupted — starting fresh")
    return {}


def _save_manifest(manifest: dict) -> None:
    md_dir = get_markdown_dir()
    md_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = md_dir / "conversion_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core conversion logic
# ─────────────────────────────────────────────────────────────────────────────

def convert_cluster(cluster_name: str, manifest: dict | None = None) -> dict:
    """
    Converts all supported files in data/raw/{cluster_name}/ to Markdown.

    Args:
        cluster_name: Name of the category folder (e.g. "الشيكولاتة")
        manifest:     Existing manifest dict to update in-place (loaded fresh if None)

    Returns:
        Updated manifest dict
    """
    if manifest is None:
        manifest = _load_manifest()

    raw_dir      = get_raw_dir()
    markdown_dir = get_markdown_dir()
    cluster_raw  = raw_dir / cluster_name
    cluster_md   = markdown_dir / cluster_name

    if not cluster_raw.exists():
        log.warning(f"[SKIP] Cluster directory not found: {cluster_raw}")
        return manifest

    files = [
        f for f in cluster_raw.rglob("*")
        if f.suffix.lower() in SUPPORTED_EXT and f.name != "metadata.json"
    ]

    if not files:
        log.info(f"[EMPTY] No supported files in: {cluster_name}")
        return manifest

    log.info(f"\n{'═'*60}")
    log.info(f"  Cluster: {cluster_name}  ({len(files)} files)")
    log.info(f"{'═'*60}")

    done = skipped = errors = 0

    for file_path in files:
        key      = f"{cluster_name}/{file_path.name}"
        out_path = cluster_md / f"{file_path.stem}.md"

        # ── Skip already-converted files ──────────────────────────────────────
        if out_path.exists() and manifest.get(key, {}).get("status") == "done":
            log.info(f"  [SKIP]    {file_path.name}")
            skipped += 1
            continue

        log.info(f"  [CONVERT] {file_path.name}")
        try:
            result = convert_to_markdown(file_path, cluster_md)
            manifest[key] = {
                "status":       "done",
                "output":       str(result.relative_to(PROJECT_ROOT)),
                "cluster":      cluster_name,
                "source":       str(file_path.relative_to(PROJECT_ROOT)),
                "converted_at": datetime.now(timezone.utc).isoformat(),
            }
            done += 1
        except Exception as exc:
            log.error(f"  [ERROR]   {file_path.name}: {exc}")
            manifest[key] = {
                "status":  "error",
                "cluster": cluster_name,
                "source":  str(file_path.relative_to(PROJECT_ROOT)),
                "error":   str(exc),
            }
            errors += 1

        # Save after every file — crash-safe
        _save_manifest(manifest)

    log.info(f"\n  ✓ done={done}  skipped={skipped}  errors={errors}")
    return manifest


def run_conversion(cluster_names: list[str] | None = None) -> dict:
    """
    Run Stage 1 conversion over one, several, or all clusters.

    Args:
        cluster_names: List of cluster folder names.  Pass None to process all.

    Returns:
        Final manifest dict
    """
    manifest = _load_manifest()

    if cluster_names is None:
        raw_dir = get_raw_dir()
        cluster_names = sorted(
            d.name for d in raw_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )
        log.info(f"Auto-discovered {len(cluster_names)} clusters")

    for cluster in cluster_names:
        manifest = convert_cluster(cluster, manifest)

    log.info("\n✅ Stage 1 complete")
    return manifest


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stage 1: Convert raw PDF/DOCX files to Markdown"
    )
    parser.add_argument(
        "--cluster",
        nargs="+",
        metavar="NAME",
        help="Cluster folder name(s) to process. Omit to process all clusters.",
    )
    args = parser.parse_args()
    run_conversion(args.cluster)
