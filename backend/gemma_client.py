"""
Async wrapper around the Google Gemini API using the google-generativeai SDK.

The class is named GemmaClient to keep the rest of the codebase unchanged —
it calls Gemini models (gemini-2.0-flash by default) which are Google's
hosted Gemma-family models.

Docs: https://ai.google.dev/gemini-api/docs
"""

import logging
from typing import AsyncIterator

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from google.api_core.exceptions import GoogleAPIError

from .config import get_settings

logger = logging.getLogger(__name__)

# Relax safety filters for language-learning content so corrections on
# sensitive vocabulary don't get blocked.
_SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH:        HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:  HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:  HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

_GENERATION_CONFIG = genai.types.GenerationConfig(
    temperature=0.7,
    top_p=0.9,
    max_output_tokens=1024,
)


class GemmaClient:
    """Thin async-friendly wrapper around google-generativeai."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Get a free key at https://aistudio.google.com/app/apikey "
                "and add it to your .env file."
            )
        genai.configure(api_key=settings.gemini_api_key)
        self._model_name = settings.gemini_model
        self._model = genai.GenerativeModel(
            model_name=self._model_name,
            generation_config=_GENERATION_CONFIG,
            safety_settings=_SAFETY_SETTINGS,
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def chat(self, messages: list[dict]) -> str:
        """
        Send a list of OpenAI-style messages (role/content dicts) to Gemini
        and return the full assistant reply as a string.

        The first message with role='system' is extracted and passed as
        system_instruction; the rest become the conversation history.
        """
        system_instruction, history, last_user_msg = _split_messages(messages)

        # Re-initialise with system instruction if provided
        model = genai.GenerativeModel(
            model_name=self._model_name,
            generation_config=_GENERATION_CONFIG,
            safety_settings=_SAFETY_SETTINGS,
            system_instruction=system_instruction or None,
        )

        # Build Gemini-format history (all turns except the last user message)
        gemini_history = [
            {"role": _map_role(m["role"]), "parts": [m["content"]]}
            for m in history
        ]

        chat_session = model.start_chat(history=gemini_history)

        try:
            response = await chat_session.send_message_async(last_user_msg)
            return response.text
        except GoogleAPIError as exc:
            raise RuntimeError(f"Gemini API error: {exc}") from exc

    async def is_reachable(self) -> bool:
        """Quick connectivity check — lists available models."""
        try:
            models = [m async for m in await _list_models_async()]
            return len(models) >= 0  # any response (even empty) means reachable
        except Exception:
            # Fallback: try a tiny generation
            try:
                model = genai.GenerativeModel(self._model_name)
                await model.generate_content_async("hi")
                return True
            except Exception:
                return False

    async def aclose(self) -> None:
        """No persistent connection to close with the REST SDK."""
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_messages(messages: list[dict]) -> tuple[str, list[dict], str]:
    """
    Split an OpenAI-style message list into:
      - system_instruction (str)
      - history (all messages except the final user turn)
      - last_user_msg (str) — the message to send now
    """
    system_instruction = ""
    rest: list[dict] = []

    for m in messages:
        if m["role"] == "system":
            system_instruction = m["content"]
        else:
            rest.append(m)

    if not rest:
        raise ValueError("No user message found in message list.")

    last = rest[-1]
    if last["role"] != "user":
        raise ValueError("Last non-system message must be from 'user'.")

    history = rest[:-1]
    return system_instruction, history, last["content"]


def _map_role(role: str) -> str:
    """Map OpenAI roles to Gemini roles ('user' | 'model')."""
    return "model" if role == "assistant" else "user"


async def _list_models_async():
    """Async generator wrapper around genai.list_models()."""
    import asyncio
    loop = asyncio.get_event_loop()
    models = await loop.run_in_executor(None, lambda: list(genai.list_models()))
    return iter(models)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_client: GemmaClient | None = None


def get_client() -> GemmaClient:
    global _client
    if _client is None:
        _client = GemmaClient()
    return _client
