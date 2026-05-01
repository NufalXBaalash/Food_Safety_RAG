import re
from services.llm_service import LLMService
from core.rag_tool import RAGTool
from config.settings import settings
from utils.logger import logger

AGENT_SYSTEM_PROMPT = """\
You are a friendly food safety expert assistant. You help users with questions about \
food safety standards, regulations, hygiene, HACCP, ISO, food microbiology, food chemistry, \
food packaging, food preservation, food contamination, nutrition, and related topics.

## Rules:
1. ALWAYS respond in the same language as the user's message (Arabic or English).
2. For greetings and small talk: Respond warmly and naturally, then mention you can help with food safety topics.
3. For off-topic questions (not related to food safety at all): Politely redirect to food safety topics.
4. For follow-up questions about previous messages: Use the conversation history to understand context and answer.
5. For food safety questions: You MUST search the knowledge base by outputting exactly: [SEARCH: your search query]
6. When answering with search results, base your answer ONLY on the provided context. \
If the context doesn't contain the answer, say so honestly.
7. Be direct and concise.

IMPORTANT: You must output [SEARCH: query] on its own line when you need to search. \
Do NOT include any other text with the search command."""

GENERATION_SYSTEM_PROMPT = """\
You are a food safety expert assistant. Answer the user's question based ONLY on the \
context provided below. If the context doesn't contain enough information, say so honestly.

Rules:
- Respond in the same language as the user's message.
- Be direct and concise.
- Base your answer ONLY on the context below. Do not use outside knowledge.

---
Context:
{context}
---"""

# Keywords that indicate the query is likely food-safety related,
# used as a fallback when the model doesn't output [SEARCH: ...]
FOOD_SAFETY_KEYWORDS = {
    # Arabic
    "غذاء", "غذائية", "سلامة", "صحي", "صحة", "تلوث", "بكتيريا", "ميكروب",
    "حفظ", "تخزين", "تعبئة", "تغليف", "تصنيع", "نظافة", "تطهير", "تعقيم",
    "مضاف", "مواد", "حساسية", "تسمم", "فساد", "صلاحية", "انتهاء",
    "هاسب", "haccp", "أيزو", "iso", "كودكس", "codex",
    "شوكولات", "شيكولات", "لبن", "ألبان", "لحم", "سمك", "زيت", "دهون",
    "خضار", "فواكه", "حبوب", "مكسرات", "بقول", "سكر", "ملح",
    "مطعم", "فندق", "مطبخ", "مصنع", "معمل",
    "عينة", "فحص", "تحليل", "رقابة", "تفتيش", "رصد",
    "معايير", "مواصفات", "لوائح", "تنظيم", "قانون", "اشتراطات",
    # English
    "food", "safety", "haccp", "iso", "hygiene", "sanitation",
    "contamination", "microbiology", "pathogen", "bacteria",
    "preservation", "storage", "packaging", "additives", "allergen",
    "spoilage", "shelf", "expiry", "nutrition", "dairy", "meat",
    "fish", "oil", "fat", "sugar", "salt", "chocolate",
    "restaurant", "kitchen", "factory", "inspection", "regulation",
    "standard", "codex", "gmp", " prerequisite",
}


class AgentService:
    def __init__(self):
        self.llm = LLMService()
        self.rag = RAGTool()

    def chat(self, query: str, country: str = "global", history: list = None) -> dict:
        """Main entry point. Returns {answer, categories, context}."""
        logger.info(f"Agent received query: {query} | Country: {country}")

        history = history or []
        messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": query})

        # 1st LLM call — agent decides whether to search or respond directly
        response_text = self.llm.safe_chat(messages)
        if not response_text:
            return self._fallback_response(query)

        # Check if the agent wants to search
        search_query = self._parse_search(response_text)

        # Keyword fallback: if model didn't trigger search but query looks food-safety related
        if not search_query and self._looks_like_food_safety(query):
            logger.info("Keyword fallback triggered — forcing RAG search")
            search_query = query

        if search_query:
            return self._handle_search(search_query, query, country, messages, response_text)

        # No search needed — return the agent's direct response
        logger.info("Agent responded directly (greeting/off-topic/follow-up)")
        return {"answer": response_text, "categories": [], "context": []}

    def _handle_search(self, search_query: str, original_query: str,
                       country: str, messages: list, first_response: str) -> dict:
        """Execute RAG search and generate answer from context."""
        logger.info(f"Agent searching for: {search_query}")

        # Run RAG tool (retriever + reranker, no LLM)
        rag_result = self.rag.search(search_query, country=country)
        context_chunks = rag_result["context"]

        if not context_chunks:
            logger.info("RAG returned no results — answering without context")
            # Try with just the original query
            if search_query != original_query:
                rag_result = self.rag.search(original_query, country=country)
                context_chunks = rag_result["context"]

        # Build context text for the generation prompt
        context_text = "\n---\n".join(c.get("text", "") for c in context_chunks)

        # 2nd LLM call — generate answer from retrieved context
        gen_messages = [
            {"role": "system", "content": GENERATION_SYSTEM_PROMPT.format(context=context_text)},
        ]
        # Include history for follow-up context
        for m in messages[1:]:  # Skip the agent system prompt
            if m["role"] in ("user", "assistant"):
                gen_messages.append({"role": m["role"], "content": m["content"]})
        # Replace last user message with the original query
        if gen_messages[-1]["role"] == "user":
            gen_messages[-1]["content"] = original_query

        answer = self.llm.safe_chat(gen_messages)
        if not answer:
            answer = "عذراً، لم أتمكن من توليد إجابة. يرجى المحاولة مرة أخرى."

        # Extract categories from context chunks
        categories = list(dict.fromkeys(
            c.get("cluster", "") for c in context_chunks if c.get("cluster")
        ))

        return {"answer": answer, "categories": categories, "context": context_chunks}

    def _parse_search(self, text: str) -> str | None:
        """Extract search query from [SEARCH: ...] pattern. Returns None if not found."""
        match = re.search(r'\[SEARCH:\s*(.+?)\]', text)
        if match:
            return match.group(1).strip()
        return None

    def _looks_like_food_safety(self, query: str) -> bool:
        """Check if query contains food-safety related keywords."""
        query_lower = query.lower()
        return any(kw in query_lower for kw in FOOD_SAFETY_KEYWORDS)

    def _fallback_response(self, query: str) -> dict:
        has_arabic = any("؀" <= c <= "ۿ" for c in query)
        answer = (
            "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى."
            if has_arabic
            else "Sorry, an error occurred. Please try again."
        )
        return {"answer": answer, "categories": [], "context": []}
