import os
import base64
import zipfile
from io import BytesIO

# ── Egypt cluster names (Arabic folder names) ──────────────────────────────────
EGYPT_CLUSTERS = [
    "جودة الغذاء", "التغذية", "الممارسات التصنيعية الجيدة", "المواد المضافة",
    "النظافة والتطهير", "الهيئة القومية لسلامة الغذاء", "تلوث الغذاء",
    "الكيمياء", "الشيكولاتة", "الميكروبيولوجي", "تحليل الأغذية",
    "أساسيات حفظ وتداول الأغذية", "مهارات حل المشكلات", "مؤشرات الأداء",
    "سحب العينات", "معامل التصنيع الغذائي", "الشروط الصحية لمصانع الأغذية",
    "التتبع", "أنظمة التعبئة والتغليف", "الهاسب HACCP", "ISO الأيزو",
    "حديث التخرج", "الزيوت والدهون", "Catering", "المكسرات",
    "PRP البرامج الأولية", "الهيئة القومية لسلامة الغذاء (الجديدة)",
    "الحبوب ومنتجاتها", "الكودكس", "فساد الغذاء",
    "الألبان ومنتجاتها", "الخضروات والفواكه",
]

# ── Saudi cluster names (English folder names) ─────────────────────────────────
SAUDI_CLUSTERS = [
    "haccp", "iso", "sfda", "meat", "dairy", "fish",
    "packaging-systems", "vegetables-and-fruits", "allergens",
    "food-additives", "microbiology", "food-quality",
    "hygiene-and-sanitation", "food-analysis", "nutrition",
    "oils-and-fats", "manufacturing", "food-spoilage", "general-food-safety",
]
GLOBAL_CLUSETRS=[ "haccp", "iso", "sfda", "meat", "dairy", "fish",
    "packaging-systems", "vegetables-and-fruits", "allergens",
    "food-additives", "microbiology", "food-quality",
    "hygiene-and-sanitation", "food-analysis", "nutrition",
    "oils-and-fats", "manufacturing", "food-spoilage", "general-food-safety",  "جودة الغذاء", "التغذية", "الممارسات التصنيعية الجيدة", "المواد المضافة",
    "النظافة والتطهير", "الهيئة القومية لسلامة الغذاء", "تلوث الغذاء",
    "الكيمياء", "الشيكولاتة", "الميكروبيولوجي", "تحليل الأغذية",
    "أساسيات حفظ وتداول الأغذية", "مهارات حل المشكلات", "مؤشرات الأداء",
    "سحب العينات", "معامل التصنيع الغذائي", "الشروط الصحية لمصانع الأغذية",
    "التتبع", "أنظمة التعبئة والتغليف", "الهاسب HACCP", "ISO الأيزو",
    "حديث التخرج", "الزيوت والدهون", "Catering", "المكسرات",
    "PRP البرامج الأولية", "الهيئة القومية لسلامة الغذاء (الجديدة)",
    "الحبوب ومنتجاتها", "الكودكس", "فساد الغذاء",
    "الألبان ومنتجاتها", "الخضروات والفواكه",]

