import os
from config.settings import settings
from utils.logger import logger


class EmbeddingService:
    def __init__(self):
        self.model_name = settings.embedding.MODEL_NAME
        self.device = settings.ACCELERATOR_DEVICE

        if "gemini" in self.model_name.lower():
            try:
                from google import genai
            except ImportError:
                raise ImportError("google-genai is required for Gemini embeddings. Install with: pip install google-genai")

            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY is missing for Gemini embedding")
            self.client = genai.Client(api_key=api_key)
            logger.info(f"Initialized EmbeddingService with Gemini model {self.model_name}")
            self.is_local = False
        else:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading local embedding model: {self.model_name} on {self.device}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.is_local = True

    def embed(self, text: str) -> list:
        try:
            if self.is_local:
                embedding = self.model.encode(text)
                return embedding.tolist()
            else:
                res = self.client.models.embed_content(
                    model=self.model_name,
                    contents=[text],
                )
                if res.embeddings and len(res.embeddings) > 0:
                    return res.embeddings[0].values
                else:
                    logger.error(f"No embeddings returned from Gemini API for {self.model_name}")
                    return []
        except Exception as e:
            logger.error(f"Error during embedding generation: {e}")
            return []
