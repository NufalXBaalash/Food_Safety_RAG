from services.llm_service import LLMService

class Generator:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    def generate(self, query, context_chunks):
        # We assume context_chunks is a list of dicts with a 'text' key
        context = "\n---\n".join([c.get("text", "") for c in context_chunks])

        prompt = f"""أنت مساعد ذكي ومتخصص في سلامة الغذاء والمواصفات القياسية.
مهمتك هي الإجابة على سؤال المستخدم بناءً على السياق المرفق. 
حاول استخلاص الإجابة الأدق من النصوص المتاحة. 
إذا كان السياق لا يحتوي على الإجابة إطلاقاً، قل "عذراً، لا أملك معلومات كافية للإجابة على هذا السؤال بناءً على الملفات المتاحة."
السياق:
{context}

السؤال:
{query}

الإجابة:
"""

        return self.llm.generate(prompt)