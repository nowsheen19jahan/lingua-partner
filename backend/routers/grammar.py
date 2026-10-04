import logging
import re

from fastapi import APIRouter, HTTPException

from ..gemma_client import get_client
from ..models import GrammarRequest, GrammarResponse
from ..prompts import correction_system_prompt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/grammar", tags=["grammar"])


@router.post("", response_model=GrammarResponse)
async def check_grammar(req: GrammarRequest) -> GrammarResponse:
    """
    Standalone grammar-check endpoint — does not affect conversation history.
    Returns a structured diff of corrections plus an explanation.
    """
    client = get_client()

    system_prompt = correction_system_prompt(req.target_language, req.native_language)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.text},
    ]

    try:
        reply = await client.chat(messages)
    except RuntimeError as exc:
        logger.error("Grammar check failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))

    corrected, corrections, explanation = _parse_reply(reply, req.text)

    return GrammarResponse(
        original=req.text,
        corrected=corrected,
        corrections=corrections,
        explanation=explanation,
    )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_CORRECTED_RE = re.compile(r"CORRECTED:\s*\n(.*?)(?:\nCORRECTIONS:|\Z)", re.DOTALL | re.IGNORECASE)
_CORRECTIONS_RE = re.compile(r"CORRECTIONS:\s*\n(.*?)(?:\nEXPLANATION:|\Z)", re.DOTALL | re.IGNORECASE)
_EXPLANATION_RE = re.compile(r"EXPLANATION:\s*\n(.*)", re.DOTALL | re.IGNORECASE)


def _parse_reply(reply: str, original: str) -> tuple[str, list[str], str]:
    corrected_match = _CORRECTED_RE.search(reply)
    corrections_match = _CORRECTIONS_RE.search(reply)
    explanation_match = _EXPLANATION_RE.search(reply)

    corrected = corrected_match.group(1).strip() if corrected_match else original
    explanation = explanation_match.group(1).strip() if explanation_match else ""

    corrections: list[str] = []
    if corrections_match:
        block = corrections_match.group(1).strip()
        lines = [line.lstrip("•-* ").strip() for line in block.splitlines() if line.strip()]
        corrections = [l for l in lines if l and l.lower() != "no errors found."]

    return corrected, corrections, explanation
