import os
from pathlib import Path
from dotenv import load_dotenv

# Load all configurations from .env
load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Config:
    # ── Pinecone ────────────────────────────────────────────────────────────────
    PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "food-safety")
    PINECONE_CLOUD     = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION    = os.getenv("PINECONE_REGION", "us-east-1")

    # ── AI Services ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

    # ── Telegram ────────────────────────────────────────────────────────────────
    TELEGRAM_API_ID   = os.getenv("TELEGRAM_API_ID")
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

    # Hardware acceleration: "cpu", "cuda", or "auto"
    ACCELERATOR_DEVICE = os.getenv("ACCELERATOR_DEVICE", "cpu").lower()

    # ── Embedding ────────────────────────────────────────────────────────────────
    EMBEDDING_MODEL     = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    # ── Metadata ──────────────────────────────────────────────────────────────────
    # Override at runtime with --country flag (see run_pipeline.py) or via .env
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

# ── Saudi Arabia cluster name map (English folder → Pinecone display name) ──────
SAUDI_CLUSTER_NAME_MAP: dict[str, str] = {
    "haccp":                   "haccp",
    "iso":                     "iso",
    "sfda":                    "sfda",
    "meat":                    "meat",
    "dairy":                   "dairy",
    "fish":                    "fish",
    "packaging-systems":       "packaging-systems",
    "vegetables-and-fruits":   "vegetables-and-fruits",
    "allergens":               "allergens",
    "food-additives":          "food-additives",
    "microbiology":            "microbiology",
    "food-quality":            "food-quality",
    "hygiene-and-sanitation":  "hygiene-and-sanitation",
    "food-analysis":           "food-analysis",
    "nutrition":               "nutrition",
    "oils-and-fats":           "oils-and-fats",
    "manufacturing":           "manufacturing",
    "food-spoilage":           "food-spoilage",
    "general-food-safety":     "general-food-safety",
}

# Create a singleton configuration instance
settings = Config()


# ── Dynamic path helpers (country-aware) ─────────────────────────────────────
def get_raw_dir() -> Path:
    """Returns data/raw/<country>/ using the current settings.COUNTRY value."""
    return _PROJECT_ROOT / "data" / "raw" / settings.COUNTRY


def get_markdown_dir() -> Path:
    """Returns data/markdown/<country>/ using the current settings.COUNTRY value."""
    return _PROJECT_ROOT / "data" / "markdown" / settings.COUNTRY


def get_cluster_name_map() -> dict[str, str]:
    """Returns the correct cluster map for the active country."""
    if settings.COUNTRY == "saudi":
        return SAUDI_CLUSTER_NAME_MAP
    return CLUSTER_NAME_MAP
