import os
import sys

# Add the project root to the python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.pipeline import Pipeline
from config.settings import settings
from utils.logger import logger

def main():
    # Fix for Windows console encoding
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    logger.info("Starting Pipeline End-to-End Test")
    
    # Initialize the pipeline
    pipeline = Pipeline()
    
    # Sample Query
    query = "ما هي شروط تخزين الشيكولاتة لضمان سلامتها؟"
    
    logger.info(f"Running pipeline for query: {query}")
    
    try:
        result = pipeline.run(query)
        
        output = []
        output.append("\n" + "="*50)
        output.append(f"QUERY: {result['query']}")
        output.append(f"ROUTED CATEGORIES: {result['categories']}")
        output.append(f"CONTEXT CHUNKS: {len(result['context'])}")
        output.append("-" * 50)
        output.append(f"ANSWER:\n{result['answer']}")
        output.append("="*50 + "\n")
        
        final_output = "\n".join(output)
        print(final_output)
        
        # Save to file for inspection
        with open("test_output/pipeline_result.txt", "w", encoding="utf-8") as f:
            f.write(final_output)
        logger.info("Result saved to test_output/pipeline_result.txt")
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
