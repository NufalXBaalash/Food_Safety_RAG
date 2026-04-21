import os
from dotenv import load_dotenv

# Load all configurations from .env
load_dotenv()

class Config:
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter") # Example default
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "food-safety-index")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Create a singleton configuration instance
settings = Config()
