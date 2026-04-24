# Food Safety RAG — Ingestion Pipeline

A complete, resumable data ingestion pipeline that converts **2,380 food-safety documents across 32 Arabic/English topic clusters** into semantically chunked, deduplicated, and embedded vectors stored in Pinecone for Retrieval-Augmented Generation.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Project Structure](#project-structure)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Pipeline](#running-the-pipeline)
   - [Single Cluster (recommended first run)](#single-cluster)
   - [Multiple Clusters](#multiple-clusters)
   - [All Clusters](#all-clusters)
   - [Individual Stages](#individual-stages)
6. [Pipeline Stages](#pipeline-stages)
7. [Data Clusters](#data-clusters)
8. [Output Files](#output-files)
9. [Pinecone Structure](#pinecone-structure)
10. [Customising the Pipeline](#customising-the-pipeline)

---

## Architecture

```
data/raw/{cluster}/          ← Source PDFs / DOCX files (downloaded via download_drive.py)
        │
        ▼  Stage 1 — text_extraction.py
data/markdown/{cluster}/     ← OCR-converted Markdown files  (Docling + CUDA)
        │
        ▼  Stage 2 — chunking.py
        └─ List of chunk dicts  (adaptive, structure-aware splitting)
                │
                ▼  Stage 3 — pipeline/deduplication.py
                └─ Deduplicated chunks  (TF-IDF char n-gram cosine sim > 0.90 → drop)
                        │
                        ▼  Stage 4 — pipeline/embedder.py
                        └─ Chunks + 768-dim vectors  (Gemini text-embedding-004)
                                │
                                ▼  Stage 5 — pipeline/indexer.py
                                └─ Pinecone index "Food-Safety"  (one namespace / cluster)
```

Every stage is **independently resumable**:
- Markdown conversion skips files that already have a `.md` counterpart.
- Embedding skips chunks whose vector is cached at `data/embeddings/`.
- Chunking / dedup always re-run (fast, pure Python, no API calls).

---

## Project Structure

```
Food_Safety_RAG/
├── config/
│   └── settings.py             Central config — reads from .env
│
├── data/
│   ├── raw/                    Raw source files (33 cluster dirs downloaded from Drive)
│   │   └── drive_files.json    Cluster manifest (names, Drive URLs, file counts)
│   ├── markdown/               Stage 1 output: .md files
│   │   └── conversion_manifest.json  Per-file conversion log (crash-safe)
│   ├── embeddings/             Stage 4 cache: {cluster}/{chunk_id}.npy
│   └── dedup_report.json       Stage 3 report: which chunks were dropped and why
│
├── pipeline/
│   ├── deduplication.py        Stage 3 — chunk-level cosine dedup
│   ├── embedder.py             Stage 4 — Gemini text-embedding-004
│   └── indexer.py              Stage 5 — Pinecone upsert
│
├── scripts/
│   ├── download_drive.py       One-time download from Google Drive
│   ├── text_extraction.py      Stage 1 — batch Markdown conversion
│   └── chunking.py             Stage 2 — adaptive chunking
│
├── services/
│   ├── gemini_service.py       Gemini client singleton
│   ├── groq_service.py         Groq client singleton
│   └── pinecone_service.py     Pinecone client singleton
│
├── utils/
│   ├── markdown_conversion.py  Docling-powered PDF/DOCX → Markdown converter
│   └── chunking.py             adaptive_chunk_markdown() — structure-aware chunker
│
├── run_pipeline.py             ← Main entry-point (CLI orchestrator)
├── requirements.txt
└── .env
```

---

## Installation

```bash
# Activate the shared virtual environment
source /home/nothing/Code/Agentic-Testing/.venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

> **First-time only** — `wordsegment` needs its corpus downloaded after install:
> ```python
> python -c "from wordsegment import load; load()"
> ```

---

## Configuration

All settings live in `.env` at the project root. The file already has production values filled in:

```dotenv
# Pinecone
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=Food-Safety
PINECONE_CLOUD=aws
PINECONE_REGION=eu-west-1

# AI
GEMINI_API_KEY=...
GROQ_API_KEY=...

# Pipeline tuning (optional — defaults shown)
EMBEDDING_MODEL=models/text-embedding-004
EMBEDDING_DIMENSION=768
DEDUP_THRESHOLD=0.90        # cosine similarity above which a chunk is dropped
CHUNK_MIN_SIZE=300           # min chars before a header triggers a new chunk
CHUNK_MAX_SIZE=1500          # target max chunk size in characters
CHUNK_OVERLAP=150            # chars shared between consecutive chunks
```

---

## Running the Pipeline

All commands are run from the **project root** with the venv active.

### Single Cluster

Run the full 5-stage pipeline on one cluster. **Always start here** to validate the setup before processing hundreds of GBs.

```bash
python run_pipeline.py --cluster "الشيكولاتة"
```

Replace `"الشيكولاتة"` with any cluster name from the [Data Clusters](#data-clusters) table.

### Multiple Clusters

```bash
python run_pipeline.py --cluster "الشيكولاتة" "الكيمياء" "الميكروبيولوجي"
```

### All Clusters

Processes all 32 clusters in the order defined in `data/raw/drive_files.json`.

```bash
python run_pipeline.py
```

> This is a long-running job (~2,380 files). Interrupted runs are safe to restart — every stage skips already-completed work.

---

### Individual Stages

You can run any subset of stages in isolation. The stage execution order is always enforced (`convert → chunk → dedup → embed → index`).

**Stage 1 only — convert raw files to Markdown:**
```bash
python scripts/text_extraction.py --cluster "الشيكولاتة"
# or via orchestrator:
python run_pipeline.py --cluster "الشيكولاتة" --stage convert
```

**Stage 2 only — chunk already-converted files:**
```bash
python scripts/chunking.py --cluster "الشيكولاتة"
# or via orchestrator:
python run_pipeline.py --cluster "الشيكولاتة" --stage chunk
```

**Stages 3+4+5 — dedup, embed, and index (skip conversion):**
```bash
python run_pipeline.py --cluster "الشيكولاتة" --stage dedup embed index
```

**Stage 5 only — re-index a cluster (after changing chunk metadata):**
```bash
python run_pipeline.py --cluster "الشيكولاتة" --stage chunk dedup embed index
```

---

## Pipeline Stages

### Stage 1 — Markdown Conversion (`scripts/text_extraction.py`)

Converts source PDFs and DOCX files to Markdown using **Docling** with:
- **OCR enabled** — handles scanned Arabic PDFs
- **Table structure detection** — preserves HACCP tables, nutrition grids, ISO checklists
- **CUDA acceleration** — uses GPU if available, falls back to CPU

Output: `data/markdown/{cluster}/{filename}.md`  
Log: `data/markdown/conversion_manifest.json`

### Stage 2 — Adaptive Chunking (`scripts/chunking.py`)

Splits each Markdown document into structured chunks that understand:
- Section hierarchy (headers build a `Root > Section > Subsection` breadcrumb)
- Content types: paragraphs, tables, code blocks, lists, blockquotes
- Arabic-aware: no language-specific tokenisation required

Each chunk gets a stable `chunk_id` (SHA-256 of `cluster:file:index`) that survives re-runs.

**Tuning (vs Vilo defaults):**

| Parameter | Value | Reason |
|---|---|---|
| `min_size` | 300 chars | Same |
| `max_size` | 1500 chars | Arabic regulatory docs are dense |
| `overlap` | 150 chars | Food safety regulations span sentence boundaries |

### Stage 3 — Deduplication (`pipeline/deduplication.py`)

Within each cluster, identifies near-duplicate chunks using **TF-IDF character n-grams (3–5)**:
- Language-agnostic — works on Arabic without a tokeniser
- Pairwise cosine similarity matrix (O(n²)) — manageable at cluster level
- Greedy keep: for each pair above threshold, keep the earlier-encountered chunk
- Report saved to `data/dedup_report.json`

Default threshold: **0.90** (configurable via `DEDUP_THRESHOLD` in `.env`)

### Stage 4 — Embedding (`pipeline/embedder.py`)

Embeds each chunk using **Gemini `text-embedding-004`** (768-dim):
- `task_type=RETRIEVAL_DOCUMENT` — boosts retrieval accuracy over plain embeddings
- Strong multilingual support including Arabic
- Free-tier friendly (1,500 RPM)
- Disk cache at `data/embeddings/{cluster}/{chunk_id}.npy` — no re-embedding on re-runs
- Exponential back-off on 429 rate-limit errors

### Stage 5 — Pinecone Indexing (`pipeline/indexer.py`)

Upserts vectors into the `Food-Safety` Pinecone index (serverless, `aws/eu-west-1`, cosine metric):
- Creates the index automatically on first run if it doesn't exist
- **One namespace per cluster** — enables filtered retrieval by topic
- Batch size: 100 vectors per request (Pinecone limit)
- Stored metadata per vector: `text`, `source_file`, `cluster`, `header`, `chunk_type`, `file_type`, `chunk_index`

---

## Data Clusters

32 topic clusters (CV resumes cluster removed as off-domain):

| # | Cluster Name | Files | Type |
|---|---|---|---|
| 1 | جودة الغذاء | 52 | PDF |
| 2 | التغذية | 97 | PDF |
| 3 | الممارسات التصنيعية الجيدة | 50 | PDF |
| 4 | المواد المضافة | 40 | PDF |
| 5 | النظافة والتطهير | 15 | PDF |
| 6 | الهيئة القومية لسلامة الغذاء | 26 | PDF |
| 7 | تلوث الغذاء | 37 | PDF |
| 8 | الكيمياء | 25 | PDF |
| 9 | الشيكولاتة | 23 | PDF |
| 10 | الميكروبيولوجي | 175 | PDF |
| 11 | تحليل الأغذية | 22 | PDF |
| 12 | أساسيات حفظ وتداول الأغذية | 25 | PDF |
| 13 | مهارات حل المشكلات | 27 | PDF |
| 14 | مؤشرات الأداء | 13 | PDF |
| 15 | سحب العينات | 20 | PDF |
| 16 | معامل التصنيع الغذائي | 34 | PDF |
| 17 | الشروط الصحية لمصانع الأغذية | 38 | PDF |
| 18 | التتبع | 20 | PDF |
| 19 | أنظمة التعبئة والتغليف | 7 | PDF |
| 20 | الهاسب HACCP | 65 | PDF |
| 21 | ISO الأيزو | 85 | PDF |
| 22 | حديث التخرج | 21 | PDF |
| 23 | الزيوت والدهون | 190 | PDF |
| 24 | Catering | 92 | PDF |
| 25 | المكسرات | 70 | PDF |
| 26 | PRP البرامج الأولية | 40 | PDF |
| 27 | الهيئة القومية لسلامة الغذاء (الجديدة) | 70 | PDF |
| 28 | الحبوب ومنتجاتها | 100 | PDF |
| 29 | الكودكس | 500 | PDF |
| 30 | فساد الغذاء | 40 | PDF |
| 31 | الألبان ومنتجاتها | 100 | PDF |
| 32 | الخضروات والفواكه | 200 | PDF |

**Total: ~2,380 files**

---

## Output Files

| Path | Description |
|---|---|
| `data/markdown/` | Converted `.md` files, mirroring `data/raw/` structure |
| `data/markdown/conversion_manifest.json` | Per-file conversion status, timestamps, errors |
| `data/embeddings/{cluster}/{chunk_id}.npy` | Cached embedding vectors (float32 NumPy arrays) |
| `data/dedup_report.json` | Per-cluster dedup log: which chunks were dropped and similarity scores |

---

## Pinecone Structure

```
Index: "Food-Safety"
  Metric:    cosine
  Dimension: 768
  Cloud:     aws
  Region:    eu-west-1

  Namespace: "الشيكولاتة"    ← all chunks from cluster 9
  Namespace: "الميكروبيولوجي" ← all chunks from cluster 10
  ...                          ← one namespace per cluster
```

**Querying a specific topic namespace:**
```python
from services import get_pinecone_client
from config.settings import settings

pc    = get_pinecone_client()
index = pc.Index(settings.PINECONE_INDEX_NAME)

# Search only within HACCP documents
results = index.query(
    vector=query_embedding,   # your 768-dim query vector
    top_k=5,
    namespace="الهاسب HACCP",
    include_metadata=True,
)
```

**Querying across all clusters (no namespace filter):**
```python
results = index.query(
    vector=query_embedding,
    top_k=10,
    include_metadata=True,
)
```

---

## Customising the Pipeline

All tunable knobs are environment variables in `.env`. No code changes needed.

| Variable | Default | Effect |
|---|---|---|
| `DEDUP_THRESHOLD` | `0.90` | Lower = more aggressive dedup |
| `CHUNK_MAX_SIZE` | `1500` | Larger = fewer but richer chunks |
| `CHUNK_OVERLAP` | `150` | Larger = more context continuity at chunk boundaries |
| `EMBEDDING_MODEL` | `models/text-embedding-004` | Swap for any Gemini embedding model |
| `EMBEDDING_DIMENSION` | `768` | Must match the model's output dimension |
| `PINECONE_CLOUD` | `aws` | `aws` or `gcp` |
| `PINECONE_REGION` | `eu-west-1` | Any Pinecone serverless region |
