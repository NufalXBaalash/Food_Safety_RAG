from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.pipeline import Pipeline
from utils.logger import logger

router = APIRouter()
pipeline = Pipeline()

class ChatRequest(BaseModel):
    query: str
    country: Optional[str] = "global" # Adding country field for filtering

class ChatResponse(BaseModel):
    answer: str
    categories: list[str]
    context: list[dict]

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Web Chat Request: {request.query} | Filter: {request.country}")
        result = pipeline.run(request.query, country=request.country)
        result1= pipeline.run(request.query, country="global")
        if len(result["context"])==0:
             return ChatResponse(
            answer=result1["answer"],
            categories=result1["categories"],
            context=result1["context"]
        )
        return ChatResponse(
            answer=result["answer"],
            categories=result["categories"],
            context=result["context"]
        )
    except Exception as e:
        logger.error(f"Error in web chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))