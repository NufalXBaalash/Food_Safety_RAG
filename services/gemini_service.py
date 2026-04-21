from google import genai
from config.settings import settings

_gemini_client = None

def get_gemini_client():
    """Initializes and returns the Gemini client."""
    global _gemini_client
    
    if _gemini_client is None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in the environment.")
        
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
    return _gemini_client
