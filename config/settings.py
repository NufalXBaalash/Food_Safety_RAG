import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path)


class BaseConfig:
    ENV = os.getenv("ENV", "dev")



class PineconeConfig:
    API_KEY = os.getenv("PINECONE_API_KEY")
    ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
    INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "rag-index")
    DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", 1024))

    @classmethod
    def validate(cls):
        if not cls.API_KEY:
            raise ValueError("❌ PINECONE_API_KEY is missing")


class LLMConfig:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "google/gemini-2.0-flash-001")

    @classmethod
    def validate(cls):
        if not cls.OPENROUTER_API_KEY:
            print("⚠️ OPENROUTER_API_KEY is missing")



class RetrievalConfig:
    TOP_K = int(os.getenv("TOP_K", 5))
    RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", 3))
    USE_HYBRID = os.getenv("USE_HYBRID", "false").lower() == "true"


class EmbeddingConfig:
    MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


class PipelineConfig:
    DEDUP_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.90"))
    CHUNK_MIN_SIZE = int(os.getenv("CHUNK_MIN_SIZE", "300"))
    CHUNK_MAX_SIZE = int(os.getenv("CHUNK_MAX_SIZE", "1500"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
    EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "50"))
    COUNTRY = os.getenv("COUNTRY", "global")

class ClusterConfig:
    EGYPT_MAP = {
        "جودة الغذاء": "food-quality",
        "التغذية": "nutrition",
        "الممارسات التصنيعية الجيدة": "good-manufacturing-practices",
        "المواد المضافة": "food-additives",
        "النظافة والتطهير": "hygiene-and-sanitation",
        "الهيئة القومية لسلامة الغذاء": "national-food-safety-authority",
        "تلوث الغذاء": "food-contamination",
        "الكيمياء": "chemistry",
        "الشيكولاتة": "chocolate",
        "الشيكولاته": "chocolate", # Handling variant spelling on disk
        "الميكروبيولوجي": "microbiology",
        "تحليل الأغذية": "food-analysis",
        "أساسيات حفظ وتداول الأغذية": "food-preservation-and-handling",
        "مهارات حل المشكلات": "problem-solving-skills",
        "مؤشرات الأداء": "key-performance-indicators",
        "سحب العينات": "sampling",
        "معامل التصنيع الغذائي": "food-manufacturing-labs",
        "الشروط الصحية لمصانع الأغذية": "food-factory-hygiene",
        "التتبع": "traceability",
        "أنظمة التعبئة والتغليف": "packaging-systems",
        "الهاسب HACCP": "haccp",
        "ISO الأيزو": "iso",
        "حديث التخرج": "fresh-graduate",
        "الزيوت والدهون": "oils-and-fats",
        "Catering": "catering",
        "المكسرات": "nuts",
        "PRP البرامج الأولية": "prerequisite-programs",
        "الهيئة القومية لسلامة الغذاء (الجديدة)": "national-food-safety-authority-new",
        "الحبوب ومنتجاتها": "cereals-and-products",
        "الكودكس": "codex",
        "فساد الغذاء": "food-spoilage",
        "الألبان ومنتجاتها": "dairy-and-products",
        "الخضروات والفواكه": "vegetables-and-fruits",
    }
    SAUDI_MAP = {
        "haccp": "haccp",
        "iso": "iso",
        "sfda": "sfda",
        "meat": "meat",
        "dairy": "dairy",
        "fish": "fish",
        "packaging-systems": "packaging-systems",
        "vegetables-and-fruits": "vegetables-and-fruits",
        "allergens": "allergens",
        "food-additives": "food-additives",
        "microbiology": "microbiology",
        "food-quality": "food-quality",
        "hygiene-and-sanitation": "hygiene-and-sanitation",
        "food-analysis": "food-analysis",
        "nutrition": "nutrition",
        "oils-and-fats": "oils-and-fats",
        "manufacturing": "manufacturing",
        "food-spoilage": "food-spoilage",
        "general-food-safety": "general-food-safety",
    }
    Global_MAP={
        "haccp": "haccp",
        "iso": "iso",
        "sfda": "sfda",
        "meat": "meat",
        "dairy": "dairy",
        "fish": "fish",
        "packaging-systems": "packaging-systems",
        "vegetables-and-fruits": "vegetables-and-fruits",
        "allergens": "allergens",
        "food-additives": "food-additives",
        "microbiology": "microbiology",
        "food-quality": "food-quality",
        "hygiene-and-sanitation": "hygiene-and-sanitation",
        "food-analysis": "food-analysis",
        "nutrition": "nutrition",
        "oils-and-fats": "oils-and-fats",
        "manufacturing": "manufacturing",
        "food-spoilage": "food-spoilage",
        "general-food-safety": "general-food-safety",
                "جودة الغذاء": "food-quality",
        "التغذية": "nutrition",
        "الممارسات التصنيعية الجيدة": "good-manufacturing-practices",
        "المواد المضافة": "food-additives",
        "النظافة والتطهير": "hygiene-and-sanitation",
        "الهيئة القومية لسلامة الغذاء": "national-food-safety-authority",
        "تلوث الغذاء": "food-contamination",
        "الكيمياء": "chemistry",
        "الشيكولاتة": "chocolate",
        "الشيكولاته": "chocolate", # Handling variant spelling on disk
        "الميكروبيولوجي": "microbiology",
        "تحليل الأغذية": "food-analysis",
        "أساسيات حفظ وتداول الأغذية": "food-preservation-and-handling",
        "مهارات حل المشكلات": "problem-solving-skills",
        "مؤشرات الأداء": "key-performance-indicators",
        "سحب العينات": "sampling",
        "معامل التصنيع الغذائي": "food-manufacturing-labs",
        "الشروط الصحية لمصانع الأغذية": "food-factory-hygiene",
        "التتبع": "traceability",
        "أنظمة التعبئة والتغليف": "packaging-systems",
        "الهاسب HACCP": "haccp",
        "ISO الأيزو": "iso",
        "حديث التخرج": "fresh-graduate",
        "الزيوت والدهون": "oils-and-fats",
        "Catering": "catering",
        "المكسرات": "nuts",
        "PRP البرامج الأولية": "prerequisite-programs",
        "الهيئة القومية لسلامة الغذاء (الجديدة)": "national-food-safety-authority-new",
        "الحبوب ومنتجاتها": "cereals-and-products",
        "الكودكس": "codex",
        "فساد الغذاء": "food-spoilage",
        "الألبان ومنتجاتها": "dairy-and-products",
        "الخضروات والفواكه": "vegetables-and-fruits",
    }


