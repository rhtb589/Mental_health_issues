"""Durable chat conversation service.

Important persistence guarantees:
- User messages are committed before LLM inference starts.
- Assistant messages are persisted independently of the HTTP request.
- Streaming generation continues in a background worker if the browser
  disconnects.
- The final assistant response is committed in its own DB transaction.
- Screening suggestions update the real assistant message rather than
  inserting a synthetic "[System: ...]" message into chat history.
- Conversation history is deleted only by delete_conversation().
"""
from __future__ import annotations

import logging
import queue
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.conversation import Conversation, ChatMessage

logger = logging.getLogger(__name__)

GREETING = "Hello! I'm here to support you. How are you feeling today?"

# Persist partial streamed responses at most once per interval. This avoids
# a database UPDATE for every generated token while still giving useful
# crash/disconnect durability.
STREAM_CHECKPOINT_SECONDS = 0.75


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_message_id() -> str:
    return str(uuid.uuid4())


def get_or_create_conversation(db: Session, user_id: str) -> Conversation:
    """Return the user's single conversation, creating it if necessary.

    The unique DB constraint on conversations.user_id protects against two
    concurrent requests creating two conversations for the same user.
    """
    existing = db.execute(
        select(Conversation)
        .options(joinedload(Conversation.messages))
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    ).unique().scalars().first()

    if existing:
        return existing

    conv = Conversation(
        conversation_id=str(uuid.uuid4()),
        user_id=user_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(conv)

    try:
        db.flush()
    except IntegrityError:
        # Another request won the race. Roll back this failed INSERT and
        # retrieve the conversation that now exists.
        db.rollback()
        existing = db.execute(
            select(Conversation)
            .options(joinedload(Conversation.messages))
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
        ).unique().scalars().first()
        if existing:
            return existing
        raise

    greeting = ChatMessage(
        message_id=_new_message_id(),
        conversation_id=conv.conversation_id,
        role="assistant",
        content=GREETING,
        created_at=_utcnow(),
    )
    db.add(greeting)

    # Conversation creation is a durable operation. Do not leave the
    # greeting/user conversation only in the request transaction.
    db.commit()

    # Re-query so the caller receives a clean, persistent object.
    return db.execute(
        select(Conversation)
        .options(joinedload(Conversation.messages))
        .where(Conversation.conversation_id == conv.conversation_id)
    ).unique().scalar_one()


def _get_history(
    db: Session,
    conversation_id: str,
    exclude_msg_id: str | None = None,
) -> list[dict]:
    query = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at, ChatMessage.message_id)
    )

    messages = db.execute(query).scalars().all()

    return [
        {"role": m.role, "content": m.content}
        for m in messages
        if m.message_id != exclude_msg_id
    ]


def _get_screening_data(
    db: Session,
    user_id: str,
    conversation_id: str,
) -> str:
    """Fetch completed screening results for the user."""
    try:
        from ml_ai.chat.graph import get_screening_summary
        return get_screening_summary(db, user_id)
    except Exception:
        logger.exception("Could not load screening summary")
        return ""


def record_screening_suggestion(
    db: Session,
    conversation_id: str,
    instrument_id: str,
) -> None:
    """Attach a screening suggestion to the latest real assistant message.

    Previously this function inserted a fake assistant message containing
    '[System: Screening suggested ...]'. That polluted the actual chat
    history and could be sent back to the LLM as if it were an assistant
    response. Now the suggestion is metadata on the real response.
    """
    now = _utcnow()

    msg = db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.role == "assistant",
        )
        .order_by(ChatMessage.created_at.desc(), ChatMessage.message_id.desc())
        .limit(1)
    ).scalar_one_or_none()

    if msg is None:
        logger.warning(
            "Cannot record screening suggestion: no assistant message "
            "for conversation %s",
            conversation_id,
        )
        return

    msg.suggested_instrument = instrument_id
    msg.suggested_at = now

    conv = db.get(Conversation, conversation_id)
    if conv:
        conv.updated_at = now

    db.commit()


