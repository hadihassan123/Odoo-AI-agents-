from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import verify_service_api_key
from app.db.database import get_db
from app.models.chat_model import Chat
from app.services.ai_service import AIServiceError, ai_studio_service

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    model: Literal["groq", "gemma"] = "groq"
    mode: Literal["general", "pipeline", "knowledge"] = "general"
    session_id: str | None = None
    user_id: str | None = None
    context: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    id: int
    response: str
    session_id: str | None = None
    user_id: str | None = None
    model: str
    mode: str


class ChatHistoryItem(BaseModel):
    id: int
    session_id: str | None = None
    user_id: str | None = None
    message: str
    response: str
    model: str
    mode: str
    created_at: str


@router.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_service_api_key),
):
    try:
        response = ai_studio_service.generate_response(
            message=req.message.strip(),
            provider=req.model,
            mode=req.mode,
            history=[item.model_dump() for item in req.history],
            context=req.context.strip() if req.context else None,
        )
    except AIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    chat_record = Chat(
        user_id=req.user_id or "anonymous",
        message=req.message.strip(),
        response=response,
        model=req.model,
        mode=req.mode,
        session_id=req.session_id,
    )
    db.add(chat_record)
    db.commit()
    db.refresh(chat_record)
    return ChatResponse(
        id=chat_record.id,
        response=chat_record.response,
        session_id=chat_record.session_id,
        user_id=chat_record.user_id,
        model=chat_record.model,
        mode=chat_record.mode,
    )


@router.get("/chat/history", response_model=list[ChatHistoryItem])
def chat_history(
    session_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(verify_service_api_key),
):
    query = db.query(Chat).order_by(Chat.created_at.desc())
    if session_id:
        query = query.filter(Chat.session_id == session_id)
    if user_id:
        query = query.filter(Chat.user_id == user_id)

    records = query.limit(limit).all()
    return [
        ChatHistoryItem(
            id=record.id,
            session_id=record.session_id,
            user_id=record.user_id,
            message=record.message,
            response=record.response,
            model=record.model,
            mode=record.mode,
            created_at=record.created_at.isoformat(),
        )
        for record in records
    ]
