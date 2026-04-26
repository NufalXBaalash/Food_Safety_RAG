import os
from google import genai
from groq import Groq
from config.settings import settings
from utils.logger import logger

class LLMService:
    def __init__(self, model_name="gemini-2.5-flash"):
        api_key = getattr(settings.llm, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY'))
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")
            
        self.client = genai.Client(api_key=api_key)
        self.groq_client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        self.model_name = model_name
        logger.info(f"Initialized LLMService with model {self.model_name}")

    def classify_categories(self, prompt: str, allowed_categories: list) -> str:
        """Ask the LLM to classify the query into one of the allowed categories.
        The LLM is given a short prompt (built by Router) and should return a comma‑separated
        list of relevant categories. If the model fails, we fall back to Groq.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            # Use getattr or check for existence of .text to avoid NoneType errors
            text = getattr(response, 'text', '')
            return text.strip() if text else ""
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                logger.warning(f"Gemini error ({e}), falling back to Groq for classification")
                try:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.3-70b-versatile",
                    )
                    return chat_completion.choices[0].message.content.strip()
                except Exception as groq_e:
                    logger.error(f"Error classifying with Groq: {groq_e}")
            logger.error(f"Error classifying categories: {e}")
            return ""

    def generate(self, prompt: str) -> str:
        """Generate a response using the primary LLM (Gemini) with a fallback to Groq."""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                logger.warning(f"Gemini error ({e}), falling back to Groq for generation")
                try:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.3-70b-versatile",
                    )
                    return chat_completion.choices[0].message.content
                except Exception as groq_e:
                    logger.error(f"Error generating text from Groq: {groq_e}")
            
            logger.error(f"Error generating text from LLM: {e}")
            return "عذراً، حدث خطأ أثناء محاولة توليد الإجابة. الرجاء المحاولة مرة أخرى."
