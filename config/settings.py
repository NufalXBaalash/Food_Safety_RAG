import os
from dotenv import load_dotenv

# Load env variables
load_dotenv('config/.env')


class BaseConfig:
    ENV = os.getenv("ENV", "dev")



class PineconeConfig:
    API_KEY = os.getenv("PINECONE_API_KEY")
    ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
    INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "rag-index")
    DIMENSION = int(os.getenv("PINECONE_DIMENSION", 3072))

    @classmethod
    def validate(cls):
        if not cls.API_KEY:
            raise ValueError("❌ PINECONE_API_KEY is missing")


class LLMConfig:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5")

    @classmethod
    def validate(cls):
        if not (cls.GROQ_API_KEY or cls.GEMINI_API_KEY):
            print("⚠️ No external LLM API key found, assuming local Ollama")



class RetrievalConfig:
    TOP_K = int(os.getenv("TOP_K", 5))
    RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", 3))
    USE_HYBRID = os.getenv("USE_HYBRID", "false").lower() == "true"


class EmbeddingConfig:
    MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")



class Settings:
    def __init__(self):
        self.base = BaseConfig
        self.pinecone = PineconeConfig
        self.llm = LLMConfig
        self.retrieval = RetrievalConfig
        self.embedding = EmbeddingConfig

    def validate(self):
        self.pinecone.validate()
        self.llm.validate()


# Singleton
settings = Settings()

# Validate on startup
settings.validate()