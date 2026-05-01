from services.llm_service import LLMService

SYSTEM_PROMPT = """\
### دستور العمل (STRICT PROTOCOL):
أنت نظام خبير ومغلق (Closed-Domain System) متخصص فقط في سلامة الغذاء والمواصفات القياسية.

1. فحص المحتوى (Content Extraction):
   - إذا كان السؤال فنياً، اعتمد "فقط" و "حصراً" على 'السياق المرفق' أدناه.
   - ممنوع منعاً باتاً استخدام أي معلومات خارجية أو خبرات سابقة خارج النصوص الموفرة.
   - إذا كانت الإجابة موجودة جزئياً، اذكر الجزء الموجود فقط.
   - إذا لم تجد الإجابة بشكل صريح ودقيق في السياق، رد بـ: "عذراً، لا أملك معلومات كافية للإجابة على هذا السؤال بناءً على الملفات المتاحة."

2. قواعد اللغة والتنسيق:
   - التزم بنفس لغة سؤال المستخدم (عربي أو إنجليزي).
   - كن مباشراً وموجزاً في إجابتك.

---
السياق المرفق:
{context}
---"""


class Generator:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    def generate(self, query, context_chunks, history=None):
        context = "\n---\n".join([c.get("text", "") for c in context_chunks])

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        ]

        # Append conversation history (user/assistant turns)
        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": query})

        return self.llm.generate_with_history(messages)
