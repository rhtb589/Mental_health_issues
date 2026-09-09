"""Persistent conversations and chat messages.

A user has one active conversation. Chat messages are durable database
records and are removed only when the conversation is explicitly deleted
(or when the owning user is deleted by the database FK cascade).

Streaming responses are persisted independently of the HTTP request so a
client disconnect does not roll back the conversation.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    # Prevent two active conversations from being created for the same user.
    # An Alembic migration is required to add this constraint to an existing DB.
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_conversations_user_id"),
    )

    conversation_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )
    is_generating: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Explicit deletion of a conversation removes its messages.
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
        passive_deletes=True,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False), primary_key=True
    )
    conversation_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey(
            "conversations.conversation_id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )

    # Screening suggestion tracking. These fields belong to the actual
    # assistant message; a screening suggestion must NOT create a fake
    # assistant message in chat history.
    suggested_instrument: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    suggested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
