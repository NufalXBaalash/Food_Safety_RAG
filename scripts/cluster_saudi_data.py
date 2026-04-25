import os
import shutil
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(BASE_DIR, "data", "raw", "files")
TARGET_DIR = os.path.join(BASE_DIR, "data", "raw", "saudi")

# Ordered carefully. More specific clusters at the top!
CLUSTERS = [
    ("haccp", [r"haccp", r"هاسب", r"هسب"]),
    ("iso", [r"iso", r"22000", r"9001", r"ايزو", r"أيزو", r"أيزو"]),
    ("sfda", [r"sfda", r"هيئة", r"سعودي", r"الهيئة"]),
    ("meat", [r"meat", r"لحم", r"لحوم", r"beef", r"poultry"]),
    ("dairy", [r"dairy", r"لبن", r"حليب", r"ألبان", r"البان", r"الألبان", r"milk"]),
    ("fish", [r"fish", r"سمك", r"أسماك", r"اسماك", r"الأسماك"]),
    ("packaging-systems", [r"package", r"packing", r"تعبئة", r"تغليف", r"تعبئة", r"عبوات"]),
    ("vegetables-and-fruits", [r"vegetable", r"fruit", r"فاكهة", r"خضار", r"خضروات", r"فواكه", r"veg"]),
    ("allergens", [r"allergy", r"allergen", r"حساسية", r"حساسيه"]),
    ("food-additives", [r"additive", r"مضافة", r"مضافات", r"preservatives"]),
    ("microbiology", [r"microbiology", r"ميكروب", r"بكتري", r"فطريات", r"فطر", r"pathogen"]),
    ("food-quality", [r"quality", r"جودة", r"qc", r"qa", r"ضبط"]),
    ("hygiene-and-sanitation", [r"hygiene", r"sanitation", r"صحة", r"صحي", r"نظافة", r"تطهير", r"ghp"]),
    ("food-analysis", [r"analysis", r"تحليل", r"فحص", r"فحوصات", r"اختبار"]),
    ("nutrition", [r"nutrition", r"تغذية", r"dietary", r"حمية"]),
    ("oils-and-fats", [r"oil", r"fat", r"زيت", r"دهن", r"زيوت", r"دهون"]),
    ("manufacturing", [r"manufacturing", r"gmp", r"تصنيع", r"صناعات", r"ممارسات"]),
    ("food-spoilage", [r"spoilage", r"تلوث", r"فساد", r"تسمم", r"سموم", r"recall", r"سحب"]),
]

def cluster_data():
    if not os.path.exists(SOURCE_DIR):
        print(f"Source directory {SOURCE_DIR} does not exist.")
        return

    files = [f for f in os.listdir(SOURCE_DIR) if os.path.isfile(os.path.join(SOURCE_DIR, f))]
    print(f"Found {len(files)} files to cluster.")

    moved = 0
    uncategorized = 0

    for filename in files:
        if filename.endswith(".jpg"): # skip thumbnails
            continue

        lower_name = filename.lower()
        matched_cluster = "general-food-safety" # default fallback
        
        for cluster_name, patterns in CLUSTERS:
            if any(re.search(p, lower_name) for p in patterns):
                matched_cluster = cluster_name
                break
        
        dest_folder = os.path.join(TARGET_DIR, matched_cluster)
        os.makedirs(dest_folder, exist_ok=True)
        
        src_path = os.path.join(SOURCE_DIR, filename)
        dest_path = os.path.join(dest_folder, filename)
        
        # move file
        shutil.move(src_path, dest_path)
        # move matching thumbnail if exists
        thumb_path = src_path + "_thumb.jpg"
        if os.path.exists(thumb_path):
            shutil.move(thumb_path, os.path.join(dest_folder, filename + "_thumb.jpg"))

        moved += 1
        if matched_cluster == "general-food-safety":
            uncategorized += 1

    print(f"Clustering complete. {moved} files moved.")
    print(f"Note: {uncategorized} files defaulted to 'general-food-safety'.")

if __name__ == "__main__":
    cluster_data()
