import sys
import os
from core.pipeline import Pipeline
from utils.logger import logger

# Fix encoding for Windows console if needed
if os.name == 'nt':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    # Initialize the pipeline
    # The new Pipeline class handles the instantiation of its components
    pipeline = Pipeline()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Ask: ")

    if not query.strip():
        print("Please enter a valid query.")
        return

    try:
        result = pipeline.run(query)
        
        print("\n" + "="*50)
        print("--- CATEGORIES DETECTED ---")
        print(result["categories"] if result["categories"] else "All (General)")
        
        print("\n--- TOP CONTEXT SOURCES ---")
        for i, chunk in enumerate(result["context"]):
            print(f"{i+1}. [{chunk['category']}] {chunk['source']} (Score: {chunk.get('rerank_score', 'N/A'):.4f})")
            
        print("\n--- ANSWER ---")
        print(result["answer"])
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()