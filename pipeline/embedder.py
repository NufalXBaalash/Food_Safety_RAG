"""
Stage 4 — Local Embedding
===========================
Embeds each chunk's text using sentence-transformers (BAAI/bge-m3).

Features:
  - Disk cache per chunk_id under data/embeddings/ — interrupted runs resume
  - Batching on GPU
  - Returns chunks unchanged but with an added "vector" key
"""

import sys
import time
import logging
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings

EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"

log = logging.getLogger(__name__)

# Lazy-loaded model to save RAM if skipped
_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        log.info(f"Loading embedding model: {settings.EMBEDDING_MODEL} on {settings.ACCELERATOR_DEVICE}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL, device=settings.ACCELERATOR_DEVICE)
    return _model

# ─────────────────────────────────────────────────────────────────────────────
# Cache helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cache_path(cluster: str, chunk_id: str) -> Path:
    return EMBEDDINGS_DIR / cluster / f"{chunk_id}.npy"


def _load_cached(cluster: str, chunk_id: str) -> list[float] | None:
    path = _cache_path(cluster, chunk_id)
    if path.exists():
        return np.load(str(path)).tolist()
    return None


def _save_cached(cluster: str, chunk_id: str, vector: list[float]) -> None:
    path = _cache_path(cluster, chunk_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(path), np.array(vector, dtype=np.float32))

# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed a list of chunk dicts and attach a "vector" key to each.

    Chunks with a cached embedding (data/embeddings/{cluster}/{chunk_id}.npy)
    are served from disk — no computation made.

    Args:
        chunks: List of enriched chunk dicts from Stage 2 / Stage 3.

    Returns:
        Same list, each dict now containing a "vector" key.
        Chunks whose embedding failed keep vector=None and are logged as errors.
    """
    embedded: list[dict] = []
    
    to_embed = []
    cache_hits = 0
    errors = 0
    
    for chunk in chunks:
        meta     = chunk["metadata"]
        cluster  = meta.get("cluster", "unknown")
        chunk_id = meta.get("chunk_id", "unknown_id")
        
        cached = _load_cached(cluster, chunk_id)
        if cached is not None:
            chunk["vector"] = cached
            embedded.append(chunk)
            cache_hits += 1
        else:
            to_embed.append(chunk)

    new_embeds = len(to_embed)

    if to_embed:
        model = _get_model()
        texts = [chunk["text"] for chunk in to_embed]
        
        log.info(f"  Embedding {len(texts)} chunks using {settings.EMBEDDING_MODEL} on {settings.ACCELERATOR_DEVICE} (batch size: {settings.EMBED_BATCH_SIZE})...")
        
        try:
            embeddings = model.encode(texts, batch_size=settings.EMBED_BATCH_SIZE, show_progress_bar=True)
            
            for chunk, vector in zip(to_embed, embeddings):
                norm_vector = vector.tolist()
                
                meta     = chunk["metadata"]
                cluster  = meta.get("cluster", "unknown")
                chunk_id = meta.get("chunk_id", "unknown_id")
                
                _save_cached(cluster, chunk_id, norm_vector)
                chunk["vector"] = norm_vector
                embedded.append(chunk)
                
        except Exception as exc:
            log.error(f"  [ERROR] batch embedding failed: {exc}")
            for chunk in to_embed:
                chunk["vector"] = None
                embedded.append(chunk)
            errors = len(to_embed)
            new_embeds = 0

    log.info(
        f"  Embedding complete — "
        f"new={new_embeds}  cache_hits={cache_hits}  errors={errors}"
    )
    return embedded