class Settings:
    def __init__(self):
        self.base = BaseConfig
        self.pinecone = PineconeConfig
        self.llm = LLMConfig
        self.retrieval = RetrievalConfig
        self.embedding = EmbeddingConfig
        self.pipeline = PipelineConfig
        self.clusters = ClusterConfig

    def validate(self):
        self.pinecone.validate()
        self.llm.validate()
    
    # Backward compatibility aliases for run_pipeline.py
    @property
    def COUNTRY(self): return self.pipeline.COUNTRY
    @property
    def DEDUP_THRESHOLD(self): return self.pipeline.DEDUP_THRESHOLD
    @property
    def EMBED_BATCH_SIZE(self): return self.pipeline.EMBED_BATCH_SIZE
    @property
    def PINECONE_INDEX_NAME(self): return self.pinecone.INDEX_NAME
    @property
    def PINECONE_CLOUD(self): return self.pinecone.CLOUD
    @property
    def PINECONE_REGION(self): return self.pinecone.REGION
    @property
    def EMBEDDING_DIMENSION(self): return self.pinecone.DIMENSION
    @property
    def ACCELERATOR_DEVICE(self): 
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    @property
    def EMBEDDING_MODEL(self): return self.embedding.MODEL_NAME
    @property
    def CHUNK_MIN_SIZE(self): return self.pipeline.CHUNK_MIN_SIZE
    @property
    def CHUNK_MAX_SIZE(self): return self.pipeline.CHUNK_MAX_SIZE
    @property
    def CHUNK_OVERLAP(self): return self.pipeline.CHUNK_OVERLAP

    @property
    def active_cluster_map(self):
        if self.pipeline.COUNTRY == "saudi":
            return self.clusters.SAUDI_MAP
        return self.clusters.EGYPT_MAP

    def normalize_arabic(self, text: str) -> str:
        """Normalize Arabic text for better matching."""
        if not text: return ""
        # Remove common variations
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        text = text.replace("ة", "ه")
        # Remove extra whitespace
        text = " ".join(text.split())
        return text


# Project Root for Path Helpers
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Dynamic path helpers (country-aware) ─────────────────────────────────────
def get_raw_dir() -> Path:
    """Returns data/raw/<country>/ using the current settings.COUNTRY value."""
    return _PROJECT_ROOT / "data" / "raw" / settings.pipeline.COUNTRY


def get_markdown_dir() -> Path:
    """Returns data/markdown/<country>/ using the current settings.COUNTRY value."""
    return _PROJECT_ROOT / "data" / "markdown" / settings.pipeline.COUNTRY


def get_cluster_name_map() -> dict[str, str]:
    """Returns the correct cluster map for the active country."""
    if settings.pipeline.COUNTRY == "saudi":
        return settings.clusters.SAUDI_MAP
    return settings.clusters.EGYPT_MAP

# Singleton
settings = Settings()

# Validate on startup
settings.validate()