def _persist_user_message(
    user_id: str,
    conversation_id: str,
    content: str,
) -> ChatMessage:
    """Persist a user message using an independent transaction.

    This guarantees that the user message is not lost if the HTTP streaming
    request is cancelled, times out, or the request-scoped DB transaction is
    rolled back later.
    """
    from app.core.database import SessionLocal

    save_db = SessionLocal()
    try:
        msg = ChatMessage(
            message_id=_new_message_id(),
            conversation_id=conversation_id,
            role="user",
            content=content,
            created_at=_utcnow(),
        )
        save_db.add(msg)

        conv = save_db.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            raise ValueError("Conversation does not belong to user")

        conv.updated_at = _utcnow()
        save_db.commit()

        # Detach the object before closing the session.
        save_db.refresh(msg)
        return msg
    except Exception:
        save_db.rollback()
        raise
    finally:
        save_db.close()


def send_message(
    db: Session,
    conversation_id: str,
    user_id: str,
    content: str,
) -> tuple[ChatMessage, ChatMessage]:
    """Send and durably save a non-streaming message pair."""
    # Persist the user message BEFORE inference. The request cannot lose it
    # if the LLM fails.
    user_msg = _persist_user_message(user_id, conversation_id, content)

    # Use a fresh session for history so it sees the committed message state.
    history = _get_history(db, conversation_id)
    # Do not send the current user message twice.
    history = history[:-1] if history and history[-1]["role"] == "user" else history

    screening_data = _get_screening_data(db, user_id, conversation_id)

    try:
        from ml_ai.chat.graph import run_chat_graph

        save_db_gen = SessionLocal()
        try:
            conv = save_db_gen.get(Conversation, conversation_id)
            if conv:
                conv.is_generating = True
                save_db_gen.commit()
        finally:
            save_db_gen.close()

        reply_text = run_chat_graph(
            user_message=content,
            conversation_history=history,
            screening_data=screening_data,
        )
    except Exception:
        logger.exception("LLM pipeline failed, using fallback reply")
        reply_text = (
            "I'm here to help. Could you tell me more about what you're "
            "experiencing?"
        )
    finally:
        save_db_gen = SessionLocal()
        try:
            conv = save_db_gen.get(Conversation, conversation_id)
            if conv:
                conv.is_generating = False
                save_db_gen.commit()
        finally:
            save_db_gen.close()

    # Persist assistant response in its own transaction.
    from app.core.database import SessionLocal

    save_db = SessionLocal()
    try:
        assistant_msg = ChatMessage(
            message_id=_new_message_id(),
            conversation_id=conversation_id,
            role="assistant",
            content=reply_text,
            created_at=_utcnow(),
        )
        save_db.add(assistant_msg)

        conv = save_db.get(Conversation, conversation_id)
        if conv:
            conv.updated_at = _utcnow()

        save_db.commit()
        save_db.refresh(assistant_msg)
        return user_msg, assistant_msg
    except Exception:
        save_db.rollback()
        logger.exception("Failed to persist assistant response")
        raise
    finally:
        save_db.close()


