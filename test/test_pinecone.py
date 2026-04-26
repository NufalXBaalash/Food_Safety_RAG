import os
import sys

# Add the project root to the python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from pinecone import Pinecone, ServerlessSpec
from services.pinecone_service import get_pinecone_client

pc = get_pinecone_client()

index_name = "developer-quickstart-py"

if not pc.has_index(index_name):
    pc.create_index_for_model(
        name=index_name,
        cloud="aws",
        region="us-east-1",
        embed={
            "model":"llama-text-embed-v2",
            "field_map":{"text": "chunk_text"}
        }
    )

# Wait for index to be ready
print(f"Ensuring index '{index_name}' is ready...")
index = pc.Index(index_name)

# Sample Food Safety Data
records = [
    {
        "_id": "fs-1",
        "chunk_text": "HACCP (Hazard Analysis and Critical Control Point) is a system that helps food business operators look at how they handle food and introduces procedures to make sure the food produced is safe to eat.",
        "category": "HACCP"
    },
    {
        "_id": "fs-2",
        "chunk_text": "Food allergens are proteins in foods that cause an abnormal immune response. The 14 major allergens include cereals containing gluten, crustaceans, eggs, fish, peanuts, soybeans, milk, nuts, celery, mustard, sesame seeds, sulphur dioxide and sulphites, lupin and molluscs.",
        "category": "Allergens"
    },
    {
        "_id": "fs-3",
        "chunk_text": "Proper handwashing is essential for food safety. Food handlers should wash their hands before starting work, after using the toilet, after handling raw food, and after touching their face or hair.",
        "category": "Hygiene"
    }
]

print("Upserting records...")
index.upsert_records(namespace="food-safety-test", records=records)

# Wait for indexing
import time
print("Waiting for indexing...")
time.sleep(10)

# Search
query = "How to ensure food is safe to eat using HACCP?"
print(f"\nSearching for: '{query}'")
results = index.search(
    namespace="food-safety-test",
    query={
        "top_k": 2,
        "inputs": {"text": query}
    }
)

print("\nSearch Results:")
for hit in results['result']['hits']:
    print(f"ID: {hit['_id']} | Score: {hit['_score']:.4f}")
    print(f"Text: {hit['fields']['chunk_text']}")
    print("-" * 20)