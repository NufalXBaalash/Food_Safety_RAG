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

router = APIRouter()

@router.post("/ingest")
async def ingest_files(
    files: List[UploadFile] = File(...),
    country: str = Form(...),
    cluster: str = Form(...)
):
    try:
        # Temporarily use the selected country for parsing
        settings.COUNTRY = country.lower()
        
        PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        raw_dir = PROJECT_ROOT / "data" / "raw" / cluster
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        skipped_files = []
        
        for file in files:
            file_path = raw_dir / file.filename
            
            # Read file into memory for hashing
            content = await file.read()
            file_hash = hashlib.md5(content).hexdigest()
            
            if is_duplicate_hash(file_hash):
                skipped_files.append(file.filename)
                continue
                
            # Write safely to disk
            with open(file_path, "wb") as f:
                f.write(content)
                
            register_file(file_hash, str(file_path))
            saved_files.append(file.filename)
            logger.info(f"Saved new file: {file.filename} into {country}/{cluster}")

        if not saved_files:
            return {"message": f"All {len(files)} files were already verified as duplicates and skipped."}

        # 1. Convert to Markdown
        logger.info(f"Running conversion for {cluster}")
        convert_cluster(cluster)
        
        # 2. Chunking
        logger.info(f"Running adaptive chunking for {cluster}")
        chunks = chunk_cluster(cluster)
        
        # 3. Deduplication
        kept_chunks, dropped_log = dedup_chunks(chunks)
        save_dedup_report(cluster, dropped_log)
        
        # 4. Embedding & Indexing
        # The user specifically requested to write this logic so the schema remains identical,
        # but NOT to execute the heavy embedding model on their local machine during this session.
        # Thus, we preserve the exact pipeline calls but wrap them in a safety toggle.
        
        EXECUTE_EMBEDDING = False # Toggled off per user request for local testing
        if EXECUTE_EMBEDDING:
            logger.info(f"Embedding {len(kept_chunks)} valid chunks")
            embedded_chunks = embed_chunks(kept_chunks)
            upsert_to_pinecone(embedded_chunks, namespace=cluster)
        else:
            logger.info(f"Skipping embedding & Pinecone index generation for {len(kept_chunks)} chunks (local dev mode).")

        return {
            "message": f"Ingestion processed {len(saved_files)} new files successfully for [{country.upper()}] - {cluster}. Skipped {len(skipped_files)} duplicates. (Embedding intentionally bypassed).",
            "saved": saved_files,
            "skipped": skipped_files
        }
    except Exception as e:
        logger.error(f"Ingestion API failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
