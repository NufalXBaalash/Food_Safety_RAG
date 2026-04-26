"""
Stage 3 — Chunk-Level Cosine Similarity Deduplication
=======================================================
Within each cluster, removes chunks whose text is ≥ DEDUP_THRESHOLD (default 0.90)
similar to an already-kept chunk, using TF-IDF with character n-grams.

Character n-grams (3–5) are language-agnostic and work naturally on Arabic text
without any tokenisation step.

The deduplication report is appended to data/dedup_report.json so you can
inspect exactly which chunks were dropped and why.
"""

import json
import logging
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEDUP_REPORT = PROJECT_ROOT / "data" / "dedup_report.json"

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Core dedup logic
# ─────────────────────────────────────────────────────────────────────────────

def dedup_chunks(
    chunks: list[dict],
    threshold: float = 0.90,
) -> tuple[list[dict], list[dict]]:
    """
    Remove near-duplicate chunks from a cluster's chunk list.

    Algorithm:
        1. Vectorise all chunk texts with TF-IDF char n-grams (3–5).
        2. Compute pairwise cosine similarity matrix.
        3. Greedy pass: for each pair (i, j) where sim > threshold and
           j has not already been dropped, mark j as duplicate of i.
           (i is always encountered first, so the earlier/longer chunk wins.)

    Args:
        chunks:    List of chunk dicts (output of Stage 2).
        threshold: Cosine similarity above which a chunk is considered duplicate.

    Returns:
        (kept_chunks, dropped_log)
        dropped_log is a list of dicts describing each dropped chunk.
    """
    if len(chunks) < 2:
        return chunks, []

    texts = [c["text"] for c in chunks]

    try:
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",   # character n-grams within word boundaries
            ngram_range=(3, 5),
            max_features=15_000,
            sublinear_tf=True,    # log(1 + tf) — smooths high-frequency terms
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError as exc:
        log.warning(f"TF-IDF vectorisation failed ({exc}); skipping dedup")
        return chunks, []

    sim_matrix = cosine_similarity(tfidf_matrix)
    np.fill_diagonal(sim_matrix, 0.0)  # mask self-similarity

    dropped_indices: set[int] = set()
    dropped_log: list[dict] = []

    # ── Greedy pass with progress bar ──────────────────────────────────────────
    # The sim_matrix is N x N. We only care about the upper triangle (j > i).
    # For large clusters (5000+ chunks), the N^2 check is slow in Python,
    # so we add a tqdm bar to provide feedback.
    with tqdm(
        total=len(chunks),
        desc=f"  [{chunks[0]['metadata'].get('cluster', 'dedup')}] dedup",
        unit="chunk",
        leave=False,
        dynamic_ncols=True,
    ) as bar:
        for i in range(len(chunks)):
            bar.update(1)
            if i in dropped_indices:
                continue
            
            # Find all chunks j > i that are similar to i
            # Vectorized check for siblings of i
            similar_to_i = np.where(sim_matrix[i, i+1:] >= threshold)[0]
            
            for rel_j in similar_to_i:
                j = i + 1 + rel_j
                if j in dropped_indices:
                    continue
                
                score = float(sim_matrix[i, j])
                dropped_indices.add(j)
                dropped_log.append({
                    "dropped_chunk_id":  chunks[j]["metadata"].get("chunk_id", str(j)),
                    "dropped_source":    chunks[j]["metadata"].get("source_file", ""),
                    "dropped_index":     chunks[j]["metadata"].get("chunk_index", j),
                    "kept_chunk_id":     chunks[i]["metadata"].get("chunk_id", str(i)),
                    "kept_source":       chunks[i]["metadata"].get("source_file", ""),
                    "similarity":        round(score, 4),
                })

    kept = [c for idx, c in enumerate(chunks) if idx not in dropped_indices]
    dropped = [chunks[idx] for idx in dropped_indices]  # noqa: F841 (available if caller needs it)

    log.info(
        f"  Dedup: {len(chunks)} → {len(kept)} chunks "
        f"({len(dropped_indices)} duplicates removed at threshold={threshold})"
    )
    return kept, dropped_log


# ─────────────────────────────────────────────────────────────────────────────
# Report persistence
# ─────────────────────────────────────────────────────────────────────────────

def save_dedup_report(cluster_name: str, dropped_log: list[dict]) -> None:
    """Append this cluster's dedup results to data/dedup_report.json."""
    if not dropped_log:
        return

    report: dict = {}
    if DEDUP_REPORT.exists():
        try:
            report = json.loads(DEDUP_REPORT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = {}

    report[cluster_name] = {
        "dropped_count": len(dropped_log),
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "entries":       dropped_log,
    }

    DEDUP_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DEDUP_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info(f"  Dedup report updated → data/dedup_report.json")
