from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatSend, ScreeningSuggested, ChatMessageOut, ConversationOut
from app.security.permissions import get_current_principal, Principal
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


def _msg_out(m) -> ChatMessageOut:
    return ChatMessageOut(
        message_id=m.message_id,
        role=m.role,
        content=m.content,
        created_at=m.created_at.isoformat() if m.created_at else "",
    )


def _conv_out(conv) -> ConversationOut:
    return ConversationOut(
        conversation_id=conv.conversation_id,
        messages=[_msg_out(m) for m in conv.messages],
        is_generating=getattr(conv, "is_generating", False),
        created_at=conv.created_at.isoformat() if conv.created_at else "",
        updated_at=conv.updated_at.isoformat() if conv.updated_at else "",
    )


@router.get("", response_model=ConversationOut)
def get_conversation(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    conv = chat_service.get_or_create_conversation(db, principal.user_id)
    db.commit()
    return _conv_out(conv)


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def send_message(
    payload: ChatSend,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    conv = chat_service.get_or_create_conversation(db, principal.user_id)
    chat_service.send_message(db, conv.conversation_id, principal.user_id, payload.content)
    db.commit()
    db.refresh(conv)
    return _conv_out(conv)


@router.post("/stream")
def send_message_stream(
    payload: ChatSend,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    conv = chat_service.get_or_create_conversation(db, principal.user_id)
    db.commit()

    def event_generator():
        for chunk in chat_service.send_message_stream(
            db, conv.conversation_id, principal.user_id, payload.content
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
        db.commit()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    conv = chat_service.get_or_create_conversation(db, principal.user_id)
    chat_service.delete_conversation(db, conv.conversation_id, principal.user_id)
    db.commit()


@router.post("/screening-suggested", status_code=status.HTTP_200_OK)
def record_screening_suggested(
    payload: ScreeningSuggested,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    """Record that the assistant suggested a screening instrument in the current conversation.
    This enables filtering assessments to only those completed AFTER the suggestion."""
    conv = chat_service.get_or_create_conversation(db, principal.user_id)
    chat_service.record_screening_suggestion(db, conv.conversation_id, payload.instrument_id)
    db.commit()
    return {"detail": "ok"}
