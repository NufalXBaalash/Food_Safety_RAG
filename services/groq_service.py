from groq import Groq
from config.settings import settings

_groq_client = None

def get_groq_client():
    global _groq_client
    
    if _groq_client is None:
        api_key = settings.llm.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in the environment.")
            
        _groq_client = Groq(api_key=api_key)
        
    return _groq_client
