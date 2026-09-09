from __future__ import annotations

from pydantic import BaseModel


class ChatSend(BaseModel):
    content: str


class ScreeningSuggested(BaseModel):
    instrument_id: str


class ChatMessageOut(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: str


class ConversationOut(BaseModel):
    conversation_id: str
    messages: list[ChatMessageOut]
    is_generating: bool = False
    created_at: str
    updated_at: str
