import os
from openai import OpenAI
from config.settings import settings
from utils.logger import logger


class LLMService:
    def __init__(self):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        model_name = os.environ.get("MODEL_NAME", "google/gemini-2.0-flash-001")

        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is missing")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model_name = model_name
        logger.info(f"Initialized LLMService with OpenRouter model {self.model_name}")

    def safe_chat(self, messages: list, retries: int = 2) -> str:
        """Chat completion with null-safety and retry logic for free models."""
        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                )
                content = response.choices[0].message.content
                if content and content.strip():
                    return content.strip()
                logger.warning(f"LLM returned empty content (attempt {attempt + 1}/{retries})")
            except Exception as e:
                logger.error(f"LLM call failed (attempt {attempt + 1}/{retries}): {e}")
        return ""

    # -- Legacy methods kept for backward compatibility --

    def classify_categories(self, prompt: str, allowed_categories: list) -> str:
        try:
            return self.safe_chat([{"role": "user", "content": prompt}])
        except Exception as e:
            logger.error(f"Error classifying categories: {e}")
            return ""

    def generate(self, prompt: str) -> str:
        try:
            return self.safe_chat([{"role": "user", "content": prompt}])
        except Exception as e:
            logger.error(f"Error generating text from LLM: {e}")
            return "عذراً، حدث خطأ أثناء محاولة توليد الإجابة. الرجاء المحاولة مرة أخرى."

    def generate_with_history(self, messages: list) -> str:
        try:
            return self.safe_chat(messages)
        except Exception as e:
            logger.error(f"Error generating text with history: {e}")
            return "عذراً، حدث خطأ أثناء محاولة توليد الإجابة. الرجاء المحاولة مرة أخرى."
