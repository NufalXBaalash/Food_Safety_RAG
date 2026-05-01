# Food Safety RAG

A Retrieval-Augmented Generation system for food safety compliance. Upload regulatory documents (PDFs, DOCX), the pipeline converts, chunks, embeds, and indexes them into Pinecone. Then query the knowledge base through a chat API that runs hybrid search (semantic + BM25) with cross-encoder reranking and LLM generation.

Supports bilingual queries (Arabic and English) with multi-country filtering.

---

## Architecture

```
User Query
    |
    v
AgentService (LLM decides: search or respond directly)
    |
    v  (if food-safety related)
RAGTool
    |
    +-- Retriever
    |     +-- Semantic (Pinecone vector search, BAAI/bge-m3 embeddings)
    |     +-- BM25 (keyword search, rank_bm25)
    |     +-- Merge & deduplicate
    |
    v
Reranker (cross-encoder/ms-marco-MiniLM-L-6-v2)
    |
    v
Generator (OpenRouter LLM with retrieved context)
    |
    v
Final Answer
```

---

## Project Structure

```
backend/
  main.py              # FastAPI app entry point
  api/
    chat.py            # POST /api/chat
    ingest.py          # POST /api/ingest, GET /api/ingest/progress

app/static/
  index.html           # Web UI (chat + file upload)

core/
  agent.py             # AgentService - decides search vs direct reply
  rag_tool.py          # RAGTool - retrieval + reranking (no LLM)
  retriever.py         # Hybrid retriever (semantic + BM25)
  reranker.py          # Cross-encoder reranker
  generator.py         # LLM answer generation (legacy pipeline)
  router.py            # LLM category router (legacy pipeline)
  pipeline.py          # Full pipeline: route > retrieve > rerank > generate (legacy)

services/
  llm_service.py       # OpenRouter LLM client
  embedding_service.py  # Local (sentence-transformers) or Gemini embeddings
  pinecone_service.py  # Pinecone query/upsert helpers

pipeline/
  deduplication.py     # TF-IDF cosine dedup on chunks
  embedder.py          # Batch embedding with disk cache
  indexer.py           # Upsert embedded chunks to Pinecone

scripts/
  text_extraction.py   # Stage 1: PDF/DOCX to Markdown (via docling)
  chunking.py          # Stage 2: Adaptive markdown chunking
  download_drive.py    # Google Drive sync for Egypt dataset

config/
  settings.py          # All config from .env, cluster maps per country

utils/
  chunking.py          # adaptive_chunk_markdown()
  hashing.py           # File hash dedup for uploads
  logger.py            # Shared logger
  markdown_conversion.py  # convert_to_markdown()

run_pipeline.py        # CLI orchestration of all ingestion stages
run_web_app.py         # Launch the web server with auto-reload
```

---

## Setup

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install fastapi uvicorn scikit-learn
```

### 2. Configure `.env`

Create a `.env` file in the project root:

```env
# Required
PINECONE_API_KEY=your_pinecone_key
OPENROUTER_API_KEY=your_openrouter_key

# Pinecone
PINECONE_INDEX_NAME=food-safety
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# LLM via OpenRouter
MODEL_NAME=openai/gpt-oss-120b:free

# Embeddings
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# Pipeline tuning
CHUNK_MIN_SIZE=300
CHUNK_MAX_SIZE=1500
CHUNK_OVERLAP=150
EMBED_BATCH_SIZE=50
COUNTRY=egypt
```

### 3. Run the server

```bash
python run_web_app.py
```

Opens at **http://localhost:8000**.

---

## API Reference

Base URL: `http://localhost:8000/api`

---

### POST `/api/ingest`

Upload documents and run the full ingestion pipeline (convert, chunk, dedup, embed, upsert to Pinecone).

**Request:** `multipart/form-data`

| Field     | Type               | Required | Description                                      |
|-----------|--------------------|----------|--------------------------------------------------|
| `files`   | `List[UploadFile]` | Yes      | PDF/DOCX files to ingest                         |
| `country` | `str`              | Yes      | Country code: `egypt`, `saudi`, etc.             |
| `cluster` | `str`              | Yes      | Cluster/category name (e.g. `haccp`, `dairy`)    |

**Example — Upload files via curl:**

```bash
curl -X POST http://localhost:8000/api/ingest \
  -F "files=@/path/to/haccp_guide.pdf" \
  -F "files=@/path/to/hygiene_standards.docx" \
  -F "country=egypt" \
  -F "cluster=haccp"
```

