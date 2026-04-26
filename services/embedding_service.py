import os
from google import genai
from config.settings import settings
from utils.logger import logger

class EmbeddingService:
    def __init__(self):
        # We assume GEMINI_API_KEY is in settings.llm or os.environ
        api_key = getattr(settings.llm, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY'))
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing")
            
        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-embedding-001"
        logger.info(f"Initialized EmbeddingService with model {self.model}")

    def embed(self, text: str) -> list:
        try:
            res = self.client.models.embed_content(
                model=self.model,
                contents=[text]
            )
            if res.embeddings and len(res.embeddings) > 0:
                return res.embeddings[0].values
            else:
                logger.error("No embeddings returned from Gemini API.")
                return []
        except Exception as e:
            logger.error(f"Error during embedding generation: {e}")
            return []
