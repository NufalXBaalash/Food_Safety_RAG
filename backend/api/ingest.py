import os
import hashlib
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
from utils.hashing import is_duplicate_hash, register_file
from utils.logger import logger
from scripts.text_extraction import convert_cluster
from scripts.chunking import chunk_cluster
from pipeline.deduplication import dedup_chunks, save_dedup_report
from pipeline.embedder import embed_chunks
from pipeline.indexer import upsert_to_pinecone
from config.settings import settings

INGEST_PROGRESS = {}

router = APIRouter()

@router.get("/ingest/progress")
def get_progress(cluster: str):
    return INGEST_PROGRESS.get(cluster, {"stage": "idle", "file": ""})

@router.post("/ingest")
async def ingest_files(
    files: List[UploadFile] = File(...),
    country: str = Form(...),
    cluster: str = Form(...)
):
    try:
        # Temporarily use the selected country for parsing
        settings.pipeline.COUNTRY = country.lower()
        
        PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        raw_dir = PROJECT_ROOT / "data" / "raw" / country.lower() / cluster
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        skipped_files = []
        
        for file in files:
            # Ensure we only use the basename to avoid FileNotFoundError from nested webkit relative paths
            file_path = raw_dir / Path(file.filename).name
            
            # Read file into memory for hashing
            content = await file.read()
            file_hash = hashlib.md5(content).hexdigest()
            
            if is_duplicate_hash(file_hash) and file_path.exists():
                skipped_files.append(file.filename)
                continue
                
            # Write safely to disk
            with open(file_path, "wb") as f:
                f.write(content)
                
            register_file(file_hash, str(file_path))
            saved_files.append(file.filename)
            logger.info(f"Saved new file: {file.filename} into {country}/{cluster}")

        
        def update_progress(status):
            INGEST_PROGRESS[cluster] = status

        if not saved_files:
            logger.info("All files were duplicates, but continuing pipeline execution on the existing cluster dataset.")

        # 1. Convert to Markdown
        logger.info(f"Running conversion for {cluster}")
        update_progress({"stage": "Preparing Conversion", "file": "..."})
        convert_cluster(cluster, progress_callback=update_progress)
        
        # 2. Chunking
        logger.info(f"Running adaptive chunking for {cluster}")
        update_progress({"stage": "Preparing Chunking", "file": "..."})
        chunks = chunk_cluster(cluster, progress_callback=update_progress)
        
        # 3. Deduplication
        update_progress({"stage": "Deduplicating Chunks", "file": "..."})
        kept_chunks, dropped_log = dedup_chunks(chunks)
        save_dedup_report(cluster, dropped_log)
        
        # 4. Embedding & Indexing
        EXECUTE_EMBEDDING = True
        if EXECUTE_EMBEDDING:
            logger.info(f"Embedding {len(kept_chunks)} valid chunks")
            update_progress({"stage": "Embedding & Indexing", "file": "Pushing to Pinecone..."})
            embedded_chunks = embed_chunks(kept_chunks)
            upsert_to_pinecone(embedded_chunks, namespace=cluster, country=country.lower())
        else:
            logger.info(f"Skipping embedding & Pinecone index generation for {len(kept_chunks)} chunks (local dev mode).")
            
        update_progress({"stage": "Complete", "file": ""})

        return {
            "message": f"Ingestion processed {len(saved_files)} new files successfully for [{country.upper()}] - {cluster}. Skipped {len(skipped_files)} duplicates.",
            "saved": saved_files,
            "skipped": skipped_files
        }
    except Exception as e:
        logger.error(f"Ingestion API failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