**Example — Upload via Python (requests):**

```python
import requests

response = requests.post(
    "http://localhost:8000/api/ingest",
    files=[
        ("files", open("haccp_guide.pdf", "rb")),
        ("files", open("hygiene_standards.docx", "rb")),
    ],
    data={
        "country": "egypt",
        "cluster": "haccp",
    }
)
print(response.json())
```

**Response (200):**

```json
{
  "message": "Ingestion processed 2 new files successfully for [EGYPT] - haccp. Skipped 0 duplicates.",
  "saved": ["haccp_guide.pdf", "hygiene_standards.docx"],
  "skipped": []
}
```

**What happens behind the scenes:**

1. Files are saved to `data/raw/{country}/{cluster}/`
2. MD5 hash dedup — duplicate files are skipped
3. Documents are converted to Markdown via docling
4. Adaptive chunking (300–1500 chars, 150 overlap)
5. Near-duplicate chunks removed (TF-IDF cosine, threshold 0.90)
6. Chunks embedded with BAAI/bge-m3 (cached to disk)
7. Vectors upserted to Pinecone under the cluster namespace

**Error (500):**

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

### GET `/api/ingest/progress`

Poll the progress of an ongoing ingestion job.

**Query Parameters:**

| Param     | Type  | Description              |
|-----------|-------|--------------------------|
| `cluster` | `str` | The cluster name to check|

**Example:**

```bash
curl "http://localhost:8000/api/ingest/progress?cluster=haccp"
```

**Response:**

```json
{
  "stage": "Embedding & Indexing",
  "file": "Pushing to Pinecone..."
}
```

Possible stages: `idle`, `Converting to Markdown`, `Chunking and enriching`, `Deduplicating Chunks`, `Embedding & Indexing`, `Complete`.

**Polling example (Python):**

```python
import requests, time

cluster = "haccp"
while True:
    r = requests.get(f"http://localhost:8000/api/ingest/progress?cluster={cluster}")
    data = r.json()
    print(f"Stage: {data['stage']} — {data['file']}")
    if data["stage"] in ("Complete", "idle"):
        break
    time.sleep(3)
```

---

### POST `/api/chat`

Ask a food safety question. The agent decides whether to search the knowledge base or respond directly (for greetings/off-topic).

**Request:** `application/json`

| Field     | Type               | Required | Default     | Description                       |
|-----------|--------------------|----------|-------------|-----------------------------------|
| `query`   | `str`              | Yes      | —           | The question (Arabic or English)  |
| `country` | `str`              | No       | `"global"`  | Filter: `egypt`, `saudi`, `global`|
| `history` | `list[ChatMessage]`| No       | `[]`        | Conversation history              |

Each `ChatMessage`: `{ "role": "user"|"assistant", "content": "..." }`

**Example — Simple question:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the temperature requirements for storing dairy products?",
    "country": "egypt"
  }'
```

**Example — With conversation history:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What about meat products?",
    "country": "egypt",
    "history": [
      {"role": "user", "content": "What are the temperature requirements for storing dairy?"},
      {"role": "assistant", "content": "Dairy products should be stored at 4°C or below..."}
    ]
  }'
```

**Example — Arabic query:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ما هي شروط تخزين الشيكولاتة؟",
    "country": "egypt"
  }'
```

**Example — Python:**

```python
import requests

response = requests.post("http://localhost:8000/api/chat", json={
    "query": "What HACCP principles apply to seafood processing?",
    "country": "saudi",
    "history": []
})
data = response.json()
print("Answer:", data["answer"])
print("Categories:", data["categories"])
print("Sources used:", len(data["context"]))
```

**Response (200):**

```json
{
  "answer": "According to the referenced food safety standards, seafood processing requires...",
  "categories": ["haccp", "fish"],
  "context": [
    {
      "id": "a1b2c3d4...",
      "text": "Seafood processing facilities must implement HACCP principles including...",
      "score": 0.89,
      "rerank_score": 0.94,
      "cluster": "haccp",
      "source": "seafood_haccp_guide.pdf",
      "country": "saudi"
    }
  ]
}
```

**Behavior details:**

- If `country` is set and returns no results, it automatically falls back to `global`
- Greetings (e.g. "hello") get a warm direct response without searching
- Off-topic questions are politely redirected to food safety
- Food safety keywords trigger a search even if the LLM doesn't explicitly request one
- The agent is bilingual — it responds in the same language as the query

---

### Static Frontend

All non-`/api` routes serve the web UI from `app/static/index.html`.

The UI has two tabs:

- **Chat Interface** — Ask questions with a country filter dropdown, view context sources and detected categories in a side panel
- **Add Knowledge Base** — Upload PDF/DOCX files with country and cluster selection, see real-time ingestion progress

---

## CLI Pipeline

For batch ingestion outside the web UI, use `run_pipeline.py`:

```bash
# Ingest one cluster for Egypt
python run_pipeline.py --country egypt --cluster "الشيكولاتة"

