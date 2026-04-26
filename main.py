import sys
import os
import argparse
from core.pipeline import Pipeline
from utils.logger import logger

# Fix encoding for Windows console if needed
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Food Safety RAG System")
    parser.add_argument("--query", type=str, help="User query to process")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve")
    args = parser.parse_args()

    # Initialize the pipeline
    pipeline = Pipeline()

    if args.query:
        query = args.query
    else:
        try:
            query = input("\n🛡️ Ask about Food Safety: ").strip()
        except EOFError:
            return

    if not query:
        print("Please enter a valid query.")
        return

    try:
        result = pipeline.run(query)
        
        print("\n" + "═"*60)
        print(" 🎯 ROUTED CATEGORIES")
        print(f" {', '.join(result['categories']) if result['categories'] else 'All (General Search)'}")
        
        print("\n 🔍 TOP CONTEXT SOURCES")
        for i, chunk in enumerate(result["context"]):
            source = chunk.get('source', 'Unknown Document')
            cluster = chunk.get('cluster', 'N/A')
            score = chunk.get('rerank_score', 0.0)
            print(f" {i+1}. [{cluster}] {source} (Score: {score:.4f})")
            
        print("\n 🤖 AI RESPONSE")
        print("─"*60)
        print(result["answer"])
        print("═"*60 + "\n")
        
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        import traceback
        traceback.print_exc()
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()