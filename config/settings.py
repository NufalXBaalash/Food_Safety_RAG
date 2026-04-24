import os
from dotenv import load_dotenv

# Load all configurations from .env
load_dotenv()

class Config:
    # ── Pinecone ────────────────────────────────────────────────────────────────
    PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "food-safety")
    PINECONE_CLOUD     = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION    = os.getenv("PINECONE_REGION", "us-east-1")

    # ── AI Services ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

    # Hardware acceleration: "cpu", "cuda", or "auto"
    ACCELERATOR_DEVICE = os.getenv("ACCELERATOR_DEVICE", "cpu").lower()

    # ── Embedding ────────────────────────────────────────────────────────────────
    EMBEDDING_MODEL     = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    # ── Metadata ──────────────────────────────────────────────────────────────────
    COUNTRY             = os.getenv("COUNTRY", "egypt")

    # ── Pipeline ─────────────────────────────────────────────────────────────────
    DEDUP_THRESHOLD     = float(os.getenv("DEDUP_THRESHOLD", "0.90"))
    CHUNK_MIN_SIZE      = int(os.getenv("CHUNK_MIN_SIZE", "300"))
    CHUNK_MAX_SIZE      = int(os.getenv("CHUNK_MAX_SIZE", "1500"))
    CHUNK_OVERLAP       = int(os.getenv("CHUNK_OVERLAP", "150"))
    # How many chunks to embed + upsert per batch — controls peak RAM usage.
    # Lower = less RAM. Higher = fewer API round-trips (Pinecone max is 100).
    EMBED_BATCH_SIZE    = int(os.getenv("EMBED_BATCH_SIZE", "50"))

# ── Cluster name mapping (Arabic folder name → English display name) ───────────
CLUSTER_NAME_MAP: dict[str, str] = {
    "جودة الغذاء":                               "food-quality",
    "التغذية":                                    "nutrition",
    "الممارسات التصنيعية الجيدة":                  "good-manufacturing-practices",
    "المواد المضافة":                              "food-additives",
    "النظافة والتطهير":                            "hygiene-and-sanitation",
    "الهيئة القومية لسلامة الغذاء":                "national-food-safety-authority",
    "تلوث الغذاء":                                 "food-contamination",
    "الكيمياء":                                    "chemistry",
    "الشيكولاتة":                                  "chocolate",
    "الميكروبيولوجي":                              "microbiology",
    "تحليل الأغذية":                               "food-analysis",
    "أساسيات حفظ وتداول الأغذية":                  "food-preservation-and-handling",
    "مهارات حل المشكلات":                          "problem-solving-skills",
    "مؤشرات الأداء":                               "key-performance-indicators",
    "سحب العينات":                                 "sampling",
    "معامل التصنيع الغذائي":                       "food-manufacturing-labs",
    "الشروط الصحية لمصانع الأغذية":                 "food-factory-hygiene",
    "التتبع":                                      "traceability",
    "أنظمة التعبئة والتغليف":                      "packaging-systems",
    "الهاسب HACCP":                                "haccp",
    "ISO الأيزو":                                   "iso",
    "حديث التخرج":                                 "fresh-graduate",
    "الزيوت والدهون":                              "oils-and-fats",
    "Catering":                                    "catering",
    "المكسرات":                                    "nuts",
    "PRP البرامج الأولية":                          "prerequisite-programs",
    "الهيئة القومية لسلامة الغذاء (الجديدة)":       "national-food-safety-authority-new",
    "الحبوب ومنتجاتها":                            "cereals-and-products",
    "الكودكس":                                     "codex",
    "فساد الغذاء":                                 "food-spoilage",
    "الألبان ومنتجاتها":                            "dairy-and-products",
    "الخضروات والفواكه":                            "vegetables-and-fruits",
}

# Create a singleton configuration instance
settings = Config()
