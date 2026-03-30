from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import verify_service_api_key
from app.db.database import get_db
from app.models.chat_model import Chat
from app.services.ai_service import AIServiceError, ai_studio_service


router = APIRouter(tags=["odoo-compat"])


class OdooCompatChatRequest(BaseModel):
    message: str = Field(min_length=1)


class OdooStudioSendRequest(BaseModel):
    message: str = Field(min_length=1)
    mode: str = "groq"
    history: str = "[]"
    slave_step: int = 0
    slave_data: str = "{}"


def _map_odoo_mode(mode: str) -> tuple[str, str]:
    if mode == "pipeline":
        return "groq", "pipeline"
    if mode == "hotel_data":
        return "groq", "knowledge"
    return "groq", "general"


@router.post("/ai/chat")
def odoo_ai_chat(
    req: OdooCompatChatRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_service_api_key),
):
    response = ai_studio_service.generate_response(
        message=req.message.strip(),
        provider="groq",
        mode="pipeline",
        history=[],
        context=None,
    )
    record = Chat(
        user_id="odoo-user",
        message=req.message.strip(),
        response=response,
        model="groq",
        mode="pipeline",
        session_id="odoo-ai-chat",
    )
    db.add(record)
    db.commit()
    return {"reply": response}


@router.post("/ai_studio/send")
def odoo_ai_studio_send(
    req: OdooStudioSendRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_service_api_key),
):
    if req.mode == "slave":
        return {
            "response": "Slave mode is not implemented in the standalone backend yet.",
            "slave_step": req.slave_step or 0,
            "slave_data": req.slave_data or "{}",
            "done": False,
            "error": True,
        }

    provider, backend_mode = _map_odoo_mode(req.mode)
    context = None
    if req.mode == "hotel_data":
        context = "Hotel-specific context was requested by Odoo, but no hotel data provider is configured in the standalone backend."

    try:
        response = ai_studio_service.generate_response(
            message=req.message.strip(),
            provider=provider,
            mode=backend_mode,
            history=[],
            context=context,
        )
    except AIServiceError as exc:
        return {
            "response": str(exc),
            "slave_step": req.slave_step or 0,
            "slave_data": req.slave_data or "{}",
            "done": False,
            "error": True,
        }

    record = Chat(
        user_id="odoo-user",
        message=req.message.strip(),
        response=response,
        model=provider,
        mode=backend_mode,
        session_id="odoo-ai-studio-send",
    )
    db.add(record)
    db.commit()
    return {"response": response}
