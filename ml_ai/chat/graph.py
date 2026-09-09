from __future__ import annotations

import logging
import time
from typing import TypedDict
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END

from ml_ai.longitudinal.classifier import classify
from ml_ai.rag.retriever import retrieve, retrieve_with_context
from ml_ai.prompts.inference import generate, generate_stream

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a compassionate mental-health support assistant.

- Be empathetic, calm, respectful, and non-judgmental.
- Do not treat the user as the owner of the conversation. You are a professional assistant providing guidance and support.
- First have a natural conversation and understand the user's concerns.
- Do not diagnose or claim the user has a disorder.
- Consider symptoms, duration, frequency, distress, and functional impact before suggesting screening.
- Once suggested a screener do not recommend another one until there is change in the user's reported symptoms or a significant time has passed. 
- Ask a brief clarifying question when important information is missing.
- Recommend screening only when it is clearly appropriate and ask permission before starting.
- Screening is not a diagnosis.
- ONLY use the screening instrument recommended in the [SCREENING_RECOMMENDATION] section.
- If no [SCREENING_RECOMMENDATION] is provided, do not suggest any screening.
- Never suggest or display any other screening instrument.
- Never invent, modify, or score screening questions. Use the application's screening/scoring engine.
- If an immediate safety concern exists, prioritize urgent professional support over routine screening.
- Do not prescribe or modify medication.
- If the application provides a SCREENING RECOMMENDATION, follow it. If none is provided, do not create one yourself.
- Do not repeatedly recommend a completed screening instrument.
- After screening scores are available act as professional health care guide with the database as your source. If information is not available in the documents respond with professional help is needed.
Flow:
Natural conversation → Understand → Clarify → Screening only if appropriate  → Screen → Explain result → give guidance until the user's concerns are addressed or data not available in pdf.
"""
INSTRUMENT_NAMES = {
    "PHQ9": "PHQ-9 (Depression Screening)",
    "GAD7": "GAD-7 (Anxiety Screening)",
    "PHQ4": "PHQ-4 (Brief Mental Health Screening)",
    "SAFE-T": "SAFE-T / C-SSRS (Suicide Risk Screening)",
}


class ChatState(TypedDict):
    user_message: str
    conversation_history: list[dict]
    screening_data: str
    classification: str
    rag_context: str
    screening_completed: bool
    screening_instrument: str | None
    screening_score: str | None
    screening_recommendation: str | None
    response: str


def _classify(state: ChatState) -> ChatState:
    result = classify(state["user_message"])
    return {"classification": result}


def _detect_screening(state: ChatState) -> ChatState:
    """Determine whether to recommend a screening instrument based on
    conversation analysis. Uses the classifier output (Anxiety/Depression/
    Suicidal/Normal) plus simple persistence/impact heuristics.

    Timing:
    - Recommend after 3+ user messages if symptoms are persistent.
    - Re-evaluate every 10 messages if the user hasn't completed screening.
    """
    classification = state["classification"].lower()
    history = state["conversation_history"]
    user_msg_count = sum(1 for m in history if m["role"] == "user") + 1

    # Already completed screening — don't suggest again
    if state.get("screening_completed"):
        return {"screening_recommendation": None}

    # Not enough messages yet
    if user_msg_count < 3:
        return {"screening_recommendation": None}

    # After initial recommendation: re-evaluate every 10 messages
    already_recommended = False
    for m in history:
        if m["role"] == "assistant" and "[SCREENING_RECOMMENDATION:" in m.get("content", ""):
            already_recommended = True
            break

    if already_recommended and user_msg_count % 10 != 0:
        return {"screening_recommendation": None}

    # Map classification to instrument (most prominent only)
    instrument_map = {
        "depression": "PHQ9",
        "anxiety": "GAD7",
        "suicidal": "SAFE-T",
    }

    # Check for persistence/impact indicators
    persistence_words = [
        "weeks", "month", "every day", "daily", "constant",
        "always", "long time", "getting worse", "affecting",
        "interfering", "struggling", "can't", "difficulty",
        "problem", "issue", "trouble", "hard", "lost interest",
        "exhausted", "tired", "sleep", "concentrate", "worry",
        "nervous", "panic", "fear", "afraid", "overwhelm",
        "hopeless", "worthless", "empty", "numb",
    ]
    combined = (state["user_message"] + " " + " ".join(m["content"] for m in history[-4:])).lower()

    for condition, instrument in instrument_map.items():
        if condition in classification:
            if any(w in combined for w in persistence_words):
                return {"screening_recommendation": instrument}

    # Fallback: if Normal but user has mentioned symptoms across multiple messages
    if classification.strip() in ("normal", ""):
        symptom_count = sum(
            1 for m in history
            if m["role"] == "user" and any(
                w in m["content"].lower()
                for w in ["depressed", "anxious", "anxiety", "depression",
                           "panic", "worry", "afraid", "suicide", "self-harm",
                           "can't sleep", "insomnia", "exhausted", "hopeless"]
            )
        )
        if symptom_count >= 2 and user_msg_count >= 4:
            # User has mentioned symptoms in 2+ messages — check which is most common
            depression_words = sum(1 for m in history if any(w in m["content"].lower() for w in ["depressed", "hopeless", "empty", "worthless", "loss of interest"]))
            anxiety_words = sum(1 for m in history if any(w in m["content"].lower() for w in ["anxious", "worry", "nervous", "panic", "fear"]))
            if anxiety_words > depression_words:
                return {"screening_recommendation": "GAD7"}
            elif depression_words > 0:
                return {"screening_recommendation": "PHQ9"}

    return {"screening_recommendation": None}


def _parse_screening_context(screening_data: str) -> tuple[bool, str | None, str | None]:
    """Parse screening data string to extract instrument and score."""
    if not screening_data:
        return False, None, None
    for line in screening_data.strip().split("\n"):
        line = line.strip()
        if not line.startswith("- "):
            continue
        instrument = line[2:].split(":")[0].strip() if ":" in line else None
        score = None
        if "Score " in line:
            score_part = line.split("Score ")[1]
            score = score_part.split("—")[0].strip() if "—" in score_part else score_part.split("(")[0].strip()
        return True, instrument, score
    return False, None, None


def _retrieve_rag(state: ChatState) -> ChatState:
    query = state["user_message"]
    screening_data = state.get("screening_data", "")

    try:
        if screening_data:
            has_screening, instrument, score = _parse_screening_context(screening_data)
            if has_screening:
                context = retrieve_with_context(query, screening_context=screening_data, n_results=5)
                return {
                    **state,
                    "rag_context": context,
                    "screening_completed": True,
                    "screening_instrument": instrument,
                    "screening_score": score,
                }

        context = retrieve(query, n_results=3)
        return {
            **state,
            "rag_context": context,
            "screening_completed": False,
            "screening_instrument": None,
            "screening_score": None,
        }
    except Exception:
        logger.exception("RAG retrieval failed, proceeding without context")
        return {
            **state,
            "rag_context": "",
            "screening_completed": False,
            "screening_instrument": None,
            "screening_score": None,
        }


def _build_messages(state: ChatState) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    context_block = f"RELEVANT KNOWLEDGE:\n{state['rag_context']}"
    classification_block = f"\n\nCONVERSATION ANALYSIS:\nThe user's message tone/content has been classified as: {state['classification']}. Use this to understand the user's emotional state."

    # Screening recommendation from the detect_screening node
    screening_rec_block = ""
    rec = state.get("screening_recommendation")
    if rec and not state.get("screening_completed"):
        name = INSTRUMENT_NAMES.get(rec, rec)
        screening_rec_block = (
            f"\n\n[SCREENING_RECOMMENDATION:{rec}] "
            f"The system has analyzed this conversation and determined that the "
            f"{name} is appropriate for this user. You MUST recommend this screening "
            f"instrument. Do NOT refuse or say you cannot recommend screening. "
            f"Explain why it may be useful based on their symptoms and ask for "
            f"their permission to proceed."
        )

    # Post-screening results block
    screening_block = ""
    if state.get("screening_data"):
        screening_block = f"\n\nSCREENING RESULTS (from the database — consider these as part of the user's clinical picture):\n{state['screening_data']}"
        if state.get("screening_completed"):
            screening_block += (
                "\n\nIMPORTANT: Use the RELEVANT KNOWLEDGE above to provide self-help "
                "strategies, coping techniques, and evidence-based guidance. Only "
                "recommend professional support if the knowledge base does not contain "
                "a suitable resource for the user's specific situation, or if the "
                "screening score indicates severe/high-risk symptoms."
            )

    messages.append({
        "role": "system",
        "content": context_block + classification_block + screening_rec_block + screening_block,
    })

    for msg in state["conversation_history"]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": state["user_message"]})
    return messages


def _generate(state: ChatState) -> ChatState:
    messages = _build_messages(state)
    reply = generate(messages, max_new_tokens=256, temperature=0.7)
    return {"response": reply}


def _build_graph():
    graph = StateGraph(ChatState)
    graph.add_node("classify", _classify)
    graph.add_node("detect_screening", _detect_screening)
    graph.add_node("retrieve_rag", _retrieve_rag)
    graph.add_node("generate", _generate)
    graph.set_entry_point("classify")
    graph.add_edge("classify", "detect_screening")
    graph.add_edge("detect_screening", "retrieve_rag")
    graph.add_edge("retrieve_rag", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def run_chat_graph(user_message: str, conversation_history: list[dict] | None = None, screening_data: str = "") -> str:
    result = _get_graph().invoke({
        "user_message": user_message,
        "conversation_history": conversation_history or [],
        "screening_data": screening_data,
        "classification": "",
        "rag_context": "",
        "screening_completed": False,
        "screening_instrument": None,
        "screening_score": None,
        "screening_recommendation": None,
        "response": "",
    })
    return result["response"]


def run_chat_graph_stream(user_message: str, conversation_history: list[dict] | None = None, screening_data: str = ""):
    total_start = time.perf_counter()
    print("\n========== CHAT PIPELINE ==========")

    state = {
        "user_message": user_message,
        "conversation_history": conversation_history or [],
        "screening_data": screening_data,
        "classification": "",
        "rag_context": "",
        "screening_completed": False,
        "screening_instrument": None,
        "screening_score": None,
        "screening_recommendation": None,
        "response": "",
    }

    t = time.perf_counter()
    state = _get_graph().invoke(state)
    graph_time = time.perf_counter() - t
    print(f"[1] Graph (classify+detect+retrieve+build): {graph_time:.2f}s")
    print(f"    Classification: {state['classification']}")
    print(f"    Screening rec:  {state.get('screening_recommendation', 'None')}")

    t = time.perf_counter()
    messages = _build_messages(state)
    prompt_time = time.perf_counter() - t
    print(f"[2] Prompt assembly:  {prompt_time:.4f}s")

    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    t = time.perf_counter()
    print("[3] Starting LLM streaming...")
    yield from generate_stream(messages, max_new_tokens=512, temperature=0.7)
    gen_time = time.perf_counter() - t
    print(f"[3] LLM streaming:    {gen_time:.2f}s")

    total_time = time.perf_counter() - total_start
    print(f"[TOTAL]               {total_time:.2f}s")
    print("====================================\n")


def get_screening_summary(
    db,
    user_id: str,
    suggested_after: datetime | None = None,
    instrument_id: str | None = None,
) -> str:
    """Fetch completed screening assessments, optionally filtered by
    suggestion timestamp and instrument."""
    from sqlalchemy import select
    from app.models.assessment import Assessment
    from app.security.encryption import FieldEncryptor

    query = (
        select(Assessment)
        .where(Assessment.user_id == user_id)
        .where(Assessment.status == "completed")
    )

    if suggested_after:
        query = query.where(Assessment.completed_at > suggested_after)
    if instrument_id:
        query = query.where(Assessment.instrument_id == instrument_id)

    query = query.order_by(Assessment.completed_at.desc()).limit(10)
    assessments = db.execute(query).scalars().all()

    if not assessments:
        return ""

    encryptor = FieldEncryptor()
    lines = []
    instrument_names = {
        "PHQ9": "PHQ-9 (Depression)",
        "GAD7": "GAD-7 (Anxiety)",
        "PHQ4": "PHQ-4 (Brief)",
        "SAFE-T": "SAFE-T / C-SSRS (Suicide Risk)",
    }

    for a in assessments:
        name = instrument_names.get(a.instrument_id, a.instrument_id)
        score = encryptor.decrypt(a.encrypted_score) if a.encrypted_score else "N/A"
        interpretation = encryptor.decrypt(a.encrypted_interpretation) if a.encrypted_interpretation else "N/A"
        completed = a.completed_at.strftime("%Y-%m-%d %H:%M") if a.completed_at else "unknown"
        lines.append(f"- {name}: Score {score} — {interpretation} (completed {completed})")

    return "\n".join(lines)
