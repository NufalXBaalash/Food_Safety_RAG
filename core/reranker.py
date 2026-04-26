from sentence_transformers import CrossEncoder
from utils.logger import logger

class Reranker:
    """Re‑rank retrieved chunks using a cross‑encoder.
    The model is loaded lazily on the first call to rerank.
    """
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None

    def _load_model(self):
        if self.model is None:
            try:
                logger.info(f"Loading reranker model {self.model_name}...")
                self.model = CrossEncoder(self.model_name)
            except Exception as e:
                logger.warning(f"Failed to load reranker from Hub: {e}. Trying local-only mode.")
                try:
                    self.model = CrossEncoder(self.model_name, local_files_only=True)
                except Exception as local_e:
                    logger.error(f"Critical error: Could not load reranker model: {local_e}")
                    raise local_e

    def rerank(self, query: str, chunks: list, top_k: int = 5) -> list:
        if not chunks:
            return []
        
        self._load_model()
        
        # Prepare input pairs
        pairs = [[query, chunk["text"]] for chunk in chunks]
        scores = self.model.predict(pairs)
        # Attach scores to chunks
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)
        # Sort by rerank_score descending and keep top_k
        chunks_sorted = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
        return chunks_sorted[:top_k]