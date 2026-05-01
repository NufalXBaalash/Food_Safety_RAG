from core.router import Router
from core.retriever import Retriever
from core.reranker import Reranker
from core.generator import Generator
from services.llm_service import LLMService
from services.embedding_service import EmbeddingService
from utils.logger import logger

GREETING_RESPONSE_AR = "أهلاً وسهلاً! 😊 أنا مساعدك الذكي المتخصص في سلامة الغذاء. يمكنني مساعدتك في المواصفات القياسية، اللوائح التنظيمية، النظافة، الهاسب (HACCP)، والأيزو وغيرها من مواضيع سلامة الغذاء. كيف يمكنني مساعدتك اليوم؟"
GREETING_RESPONSE_EN = "Hello! 😊 I'm your food safety assistant. I can help you with food standards, regulations, hygiene, HACCP, ISO, and other food safety topics. How can I help you today?"
OFF_TOPIC_RESPONSE_AR = "عذراً، أنا مساعد متخصص في سلامة الغذاء فقط. يمكنني مساعدتك في الأسئلة المتعلقة بالمواصفات القياسية، اللوائح التنظيمية، النظافة، والممارسات التصنيعية الجيدة للأغذية. هل لديك سؤال متعلق بسلامة الغذاء؟"
OFF_TOPIC_RESPONSE_EN = "Sorry, I'm a food safety assistant only. I can help with questions about food standards, regulations, hygiene, HACCP, and good manufacturing practices. Do you have a food safety question?"


class Pipeline:
    def __init__(self, router=None, retriever=None, reranker=None, generator=None):
        self.router = router or Router()
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()

        self.retriever = retriever or Retriever(self.embedding_service)
        self.reranker = reranker or Reranker()
        self.generator = generator or Generator(self.llm_service)

    def run(self, query: str, country: str = "All", history: list = None):
        logger.info(f"Pipeline started for query: {query} | Country: {country}")

        # 0. Classify query intent
        intent = self.llm_service.classify_query_intent(query, history=history)
        has_arabic = any("؀" <= c <= "ۿ" for c in query)

        if intent == "greeting":
            logger.info("Query is a greeting. Returning warm response.")
            return {
                "query": query,
                "categories": [],
                "context": [],
                "answer": GREETING_RESPONSE_AR if has_arabic else GREETING_RESPONSE_EN,
            }

        if intent == "off_topic":
            logger.info("Query is off-topic. Returning polite redirect.")
            return {
                "query": query,
                "categories": [],
                "context": [],
                "answer": OFF_TOPIC_RESPONSE_AR if has_arabic else OFF_TOPIC_RESPONSE_EN,
            }

        # 1. Route to categories
        categories = self.router.route(query)
        logger.info(f"Router selected categories: {categories}")

        # 2. Retrieve (Semantic + BM25 merged)
        retrieved_chunks = self.retriever.retrieve(
            query, categories=categories, top_k=20, country=country
        )

        # 3. Rerank
        logger.info(f"Reranking {len(retrieved_chunks)} chunks...")
        reranked_chunks = self.reranker.rerank(query, retrieved_chunks, top_k=10)

        # 4. Generate Answer
        logger.info("Generating final answer...")
        answer = self.generator.generate(query, reranked_chunks, history=history)

        logger.info("Pipeline completed successfully.")
        return {
            "query": query,
            "categories": categories,
            "context": reranked_chunks,
            "answer": answer,
        }
