from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.agent import AgentService
from utils.logger import logger

router = APIRouter()
agent = AgentService()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str
    country: Optional[str] = "global"
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    categories: list[str]
    context: list[dict]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info(f"Web Chat Request: {request.query} | Filter: {request.country}")
        history = [{"role": m.role, "content": m.content} for m in request.history]

        result = agent.chat(request.query, country=request.country, history=history)

        # Fallback to global if country-specific returns no context
        if len(result["context"]) == 0 and request.country != "global":
            result = agent.chat(request.query, country="global", history=history)

        return ChatResponse(
            answer=result["answer"],
            categories=result["categories"],
            context=result["context"],
        )
    except Exception as e:
        logger.error(f"Error in web chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