def send_message_stream(
    db: Session,
    conversation_id: str,
    user_id: str,
    content: str,
):
    """Generate a response while making conversation persistence independent
    of the HTTP connection.

    The user message is committed before generation starts. An assistant
    message is created and committed before generation starts as well, then
    its content is checkpointed during generation and finalized at the end.

    Therefore a browser disconnect does not delete either side of the
    conversation.
    """
    # ---- 1. Persist the user message immediately -------------------------
    user_msg = _persist_user_message(user_id, conversation_id, content)

    # ---- 2. Build LLM context from committed DB state --------------------
    history = _get_history(db, conversation_id)

    # The current user message is already included in DB history. The graph
    # receives it separately, so remove only this exact newly-created row.
    if history:
        for i in range(len(history) - 1, -1, -1):
            if history[i]["role"] == "user" and history[i]["content"] == content:
                history.pop(i)
                break

    screening_data = _get_screening_data(db, user_id, conversation_id)

    token_queue: queue.Queue[str | None] = queue.Queue()

    def _run_and_save():
        """Background worker.

        This worker owns its DB sessions. It does not depend on the request
        session remaining alive.
        """
        from app.core.database import SessionLocal

        full_reply: list[str] = []
        assistant_id = _new_message_id()

        # Create the assistant row BEFORE generation. This prevents an
        # assistant response from existing only in RAM.
        save_db = SessionLocal()
        try:
            conv = save_db.get(Conversation, conversation_id)
            if conv:
                conv.is_generating = True
                conv.updated_at = _utcnow()

            assistant_msg = ChatMessage(
                message_id=assistant_id,
                conversation_id=conversation_id,
                role="assistant",
                content="",
                created_at=_utcnow(),
            )
            save_db.add(assistant_msg)
            save_db.commit()
        except Exception:
            save_db.rollback()
            logger.exception("Failed to create persistent assistant message")
            save_db.close()
            token_queue.put(
                "I'm here to help. Could you tell me more about what you're "
                "experiencing?"
            )
            token_queue.put(None)
            return
        finally:
            save_db.close()

        last_checkpoint = time.monotonic()

        try:
            from ml_ai.chat.graph import run_chat_graph_stream

            for chunk in run_chat_graph_stream(
                user_message=content,
                conversation_history=history,
                screening_data=screening_data,
            ):
                if not chunk:
                    continue

                full_reply.append(chunk)
                token_queue.put(chunk)

                # Checkpoint the accumulated assistant response periodically.
                # This is independent of the HTTP client and survives client
                # disconnects.
                now = time.monotonic()
                if now - last_checkpoint >= STREAM_CHECKPOINT_SECONDS:
                    checkpoint_text = "".join(full_reply)

                    checkpoint_db = SessionLocal()
                    try:
                        msg = checkpoint_db.get(ChatMessage, assistant_id)
                        if msg:
                            msg.content = checkpoint_text
                            conv = checkpoint_db.get(
                                Conversation,
                                conversation_id,
                            )
                            if conv:
                                conv.updated_at = _utcnow()
                            checkpoint_db.commit()
                        last_checkpoint = now
                    except Exception:
                        checkpoint_db.rollback()
                        logger.exception(
                            "Failed to checkpoint assistant response"
                        )
                    finally:
                        checkpoint_db.close()

        except Exception:
            logger.exception("LLM stream failed, using fallback reply")

            # Only replace the empty response with fallback if nothing was
            # generated. If partial text exists, preserve it.
            if not full_reply:
                fallback = (
                    "I'm here to help. Could you tell me more about what "
                    "you're experiencing?"
                )
                full_reply.append(fallback)
                token_queue.put(fallback)

        finally:
            # Final durable commit. This happens even if the browser has
            # disconnected because the worker is independent of the request.
            reply_text = "".join(full_reply)

            final_db = SessionLocal()
            try:
                msg = final_db.get(ChatMessage, assistant_id)
                if msg:
                    msg.content = reply_text
                
                conv = final_db.get(Conversation, conversation_id)
                if conv:
                    conv.is_generating = False
                    conv.updated_at = _utcnow()
                
                final_db.commit()
            except Exception:
                final_db.rollback()
                logger.exception(
                    "Failed to finalize assistant response in DB"
                )
            finally:
                final_db.close()

            token_queue.put(None)

    # Non-daemon: do not abandon a database persistence worker simply because
    # the HTTP client disconnected. A process shutdown/crash is different and
    # cannot be made lossless by Python alone.
    thread = threading.Thread(
        target=_run_and_save,
        name=f"chat-stream-{conversation_id[:8]}",
        daemon=False,
    )
    thread.start()

    # ---- 3. Stream to the HTTP client -----------------------------------
    # If the browser disconnects, the generator may stop being consumed, but
    # the background worker keeps running and saving the conversation.
    while True:
        try:
            token = token_queue.get(timeout=120)
            if token is None:
                break
            yield token
        except queue.Empty:
            logger.warning(
                "No chat token received for 120 seconds; "
                "continuing to wait for background worker"
            )
            continue


def delete_conversation(
    db: Session,
    conversation_id: str,
    user_id: str,
) -> bool:
    """The ONLY application-level operation that removes chat history."""
    conv = db.get(Conversation, conversation_id)

    if conv is None or conv.user_id != user_id:
        return False

    db.delete(conv)
    db.commit()

    # The FK cascade plus ORM delete-orphan removes all messages.
    return True
