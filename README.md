# Food Safety RAG — Ingestion Pipeline

Converts food-safety PDFs/DOCX files (Arabic & English) into a searchable Pinecone vector database for RAG. Supports two country datasets: **Egypt** (32 Arabic clusters) and **Saudi Arabia** (19 English clusters).

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. One-time: load the word segmentation corpus
python -c "from wordsegment import load; load()"

# 3. Copy your API keys into .env (see Configuration below)

# 4. Test your connections
python test/test_pinecone.py
python test/test_gemini.py

# 5. Run the pipeline on one cluster to validate everything works
python run_pipeline.py --cluster "الشيكولاتة"
```

---

## Configuration (`.env`)

Create a `.env` file in the project root:

```dotenv
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=food-safety
PINECONE_CLOUD=aws
PINECONE_REGION=eu-west-1

GEMINI_API_KEY=...
GROQ_API_KEY=...         # optional

ACCELERATOR_DEVICE=cpu   # set to "cuda" if you have a GPU

EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

DEDUP_THRESHOLD=0.90
CHUNK_MIN_SIZE=300
CHUNK_MAX_SIZE=1500
CHUNK_OVERLAP=150
EMBED_BATCH_SIZE=50
```

---

## How to Run the Pipeline

The single entry point is `run_pipeline.py`. It runs 6 stages in order:

```
download → convert → chunk → dedup → embed → index
```

Every stage is resumable — re-running after a crash picks up where it left off.

### Egypt Dataset (default)

```bash
# One cluster
python run_pipeline.py --cluster "الشيكولاتة"

# Multiple clusters
python run_pipeline.py --cluster "الشيكولاتة" "الكيمياء" "الميكروبيولوجي"

# All 32 Egypt clusters
python run_pipeline.py --country egypt
```

### Saudi Dataset

```bash
# One cluster
python run_pipeline.py --country saudi --cluster haccp

# All 19 Saudi clusters
python run_pipeline.py --country saudi
```

Saudi cluster names: `haccp`, `iso`, `sfda`, `meat`, `dairy`, `fish`, `packaging-systems`, `vegetables-and-fruits`, `allergens`, `food-additives`, `microbiology`, `food-quality`, `hygiene-and-sanitation`, `food-analysis`, `nutrition`, `oils-and-fats`, `manufacturing`, `food-spoilage`, `general-food-safety`

### Run Only Specific Stages

```bash
# Download raw files only
python run_pipeline.py --cluster "الشيكولاتة" --stage download

# Convert to Markdown only
python run_pipeline.py --cluster "الشيكولاتة" --stage convert

# Skip download + convert (files already on disk), run the rest
python run_pipeline.py --cluster "الشيكولاتة" --stage chunk dedup embed index

