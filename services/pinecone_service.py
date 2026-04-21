from pinecone import Pinecone
from config.settings import settings

_pinecone_client = None

def get_pinecone_client():
    global _pinecone_client
    
    if _pinecone_client is None:
        if not settings.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY is not set in the environment.")
            
        _pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
        
    return _pinecone_client
