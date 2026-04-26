import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from core.pipeline import Pipeline
from utils.logger import logger

app = FastAPI(title="Food Safety RAG API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Pipeline
pipeline = Pipeline()

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    categories: list[str]
    context: list[dict]

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Web Chat Request: {request.query}")
        result = pipeline.run(request.query)
        return ChatResponse(
            answer=result["answer"],
            categories=result["categories"],
            context=result["context"]
        )
    except Exception as e:
        logger.error(f"Error in web chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
