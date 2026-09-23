from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, description="Chat message text")


@router.get("/")
async def get_chat_status():
    """Return status of the chat router."""
    return {"status": "chat router is ready"}


@router.post("/")
async def send_chat(payload: ChatMessage):
    """Receive chat message and return response."""
    return {
        "reply": f"Echo: {payload.message}",
        "status": "success",
    }
