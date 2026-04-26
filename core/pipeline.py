from core.router import Router
from core.retriever import Retriever
from core.reranker import Reranker
from core.generator import Generator
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from utils.logger import logger

class Pipeline:
    def __init__(self, router=None, retriever=None, reranker=None, generator=None):
        self.router = router or Router()
        # Initialize default components if not provided
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        
        self.retriever = retriever or Retriever(self.embedding_service)
        self.reranker = reranker or Reranker()
        self.generator = generator or Generator(self.llm_service)

    def run(self, query: str):
        logger.info(f"Pipeline started for query: {query}")

        # 1. Route to categories
        categories = self.router.route(query)
        logger.info(f"Router selected categories: {categories}")

        # 2. Retrieve (Semantic + BM25 merged)
        # Note: We use categories as a filter. If multiple categories are selected, 
        # the current retriever queries all of them.
        retrieved_chunks = self.retriever.retrieve(query, categories=categories, top_k=20)
        
        # 3. Rerank
        logger.info(f"Reranking {len(retrieved_chunks)} chunks...")
        reranked_chunks = self.reranker.rerank(query, retrieved_chunks, top_k=10)
        
        # 4. Generate Answer
        logger.info("Generating final answer...")
        answer = self.generator.generate(query, reranked_chunks)

        logger.info("Pipeline completed successfully.")
        return {
            "query": query,
            "categories": categories,
            "context": reranked_chunks,
            "answer": answer
        }