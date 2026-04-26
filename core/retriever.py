from services.embedding_service import EmbeddingService
from services.pinecone_service import query_pinecone, get_all_chunks
from utils.logger import logger


class SemanticRetriever:
    """Retrieve chunks from Pinecone using vector similarity.
    The caller provides an already‑embedded query vector.
    """
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding = embedding_service

    def retrieve(self, query_vector, categories: list = None, top_k: int = 5, cluster: str = None):
        logger.info(f"Retrieving semantic context for vector, categories={categories}, cluster={cluster}")
        results = query_pinecone(
            vector=query_vector,
            top_k=top_k,
            categories=categories,
            cluster=cluster,
        )
        processed = self._process_results(results)
        logger.info(f"Retrieved {len(processed)} semantic chunks")
        return processed

    def _process_results(self, results):
        cleaned = []
        for r in results:
            if not r.get("text"):
                continue
            cleaned.append({
                "id": r.get("id"),
                "text": r["text"],
                "score": r["score"],
                "cluster": r.get("cluster", "unknown"),
                "source": r.get("source", "")
            })
        cleaned.sort(key=lambda x: x["score"], reverse=True)
        return cleaned

# BM25 Retriever
class BM25Retriever:
    """Keyword BM25 retrieval over all Pinecone chunks.
    The BM25 index is built lazily on first use.
    """
    def __init__(self):
        self._bm25 = None
        self._ids = []
        self._texts = []
        self._metadata = []

    def _build_index(self):
        from rank_bm25 import BM25Okapi
        logger.info("Building BM25 index from Pinecone chunks (may take a moment)")
        chunks = get_all_chunks()
        if not chunks:
            logger.warning("No chunks found to build BM25 index.")
            self._bm25 = None
            return

        self._ids = [c["id"] for c in chunks]
        self._texts = [c["text"] for c in chunks]
        self._metadata = [{"cluster": c.get("cluster"), "source": c.get("source")} for c in chunks]
        tokenized_corpus = [doc.split() for doc in self._texts]
        self._bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"BM25 index built with {len(self._texts)} documents")

    def search(self, query: str, top_k: int = 5, categories: list = None):
        if self._bm25 is None:
            self._build_index()
        
        if self._bm25 is None:
            return []

        tokenized_query = query.split()
        scores = self._bm25.get_scores(tokenized_query)
        # Pair scores with ids and metadata
        scored_items = list(zip(self._ids, self._texts, scores, self._metadata))
        if categories:
            scored_items = [item for item in scored_items if item[3].get("cluster") in categories]
        scored_items.sort(key=lambda x: x[2], reverse=True)
        top_items = scored_items[:top_k]
        results = []
        for idx, text, score, meta in top_items:
            results.append({
                "id": idx,
                "text": text,
                "score": float(score),
                "cluster": meta.get("cluster", "unknown"),
                "source": meta.get("source", "")
            })
        logger.info(f"BM25 retrieval got {len(results)} chunks for query '{query}'")
        return results

# Helper to merge and deduplicate results from two retrievers
def merge_and_deduplicate(list_a, list_b):
    """Combine two result lists, remove duplicates by text content keeping the higher score.
    Returns a list of dicts sorted by descending score.
    """
    merged = {}  # key: text, value: item
    for item in list_a + list_b:
        text_content = item.get("text", "").strip()
        if not text_content:
            continue
            
        existing = merged.get(text_content)
        if not existing or item["score"] > existing["score"]:
            merged[text_content] = item
            
    # convert to list and sort
    result = list(merged.values())
    result.sort(key=lambda x: x["score"], reverse=True)
    return result

class Retriever:
    """Facade that runs both semantic and BM25 retrieval, merges results.
    It expects an EmbeddingService instance for the semantic part.
    """
    def __init__(self, embedding_service: EmbeddingService):
        self.semantic = SemanticRetriever(embedding_service)
        self.bm25 = BM25Retriever()

    def retrieve(self, query: str, categories: list = None, top_k: int = 5, cluster: str = None):
        # Embed query for semantic search
        query_vector = self.semantic.embedding.embed(query)
        # Retrieve from both sources
        semantic_results = self.semantic.retrieve(query_vector, categories=categories, top_k=top_k, cluster=cluster)
        bm25_results = self.bm25.search(query, top_k=top_k, categories=categories)
        # Merge & deduplicate
        merged = merge_and_deduplicate(semantic_results, bm25_results)
        return merged[:top_k]