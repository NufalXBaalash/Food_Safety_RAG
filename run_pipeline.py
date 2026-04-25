#!/home/nothing/Code/Agentic-Testing/.venv/bin/python
"""
run_pipeline.py — Food Safety RAG Ingestion Orchestrator
=========================================================
Single entry-point that wires all five stages together.

Stages
------
  1. convert   PDF/DOCX → Markdown  (scripts/text_extraction.py)
  2. chunk     Markdown → chunks     (scripts/chunking.py)
  3. dedup     Remove near-duplicate chunks within cluster (pipeline/deduplication.py)
  4. embed     Gemini gemini-embedding-001 (pipeline/embedder.py)
  5. index     Upsert to Pinecone   (pipeline/indexer.py)

Quick-start examples
--------------------
  # Egypt (default) — full pipeline on ONE cluster:
  python run_pipeline.py --cluster "\u0627\u0644\u0634\u064a\u0643\u0648\u0644\u0627\u062a\u0629"

  # Saudi — full pipeline on ONE cluster:
  python run_pipeline.py --country saudi --cluster haccp

  # Saudi — full pipeline on ALL saudi clusters:
  python run_pipeline.py --country saudi

  # Egypt — full pipeline on ALL clusters:
  python run_pipeline.py --country egypt

  # Run only specific stages:
  python run_pipeline.py --country saudi --cluster haccp --stage convert chunk dedup embed index

  # Skip conversion (files already converted):
  python run_pipeline.py --country saudi --cluster haccp --stage chunk dedup embed index
"""

import sys
import logging
import argparse
import json
from pathlib import Path
from tqdm import tqdm

# ── resolve project root so relative imports work ─────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# NOTE: --country flag must be parsed BEFORE importing settings-dependent modules
# so we do a quick pre-parse here to mutate settings.COUNTRY in time.
def _pre_parse_country() -> str:
    """Fast pre-parse of --country before full argparse setup."""
    for i, arg in enumerate(sys.argv):
        if arg == "--country" and i + 1 < len(sys.argv):
            return sys.argv[i + 1].lower()
    return None

_early_country = _pre_parse_country()
if _early_country:
    import os
    os.environ["COUNTRY"] = _early_country

from config.settings import settings, get_raw_dir, get_markdown_dir, get_cluster_name_map  # noqa: E402
from scripts.text_extraction import convert_cluster           # noqa: E402
from scripts.download_drive import download_cluster_data        # noqa: E402
from scripts.chunking import chunk_cluster                    # noqa: E402
from pipeline.deduplication import dedup_chunks, save_dedup_report  # noqa: E402
from pipeline.embedder import embed_chunks                    # noqa: E402
from pipeline.indexer import upsert_to_pinecone, get_or_create_index  # noqa: E402

# ── paths ─────────────────────────────────────────────────────────────────────
# (drive_files.json only applies to the egypt/Drive workflow)
DRIVE_JSON = PROJECT_ROOT / "data" / "raw" / "egypt" / "drive_files.json"

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

ALL_STAGES = ["download", "convert", "chunk", "dedup", "embed", "index"]


# ─────────────────────────────────────────────────────────────────────────────
# Streaming embed + index (RAM-efficient)
# ─────────────────────────────────────────────────────────────────────────────

def _embed_and_index_streaming(
    chunks: list[dict],
    namespace: str,
    index,
    batch_size: int,
) -> dict:
    """
    Embeds and immediately indexes chunks in fixed-size batches.

    Unlike the flat embed-all → index-all approach, this function processes
    `batch_size` chunks at a time, upserts them to Pinecone, **then discards
    the vectors** before moving to the next batch.  Peak RAM is therefore
    O(batch_size) rather than O(total_chunks).

    Args:
        chunks:     Deduplicated chunk list from Stage 3.
        namespace:  Pinecone namespace (== cluster name).
        index:      Pinecone Index object (already created).
        batch_size: Number of chunks to embed + upsert per iteration.

    Returns:
        Summary dict with 'upserted' and 'errors' counts.
    """
    total          = len(chunks)
    total_upserted = 0
    total_errors   = 0
    num_batches    = (total + batch_size - 1) // batch_size

    with tqdm(
        total=total,
        desc=f"  [{namespace}] embedding",
        unit="chunk",
        dynamic_ncols=True,
        colour="green",
    ) as bar:
        for batch_num, start in enumerate(range(0, total, batch_size), 1):
            batch = chunks[start : start + batch_size]
            
            # ── embed ──────────────────────────────────────────────────────────
            embedded = embed_chunks(batch)

            # ── index ──────────────────────────────────────────────────────────
            result = upsert_to_pinecone(embedded, namespace=namespace, index=index)
            total_upserted += result.get("upserted", 0)
            total_errors   += result.get("errors",   0)

            # ── free vectors from memory immediately after upsert ──────────────
            for c in embedded:
                c.pop("vector", None)
            
            bar.update(len(batch))
            bar.set_postfix_str(f"upserted={total_upserted}", refresh=True)

    return {"upserted": total_upserted, "errors": total_errors}