# Ingest one cluster for Saudi
python run_pipeline.py --country saudi --cluster haccp

# Ingest ALL clusters for a country
python run_pipeline.py --country egypt

# Run specific stages only
python run_pipeline.py --country saudi --cluster haccp --stage chunk dedup embed index

# Skip conversion (files already converted to markdown)
python run_pipeline.py --country egypt --cluster "الكيمياء" --stage chunk dedup embed index
```

**Available stages:** `download`, `convert`, `chunk`, `dedup`, `embed`, `index`

Individual scripts can also be run standalone:

```bash
# Convert PDFs to Markdown
python scripts/text_extraction.py --cluster "الشيكولاتة"

# Chunk markdown files
python scripts/chunking.py --cluster "الشيكولاتة"
```

---

## Country Cluster Maps

The system uses predefined category maps per country. These map Arabic display names to English cluster names used as Pinecone namespaces.

| Country | Available Clusters |
|---------|-------------------|
| Egypt   | `جودة الغذاء` (food-quality), `الهاسب HACCP` (haccp), `ISO الأيزو` (iso), `الميكروبيولوجي` (microbiology), `الألبان ومنتجاتها` (dairy-and-products), `الخضروات والفواكه` (vegetables-and-fruits), `التغذية` (nutrition), `المواد المضافة` (food-additives), `النظافة والتطهير` (hygiene-and-sanitation), and more |
| Saudi   | `haccp`, `iso`, `sfda`, `meat`, `dairy`, `fish`, `packaging-systems`, `allergens`, `microbiology`, `food-quality`, `hygiene-and-sanitation`, `food-analysis`, `nutrition`, `oils-and-fats`, `manufacturing`, `food-spoilage`, `general-food-safety` |
| Global  | Union of Egypt + Saudi maps |

---

## Environment Variables Reference

| Variable              | Default                  | Description                            |
|-----------------------|--------------------------|----------------------------------------|
| `PINECONE_API_KEY`    | —                        | Pinecone API key (required)            |
| `PINECONE_INDEX_NAME` | `food-safety`            | Pinecone index name                    |
| `PINECONE_CLOUD`      | `aws`                    | Pinecone cloud provider                |
| `PINECONE_REGION`     | `us-east-1`              | Pinecone region                        |
| `OPENROUTER_API_KEY`  | —                        | OpenRouter API key for LLM (required)  |
| `MODEL_NAME`          | `google/gemini-2.0-flash-001` | LLM model via OpenRouter          |
| `EMBEDDING_MODEL`     | `BAAI/bge-m3`            | Embedding model (local or Gemini name) |
| `EMBEDDING_DIMENSION` | `1024`                   | Embedding vector dimension             |
| `CHUNK_MIN_SIZE`      | `300`                    | Minimum chunk size in characters       |
| `CHUNK_MAX_SIZE`      | `1500`                   | Maximum chunk size in characters       |
| `CHUNK_OVERLAP`       | `150`                    | Overlap between chunks                 |
| `EMBED_BATCH_SIZE`    | `50`                     | Batch size for embedding               |
| `COUNTRY`             | `egypt`                  | Default country for pipeline operations|
| `DEDUP_THRESHOLD`     | `0.90`                   | Cosine similarity threshold for dedup  |

---

## Tech Stack

- **Backend**: FastAPI, Uvicorn
- **LLM**: OpenRouter (any compatible model)
- **Embeddings**: BAAI/bge-m3 (local, sentence-transformers) or Gemini
- **Vector DB**: Pinecone (serverless, cosine similarity)
- **Reranker**: cross-encoder/ms-marco-MiniLM-L-6-v2
- **BM25**: rank_bm25
- **Document Conversion**: docling (PDF/DOCX to Markdown)
- **Frontend**: Vanilla HTML/CSS/JS with Tailwind CSS
