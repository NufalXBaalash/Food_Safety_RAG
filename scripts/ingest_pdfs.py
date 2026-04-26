import os
import fitz  # PyMuPDF
import glob
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google import genai
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm
import time
import uuid

# Load environment variables
load_dotenv('config/.env')

PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_INDEX_NAME = os.environ.get('PINECONE_INDEX_NAME', 'rag-index')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Initialize clients
pc = Pinecone(api_key=PINECONE_API_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

EMBEDDING_MODEL = 'models/gemini-embedding-001'
EMBEDDING_DIMENSION = 3072  # gemini-embedding-001 has 3072 dims

def ensure_index():
    print(f"Checking for Pinecone index '{PINECONE_INDEX_NAME}'...")
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}' with dimension {EMBEDDING_DIMENSION}...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
        print("Waiting for index to be ready...")
        time.sleep(10)
    else:
        print(f"Index '{PINECONE_INDEX_NAME}' already exists.")

def extract_text_from_pdf(file_path):
    print("Extracting text from a PDF file...")
    doc = fitz.open(file_path)
    text_content = ""
    for page in doc:
        text_content += page.get_text("text") + "\n\n"
    return text_content

def chunk_text(text, source):
    print("Chunking text...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = splitter.split_text(text)
    return [{"text": chunk, "source": source} for chunk in chunks]

def embed_and_upload(chunks, namespace, category, batch_size=50):
    index = pc.Index(PINECONE_INDEX_NAME)
    print(f"Embedding and uploading {len(chunks)} chunks to a specific Pinecone namespace...")
    
    for i in tqdm(range(0, len(chunks), batch_size)):
        batch_chunks = chunks[i:i+batch_size]
        texts = [chunk["text"] for chunk in batch_chunks]
        
        # Embed using Gemini
        max_retries = 3
        for attempt in range(max_retries):
            try:
                res = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=texts
                )
                break
            except Exception as e:
                print(f"Error during embedding (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(30) # wait 30s before retry
                else:
                    res = None
        
        if not res:
            continue
        
        # Prepare vectors for Pinecone
        vectors = []
        for j, embedding_obj in enumerate(res.embeddings):
            chunk_metadata = {
                "text": batch_chunks[j]["text"],
                "source": batch_chunks[j]["source"],
                "category": category
            }
            # Create a deterministic ID based on text content to avoid duplicates
            import hashlib
            chunk_id = hashlib.md5(batch_chunks[j]["text"].encode('utf-8')).hexdigest()
            vectors.append((chunk_id, embedding_obj.values, chunk_metadata))
            
        # Upload to Pinecone in the specific namespace
        try:
            index.upsert(vectors=vectors, namespace=namespace)
        except Exception as e:
            print(f"Error during Pinecone upsert: {e}")

def main():
    # 1. Setup Index
    ensure_index()
    
    # 2. Read PDFs recursively
    pdf_files = glob.glob('data/**/*.pdf', recursive=True)
    
    # If no files found recursively, fall back to checking the base directory just in case
    if not pdf_files:
        pdf_files = glob.glob('data/*.pdf')

    if not pdf_files:
        print("No PDF files found in 'data/' directory.")
        return
        
    for pdf_file in pdf_files:
        source_name = os.path.basename(pdf_file)
        # Determine folder (cluster) name for namespace
        parent_dir = os.path.dirname(pdf_file)
        folder_name = os.path.basename(parent_dir)
        
        # Clean folder name to be ASCII‑safe for Pinecone
        import re
        import hashlib
        # Try to keep ASCII parts
        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', folder_name)
        if not clean_name:
            # If no ASCII chars (e.g. Arabic), use a hash of the folder name
            clean_name = "ns-" + hashlib.md5(folder_name.encode('utf-8')).hexdigest()[:8]
            
        namespace_name = re.sub(r'[\-_]+', '-', clean_name).strip('-')
        
        # Determine category based on the parent folder name (original Arabic name)
        category = folder_name
        
        if category == 'data' or not category:
            category = "عام"
        
        # Extract
        text = extract_text_from_pdf(pdf_file)
        # Chunk
        chunks = chunk_text(text, source_name)
        
        # 3. Embed & Upload to specific namespace
        if chunks:
            embed_and_upload(chunks, namespace=namespace_name, category=category, batch_size=50)
            
    print("Data ingestion with namespaces completed successfully!")

if __name__ == "__main__":
    main()
