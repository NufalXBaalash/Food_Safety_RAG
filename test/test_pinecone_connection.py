import os
import sys
# Add the project root to the python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.pinecone_service import get_pinecone_client
from config.settings import settings

def test_pinecone():
    print(f"Testing connection to index: {settings.pinecone.INDEX_NAME}")
    pc = get_pinecone_client()
    try:
        stats = pc.Index(settings.pinecone.INDEX_NAME).describe_index_stats()
        print("Successfully connected to Pinecone!")
        print(f"Index stats: {stats}")
    except Exception as e:
        print(f"Failed to connect to Pinecone: {e}")

if __name__ == "__main__":
    test_pinecone()