# Saudi: download + convert only
python run_pipeline.py --country saudi --cluster haccp --stage download convert
```

---

## Setting Up Data Sources

### Egypt — Google Drive OAuth

Egypt data is auto-downloaded from Google Drive. You need a `credentials.json` file:

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → Enable Drive API → Create OAuth 2.0 Desktop credentials → Download as `credentials.json` → place it in the project root.
2. On first run, a browser window opens to authorize. A `token.json` is saved for future runs.

### Saudi — Getting Raw Files onto Disk

Pick one option:

| Option | How |
|---|---|
| **Bulk zip from Drive** | Set `SAUDI_ZIP_FILE_ID` in `FULL_PIPE_COLAB.py`, then run on Colab |
| **Per-cluster Drive links** | Fill in `"url"` fields in `data/raw/saudi/saudi_drive_files.json`, then use `--stage download` |
| **Manual copy** | Drop files into `data/raw/saudi/{cluster_name}/` directly |
| **Auto-cluster flat files** | Put files in `data/raw/files/`, run `python scripts/cluster_saudi_data.py` |

---

## Running on Google Colab (GPU)

**Step 1 — Build the Colab script** (run this locally):
```bash
python build_colab_script.py
# Creates FULL_PIPE_COLAB.py (~70 MB, embeds the whole project)
```

**Step 2 — Upload to Colab:**
1. Open [colab.research.google.com](https://colab.research.google.com), set runtime to **GPU (T4)**
2. Upload `FULL_PIPE_COLAB.py`
3. In a cell, run:
   ```python
   !python FULL_PIPE_COLAB.py
   ```

**Step 3 — Follow prompts:**
- Choose country (`egypt` or `saudi`)
- For Saudi: optionally provide a Google Drive zip file ID for bulk download
- Enter a cluster name, or press Enter to run all clusters

---

## Other Useful Scripts

| Script | Purpose |
|---|---|
| `scripts/cluster_saudi_data.py` | Auto-sorts flat Saudi files into cluster folders by filename keywords |
| `scripts/download_telegram.py` | Downloads files from a private Telegram group (needs `TELEGRAM_API_ID` + `TELEGRAM_API_HASH`) |
| `test/test_pinecone.py` | Verifies Pinecone connection |
| `test/test_gemini.py` | Verifies Gemini API key |
| `test/test_groq.py` | Verifies Groq API key |

---

## Querying the Index

```python
from services import get_pinecone_client
from config.settings import settings

pc    = get_pinecone_client()
index = pc.Index(settings.PINECONE_INDEX_NAME)

# Search within one cluster (namespace = English cluster name)
results = index.query(
    vector=your_1024_dim_embedding,
    top_k=5,
    namespace="haccp",
    include_metadata=True,
)

# Search across all clusters
results = index.query(vector=your_1024_dim_embedding, top_k=10, include_metadata=True)

# Filter by country
results = index.query(
    vector=your_1024_dim_embedding,
    top_k=10,
    filter={"country": {"$eq": "saudi"}},
    include_metadata=True,
)

# Each result contains:
# match["metadata"]["text"]        — the chunk text
# match["metadata"]["source_file"] — original filename
# match["metadata"]["header"]      — section breadcrumb
# match["metadata"]["country"]     — 'egypt' or 'saudi'
```

---

## Egypt Clusters Reference

| Arabic Name | Pinecone Namespace |
|---|---|
| الشيكولاتة | chocolate |
| الميكروبيولوجي | microbiology |
| الكيمياء | chemistry |
| جودة الغذاء | food-quality |
| التغذية | nutrition |
| الممارسات التصنيعية الجيدة | good-manufacturing-practices |
| المواد المضافة | food-additives |
| النظافة والتطهير | hygiene-and-sanitation |
| تلوث الغذاء | food-contamination |
| تحليل الأغذية | food-analysis |
| أساسيات حفظ وتداول الأغذية | food-preservation-and-handling |
| مهارات حل المشكلات | problem-solving-skills |
| مؤشرات الأداء | key-performance-indicators |
| سحب العينات | sampling |
| معامل التصنيع الغذائي | food-manufacturing-labs |
| الشروط الصحية لمصانع الأغذية | food-factory-hygiene |
| التتبع | traceability |
| أنظمة التعبئة والتغليف | packaging-systems |
| الهاسب HACCP | haccp |
| ISO الأيزو | iso |
| حديث التخرج | fresh-graduate |
| الزيوت والدهون | oils-and-fats |
| Catering | catering |
| المكسرات | nuts |
| PRP البرامج الأولية | prerequisite-programs |
| الهيئة القومية لسلامة الغذاء | national-food-safety-authority |
| الهيئة القومية لسلامة الغذاء (الجديدة) | national-food-safety-authority-new |
| الحبوب ومنتجاتها | cereals-and-products |
| الكودكس | codex |
| فساد الغذاء | food-spoilage |
| الألبان ومنتجاتها | dairy-and-products |
| الخضروات والفواكه | vegetables-and-fruits |
