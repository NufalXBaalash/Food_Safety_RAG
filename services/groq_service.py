from groq import Groq
from config.settings import settings

_groq_client = None

def get_groq_client():
    global _groq_client
    
    if _groq_client is None:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in the environment.")
            
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
        
    return _groq_client
