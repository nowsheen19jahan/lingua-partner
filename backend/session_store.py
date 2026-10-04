"""
In-memory conversation history keyed by session_id.

For a production deployment you'd swap this for Redis, but for a
single-instance Render service this works perfectly fine.
"""

from collections import defaultdict, deque

from .config import get_settings

# { session_id: deque of {"role": ..., "content": ...} }
_store: dict[str, deque] = defaultdict(lambda: deque(maxlen=get_settings().max_history_turns * 2))


def get_history(session_id: str) -> list[dict]:
    """Return the conversation history for a session as a plain list."""
    return list(_store[session_id])


def append_message(session_id: str, role: str, content: str) -> None:
    """Append a single message to a session's history."""
    _store[session_id].append({"role": role, "content": content})


def clear_history(session_id: str) -> None:
    """Wipe the history for a session (e.g. when the user resets)."""
    _store[session_id].clear()


def session_exists(session_id: str) -> bool:
    return session_id in _store and len(_store[session_id]) > 0
