import logging
import re

from fastapi import APIRouter, HTTPException

from ..gemma_client import get_client
from ..models import ChatRequest, ChatResponse
from ..prompts import conversation_system_prompt, correction_system_prompt
from ..session_store import append_message, clear_history, get_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Main conversational endpoint.

    Modes
    -----
    conversation : immersive back-and-forth practice
    correction   : grammar/spelling check with structured feedback
    """
    client = get_client()

    # Build system prompt based on mode
    if req.mode == "correction":
        system_prompt = correction_system_prompt(req.target_language, req.native_language)
    else:
        system_prompt = conversation_system_prompt(req.target_language, req.native_language)

    # Retrieve history and append the new user message
    history = get_history(req.session_id)
    append_message(req.session_id, "user", req.message)

    # Assemble the full message list for Gemini
    messages = [{"role": "system", "content": system_prompt}] + history + [
        {"role": "user", "content": req.message}
    ]

    try:
        reply = await client.chat(messages)
    except RuntimeError as exc:
        logger.error("Gemma request failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))

    # Persist the assistant reply
    append_message(req.session_id, "assistant", reply)

    # Parse structured corrections out of correction-mode replies
    corrections: list[str] = []
    if req.mode == "correction":
        corrections = _parse_corrections(reply)

    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        corrections=corrections,
        mode=req.mode,
    )


@router.delete("/{session_id}", status_code=204)
async def reset_session(session_id: str) -> None:
    """Clear conversation history for a session (user hits 'New Chat')."""
    clear_history(session_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CORRECTIONS_RE = re.compile(
    r"CORRECTIONS:\s*\n(.*?)(?:\nEXPLANATION:|\Z)", re.DOTALL | re.IGNORECASE
)


def _parse_corrections(reply: str) -> list[str]:
    """Extract bullet-point corrections from a correction-mode reply."""
    match = _CORRECTIONS_RE.search(reply)
    if not match:
        return []
    block = match.group(1).strip()
    lines = [line.lstrip("•-* ").strip() for line in block.splitlines() if line.strip()]
    return [l for l in lines if l and l.lower() != "no errors found."]
