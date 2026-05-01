import os
import sys
import logging
from pathlib import Path

# Ensure the backend directory is on sys.path so `api` package is importable
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Also add project root for rag/ module access
PROJECT_ROOT = BACKEND_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.chat import router as chat_router
from api.ingest import router as ingest_router

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app = FastAPI(title="Food Safety RAG API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(chat_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")

# Mount static files
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning", access_log=False)
