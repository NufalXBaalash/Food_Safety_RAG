from google import genai
from config.settings import settings

_gemini_client = None

def get_gemini_client():
    """Initializes and returns the Gemini client."""
    global _gemini_client
    
    if _gemini_client is None:
        api_key = settings.llm.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in the environment.")
        
        _gemini_client = genai.Client(api_key=api_key)
        
    return _gemini_client
