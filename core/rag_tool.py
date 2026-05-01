from services.embedding_service import EmbeddingService
from core.retriever import Retriever
from core.reranker import Reranker
from utils.logger import logger


class RAGTool:
    def __init__(self):
        self.retriever = Retriever(EmbeddingService())
        self.reranker = Reranker()

    def search(self, query: str, country: str = "global", top_k: int = 20, rerank_k: int = 10) -> dict:
        """Search the food-safety knowledge base. No LLM calls — pure retrieval + reranking."""
        # Retrieve without category filter — search all namespaces,
        # rely on the cross-encoder reranker to surface the most relevant chunks.
        chunks = self.retriever.retrieve(query, categories=None, top_k=top_k, country=country)
        if not chunks:
            logger.info("RAGTool: no chunks retrieved")
            return {"categories": [], "context": []}

        reranked = self.reranker.rerank(query, chunks, top_k=rerank_k)
        logger.info(f"RAGTool: {len(reranked)} chunks after reranking")
        return {"categories": [], "context": reranked}
