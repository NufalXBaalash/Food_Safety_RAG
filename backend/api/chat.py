from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.pipeline import Pipeline
from utils.logger import logger

router = APIRouter()
pipeline = Pipeline()

class ChatRequest(BaseModel):
    query: str
    country: Optional[str] = "All" # Adding country field for filtering

class ChatResponse(BaseModel):
    answer: str
    categories: list[str]
    context: list[dict]

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Web Chat Request: {request.query} | Filter: {request.country}")
        result = pipeline.run(request.query, country=request.country)
        
        return ChatResponse(
            answer=result["answer"],
            categories=result["categories"],
            context=result["context"]
        )
    except Exception as e:
        logger.error(f"Error in web chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