# ─────────────────────────────────────────────────────────────────────────────
# Cluster discovery
# ─────────────────────────────────────────────────────────────────────────────

def _all_cluster_names() -> list[str]:
    """
    Return the ordered list of cluster names for the active country.
    For Egypt, reads order from drive_files.json.
    For Saudi (and others), scans the country's raw directory.
    """
    if settings.COUNTRY == "egypt" and DRIVE_JSON.exists():
        try:
            data = json.loads(DRIVE_JSON.read_text(encoding="utf-8"))
            return [lib["name"] for lib in data.get("libraries", [])]
        except Exception:
            pass
    # General fallback: scan disk
    raw_dir = get_raw_dir()
    if not raw_dir.exists():
        log.warning(f"Raw data directory not found: {raw_dir}")
        return []
    return sorted(
        d.name for d in raw_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-cluster pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_cluster(cluster_name: str, stages: list[str], index=None) -> dict:
    """
    Execute the requested pipeline stages for a single cluster.

    Args:
        cluster_name: Name of the cluster folder (e.g. "الشيكولاتة")
        stages:       Ordered sub-list of ALL_STAGES to execute
        index:        Shared Pinecone Index object (created once, reused across clusters)

    Returns:
        Summary dict with per-stage statistics
    """
    english_name = get_cluster_name_map().get(cluster_name, cluster_name)

    log.info(f"\n{'█'*62}")
    log.info(f"  CLUSTER: {cluster_name}  →  {english_name}")
    log.info(f"  STAGES:  {' → '.join(stages)}")
    log.info(f"{'█'*62}")

    summary: dict = {"cluster": english_name}
    chunks: list[dict] = []   # flows through chunk → dedup → embed → index

    # ── Stage 0: Download ────────────────────────────────────────────────────
    if "download" in stages:
        log.info("\n▶ Stage 0: Downloading Raw Data")
        log.info(
            f"  [DOWNLOAD] Checking/Fetching '{cluster_name}' "
            f"({settings.COUNTRY}) from Google Drive"
        )
        # For Saudi: uses data/raw/saudi/saudi_drive_files.json.
        # If the Drive URL for a cluster is empty (not yet filled in),
        # the downloader warns and returns False — pipeline continues
        # with whatever files already exist on disk.
        success = download_cluster_data(cluster_name, country=settings.COUNTRY)
        summary["download"] = "done" if success else "skipped/failed"

    # ── Stage 1: Convert ─────────────────────────────────────────────────────
    if "convert" in stages:
        log.info("\n▶ Stage 1: Markdown Conversion")
        convert_cluster(cluster_name)
        summary["convert"] = "done"

    # ── Stage 2: Chunk ───────────────────────────────────────────────────────
    if "chunk" in stages:
        log.info("\n▶ Stage 2: Chunking")
        chunks = chunk_cluster(cluster_name, display_name=english_name)
        summary["chunks_raw"] = len(chunks)

    # ── Stage 3: Deduplication ───────────────────────────────────────────────
    if "dedup" in stages:
        log.info("\n▶ Stage 3: Deduplication")
        if not chunks:
            chunks = chunk_cluster(cluster_name, display_name=english_name)
            summary["chunks_raw"] = len(chunks)

        kept, dropped_log = dedup_chunks(chunks, threshold=settings.DEDUP_THRESHOLD)
        save_dedup_report(english_name, dropped_log)

        chunks = kept
        summary["chunks_after_dedup"] = len(kept)
        summary["chunks_dropped"]     = len(dropped_log)

    # ── Stage 4 + 5 combined — streaming to keep peak RAM low ────────────────
    if "embed" in stages and "index" in stages:
        log.info("\n▶ Stages 4+5: Embedding + Pinecone Indexing (streamed)")
        if not chunks:
            log.warning("  No chunks to embed/index — run earlier stages first")
            summary["embed"] = summary["index"] = "skipped (no chunks)"
        else:
            if index is None:
                index = get_or_create_index()
            result = _embed_and_index_streaming(
                chunks,
                namespace=english_name,
                index=index,
                batch_size=settings.EMBED_BATCH_SIZE,
            )
            summary["chunks_embedded"] = result["upserted"]
            summary.update(result)

    # ── Stage 4 only (embed, save vectors in-memory for a later index run) ───
    elif "embed" in stages:
        log.info("\n▶ Stage 4: Embedding")
        if not chunks:
            log.warning("  No chunks to embed — run 'chunk' and/or 'dedup' first")
            summary["embed"] = "skipped (no chunks)"
        else:
            chunks = embed_chunks(chunks)
            summary["chunks_embedded"] = sum(1 for c in chunks if c.get("vector"))

    # ── Stage 5 only (index already-embedded chunks) ─────────────────────────
    elif "index" in stages:
        log.info("\n▶ Stage 5: Pinecone Indexing")
        if not chunks:
            log.warning("  No chunks to index — run earlier stages first")
            summary["index"] = "skipped (no chunks)"
        else:
            if index is None:
                index = get_or_create_index()
            result = upsert_to_pinecone(chunks, namespace=english_name, index=index)
            summary.update(result)

    return summary


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Food Safety RAG Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--cluster",
        nargs="+",
        metavar="NAME",
        help=(
            "Cluster folder name(s) to process. "
            "Omit to run on ALL clusters (reads order from drive_files.json)."
        ),
    )
    parser.add_argument(
        "--stage",
        nargs="+",
        metavar="STAGE",
        choices=ALL_STAGES,
        default=ALL_STAGES,
        help=(
            f"Pipeline stage(s) to execute. Choices: {ALL_STAGES}. "
            "Default: all stages. Order is always enforced (convert→chunk→dedup→embed→index)."
        ),
    )
    parser.add_argument(
        "--country",
        metavar="COUNTRY",
        default=None,
        help=(
            "Country dataset to process: 'egypt' or 'saudi'. "
            "Overrides COUNTRY in .env. Default: egypt."
        ),
    )
    args = parser.parse_args()

    # --country was already applied to os.environ via _pre_parse_country(),
    # but log the value so it's visible in every run.
    log.info(f"Country: {settings.COUNTRY.upper()}")  # shows active country

    # Enforce canonical stage ordering
    stages = [s for s in ALL_STAGES if s in args.stage]

    # Resolve cluster list
    cluster_names = args.cluster if args.cluster else _all_cluster_names()
    log.info(
        f"Pipeline starting — country={settings.COUNTRY}  "
        f"{len(cluster_names)} cluster(s), stages: {' → '.join(stages)}"
    )

    # Create Pinecone index once for all clusters (saves repeated API calls)
    index = None
    if "index" in stages:
        index = get_or_create_index()

    # ── Run ──────────────────────────────────────────────────────────────────
    all_summaries = []
    for cluster in cluster_names:
        summary = run_cluster(cluster, stages, index=index)
        all_summaries.append(summary)

    # ── Final report ─────────────────────────────────────────────────────────
    log.info(f"\n{'═'*62}")
    log.info("  PIPELINE COMPLETE — SUMMARY")
    log.info(f"{'═'*62}")
    for s in all_summaries:
        parts = [f"  {s['cluster']}"]
        if "chunks_raw"         in s: parts.append(f"raw={s['chunks_raw']}")
        if "chunks_after_dedup" in s: parts.append(f"kept={s['chunks_after_dedup']}")
        if "upserted"           in s: parts.append(f"indexed={s['upserted']}")
        log.info("  │  ".join(parts))
    log.info(f"{'═'*62}\n")


if __name__ == "__main__":
    main()