def _build_colab_template(zip_b64: str) -> str:
    """Return the FULL_PIPE_COLAB.py source as a string."""

    egypt_repr = repr(EGYPT_CLUSTERS)
    saudi_repr = repr(SAUDI_CLUSTERS)
    global_repr=repr(GLOBAL_CLUSETRS)

    return f'''"""
FULL_PIPE_COLAB.py

Run this script in Google Colab to deploy the full Food Safety RAG pipeline.
This unpacks your architecture securely and installs GPU requirements.

Supported countries:
  egypt  — Arabic cluster folders  (e.g. "الشيكولاتة") — downloaded on-demand from Google Drive
  saudi  — English cluster folders (e.g. "haccp")       — requires Drive URLs in saudi_drive_files.json
                                                           OR a pre-zipped Drive file set via SAUDI_ZIP_FILE_ID
"""

import os
import base64
import zipfile
import shutil
from io import BytesIO
import subprocess
import sys

REPO_B64 = "{zip_b64}"

# ── Saudi data zip (optional fast-path) ──────────────────────────────────────
# If you have all Saudi raw data zipped and uploaded to Google Drive,
# paste the FILE ID (not the full URL) here.  The script will download
# and unzip it automatically before the pipeline runs.
# Leave empty ("") to skip — data will then be fetched cluster-by-cluster
# via saudi_drive_files.json (requires URLs to be filled in).
SAUDI_ZIP_FILE_ID = ""

# ── Available clusters per country ────────────────────────────────────────────
EGYPT_CLUSTERS  = {egypt_repr}
SAUDI_CLUSTERS  = {saudi_repr}
GLOBAL_CLUSTERS ={global_repr}

COUNTRY_CLUSTERS = {{
    "egypt": EGYPT_CLUSTERS,
    "saudi": SAUDI_CLUSTERS,
    "global":GLOBAL_CLUSTERS
}}


def _download_saudi_zip(file_id: str) -> bool:
    """Download a Google Drive zip of Saudi raw data and extract it."""
    print(f"  📥 Downloading Saudi data zip from Drive (file_id={{file_id}})...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "gdown"],
            check=True,
        )
        import gdown
        zip_path = "/content/saudi_raw.zip"
        gdown.download(id=file_id, output=zip_path, quiet=False)
        print("  📦 Extracting Saudi data...")
        dest = "/content/Food_Safety_RAG/data/raw/saudi"
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest)
        os.remove(zip_path)
        print(f"  ✅ Saudi data extracted to {{dest}}")
        return True
    except Exception as e:
        print(f"  ⚠️  Could not download Saudi zip: {{e}}")
        return False


def _ensure_saudi_data(country: str) -> None:
    """
    For Saudi runs: try to get the raw data into data/raw/saudi/.
    Priority:
      1. SAUDI_ZIP_FILE_ID is set  → download once via gdown
      2. Prompt user for a Drive zip file ID interactively
      3. Skip (data is expected to already be on disk / pulled per-cluster via Drive manifest)
    """
    if country != "saudi":
        return

    saudi_raw = "/content/Food_Safety_RAG/data/raw/saudi"

    # Count non-metadata files already present
    existing = 0
    if os.path.isdir(saudi_raw):
        for root, _, files in os.walk(saudi_raw):
            existing += sum(
                1 for f in files
                if f.lower().endswith((".pdf", ".docx", ".doc")) and f != "metadata.json"
            )

    if existing > 0:
        print(f"  ✅ Saudi raw data already on disk ({{existing}} files found). Skipping zip download.")
        return

    # Try the pre-configured zip ID first
    if SAUDI_ZIP_FILE_ID:
        _download_saudi_zip(SAUDI_ZIP_FILE_ID)
        return

    # Interactive fallback
    print("\\n⚠️  No Saudi raw files found in data/raw/saudi/.")
    print("Options:")
    print("  [1] Enter a Google Drive FILE ID for a zip of the Saudi data")
    print("  [2] Skip — per-cluster download will be attempted via saudi_drive_files.json")
    choice = input("Choice [1/2] (default: 2): ").strip() or "2"
    if choice == "1":
        fid = input("Google Drive File ID: ").strip()
        if fid:
            _download_saudi_zip(fid)
        else:
            print("  No file ID entered — skipping zip download.")
    else:
        print("  Skipping zip download. Make sure Drive URLs are set in saudi_drive_files.json.")


def setup_colab():
    # ── [1/3] Unpack ──────────────────────────────────────────────────────────
    print("📦 [1/3] Unpacking Food Safety RAG architecture...")
    zip_data = base64.b64decode(REPO_B64)
    with zipfile.ZipFile(BytesIO(zip_data), "r") as zipf:
        zipf.extractall("/content/Food_Safety_RAG")
    os.chdir("/content/Food_Safety_RAG")

    # ── [2/3] Install deps ────────────────────────────────────────────────────
    print("⚙️  [2/3] Installing dependencies (docling, bge-m3, torch, uvicorn, pyngrok) — ~1 min...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt", "uvicorn", "fastapi", "pyngrok"])

    # ── [3/3] Configure run ───────────────────────────────────────────────────
    print("\\n🚀 [3/3] Configuring Pipeline Run\\n")

    print("\\nWhat would you like to run?")
    print("  1. Run Data Ingestion Pipeline")
    print("  2. Start API / Web Server (UI & Chat)")
    print("  3. Both (Ingest then Start Server)")
    mode = input("Choice [1/2/3] (default: 2): ").strip() or "2"

    if mode in ["1", "3"]:
        # Country selection
        print("\\n--- Pipeline Configuration ---")
        print("Select country dataset:")
        print("  egypt  — Arabic clusters  (auto-downloaded from Google Drive)")
        print("  saudi  — English clusters (requires zip upload or Drive URLs)")
        while True:
            country = input("Country [egypt/saudi] (default: egypt): ").strip().lower() or "egypt"
            if country in COUNTRY_CLUSTERS:
                break
            print(f"  ⚠️  Unknown country '{{country}}'. Please type 'egypt' or 'saudi'.")

        # For Saudi: ensure raw data is present before the pipeline starts
        _ensure_saudi_data(country)

        # Cluster selection
        clusters = COUNTRY_CLUSTERS[country]
        print(f"\\nAvailable {{country.upper()}} clusters:")
        for i, name in enumerate(clusters, 1):
            print(f"  {{i:2d}}. {{name}}")

        print("\\nType the exact cluster name to process ONE cluster,")
        print("or press Enter to run ALL clusters for this country:")
        cluster = input("Cluster Name: ").strip()

        # Build & run command
        cmd = [sys.executable, "run_pipeline.py", "--country", country]
        if cluster:
            cmd += ["--cluster", cluster]

        print(f"\\n▶  Running: {{' '.join(cmd)}}\\n")
        subprocess.run(cmd)

    if mode in ["2", "3"]:
        print("\\n--- Starting API Server ---")
        
        # Ngrok setup
        use_ngrok = input("Use Ngrok for public URL access? [y/N]: ").strip().lower() == 'y'
        if use_ngrok:
            print("\\n(Optional) Enter your Ngrok Authtoken if you have one, or press Enter to skip:")
            ngrok_token = input("Authtoken: ").strip()
            try:
                from pyngrok import ngrok
                if ngrok_token:
                    ngrok.set_auth_token(ngrok_token)
                public_url = ngrok.connect(8000).public_url
                print(f"\\n✅ Ngrok Tunnel Established!")
                print(f"🔗 Public URL: {{public_url}}\\n")
            except Exception as e:
                print(f"  ⚠️ Could not start Ngrok: {{e}}\\n")
        else:
            try:
                from google.colab import output
                print("\\n🌐 Exposing Port 8000 for Colab Access...")
                output.serve_kernel_port_as_window(8000)
                output.serve_kernel_port_as_iframe(8000, height=800)
            except ImportError:
                print("  ⚠️ Not running in Colab, unable to use colab proxy.\\n")
            
        print("🚀 Launching Uvicorn Server (Stop cell to exit)...\\n")
        cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
        subprocess.run(cmd)


if __name__ == "__main__":
    setup_colab()
'''


