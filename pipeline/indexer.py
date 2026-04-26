"""
Stage 5 — Pinecone Indexing
============================
Upserts embedded chunks into the Pinecone index, one namespace per cluster.

Features:
  - Creates the index (serverless, aws/eu-west-1, cosine, 768-dim) if absent
  - Batches upserts in groups of 100 vectors (Pinecone recommended maximum)
  - Skips chunks whose vector is None (embedding failed at Stage 4)
  - Stores the chunk text + key metadata in each vector's metadata dict
    so retrieval can return context without a secondary lookup
"""

import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pinecone import ServerlessSpec          # noqa: E402
from config.settings import settings          # noqa: E402
from services import get_pinecone_client      # noqa: E402

log = logging.getLogger(__name__)

_UPSERT_BATCH = 100          # Pinecone recommended batch size
_MAX_METADATA_CHARS = 10_000  # Pinecone metadata value size cap (safety trim)


# ─────────────────────────────────────────────────────────────────────────────
# Index management
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_index():
    """
    Return a ready Pinecone Index object, creating it first if it doesn't exist.

    Index spec:
        name:      settings.PINECONE_INDEX_NAME  (default: "Food-Safety")
        metric:    cosine
        dimension: settings.EMBEDDING_DIMENSION  (default: 768)
        cloud:     aws
        region:    eu-west-1
    """
    pc = get_pinecone_client()

    existing = [idx.name for idx in pc.list_indexes()]
    if settings.PINECONE_INDEX_NAME not in existing:
        log.info(
            f"Creating Pinecone index '{settings.PINECONE_INDEX_NAME}' "
            f"({settings.PINECONE_CLOUD}/{settings.PINECONE_REGION}, "
            f"dim={settings.EMBEDDING_DIMENSION}, metric=cosine) …"
        )
        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=settings.EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.PINECONE_CLOUD,
                region=settings.PINECONE_REGION,
            ),
        )
        log.info("Index created ✓")
    else:
        log.info(f"Using existing index '{settings.PINECONE_INDEX_NAME}'")

    return pc.Index(settings.PINECONE_INDEX_NAME)


# ─────────────────────────────────────────────────────────────────────────────
# Metadata preparation
# ─────────────────────────────────────────────────────────────────────────────

def _build_pinecone_meta(chunk: dict) -> dict:
    """
    Extract the fields we want stored alongside each vector in Pinecone.
    Stored metadata enables filtered queries (e.g. "only HACCP documents").
    """
    meta = chunk.get("metadata", {})
    text = chunk.get("text", "")

    return {
        "text":        text[:_MAX_METADATA_CHARS],  # stored for context retrieval
        "source_file": meta.get("source_file", ""),
        "source_md":   meta.get("source_md", ""),
        "cluster":     meta.get("cluster", ""),
        "cluster_id":  meta.get("cluster_id", -1),
        "header":      meta.get("header", "Root"),
        "chunk_type":  meta.get("chunk_type", ""),
        "file_type":   meta.get("file_type", ""),
        "chunk_index": meta.get("chunk_index", 0),
        "size":        meta.get("size", 0),
        "country":     settings.COUNTRY,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def upsert_to_pinecone(
    chunks: list[dict],
    namespace: str,
    index=None,
) -> dict:
    """
    Upsert a list of embedded chunk dicts into the Pinecone index.

    Args:
        chunks:    Chunks produced by Stage 4 (each must have a "vector" key).
        namespace: Pinecone namespace — use the cluster name for clean separation.
        index:     Optional pre-fetched Pinecone Index object.
                   Created automatically if not provided.

    Returns:
        Summary dict {"upserted": int, "skipped_no_vector": int}
    """
    if index is None:
        index = get_or_create_index()

    # Filter out failed embeddings
    valid   = [c for c in chunks if c.get("vector")]
    skipped = len(chunks) - len(valid)
    if skipped:
        log.warning(f"  Skipping {skipped} chunks with no vector")

    if not valid:
        log.warning("  No valid vectors to upsert")
        return {"upserted": 0, "skipped_no_vector": skipped}

    # Batch upsert
    total_upserted = 0
    for batch_start in range(0, len(valid), _UPSERT_BATCH):
        batch = valid[batch_start: batch_start + _UPSERT_BATCH]
        vectors = [
            {
                "id":       chunk["metadata"]["chunk_id"],
                "values":   chunk["vector"],
                "metadata": _build_pinecone_meta(chunk),
            }
            for chunk in batch
        ]
        index.upsert(vectors=vectors, namespace=namespace)
        total_upserted += len(vectors)
        log.info(
            f"  Upserted batch {batch_start // _UPSERT_BATCH + 1} "
            f"({total_upserted}/{len(valid)} vectors)"
        )

    log.info(
        f"  ✓ Pinecone upsert complete — "
        f"namespace='{namespace}'  upserted={total_upserted}  skipped={skipped}"
    )
    return {"upserted": total_upserted, "skipped_no_vector": skipped}
