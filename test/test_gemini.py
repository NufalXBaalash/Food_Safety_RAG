import os
import sys

# Add the project root to the python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.gemini_service import get_gemini_client

client = get_gemini_client()

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Hello, how are you?"
)

print(response.text)