def create_colab_script():
    print("Packing repository into memory...")
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("."):
            # Exclude large / irrelevant directories
            dirs[:] = [
                d for d in dirs
                if d not in {".venv", ".git", "__pycache__", "test_output", ".claude", ".gemini"}
            ]

            for file in files:
                # Skip compiled / generated files
                if file.lower().endswith((".pyc",)):
                    continue
                if file.lower() in {"full_pipe_colab.py", "build_colab_script.py"}:
                    continue
                # Skip raw document files and cached vectors
                if file.lower().endswith((".pdf", ".docx", ".doc", ".npy", ".mp4")):
                    continue
                if "embeddings" in root:
                    continue

                file_path = os.path.join(root, file)
                zipf.write(file_path, file_path)

    zip_b64 = base64.b64encode(zip_buffer.getvalue()).decode("utf-8")

    print("Writing FULL_PIPE_COLAB.py...")
    colab_source = _build_colab_template(zip_b64)

    with open("FULL_PIPE_COLAB.py", "w", encoding="utf-8") as f:
        f.write(colab_source)

    print("✅  Success! FULL_PIPE_COLAB.py created.")
    print(f"    Embedded zip size: {len(zip_b64) // 1024} KB (base64)")


if __name__ == "__main__":
    create_colab_script()
