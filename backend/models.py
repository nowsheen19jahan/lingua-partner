from enum import Enum
from pydantic import BaseModel, Field


class Role(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(BaseModel):
    role: Role
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        description="Client-generated UUID that identifies the conversation session.",
    )
    message: str = Field(..., min_length=1, max_length=4000)
    target_language: str = Field(
        default="Spanish",
        description="The language the user wants to practise.",
    )
    native_language: str = Field(
        default="English",
        description="The user's native language (used for explanations).",
    )
    mode: str = Field(
        default="conversation",
        description="Either 'conversation' or 'correction'.",
    )


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    corrections: list[str] = Field(
        default_factory=list,
        description="List of grammar/spelling corrections when mode='correction'.",
    )
    mode: str


class GrammarRequest(BaseModel):
    session_id: str
    text: str = Field(..., min_length=1, max_length=4000)
    target_language: str = "Spanish"
    native_language: str = "English"


class GrammarResponse(BaseModel):
    original: str
    corrected: str
    corrections: list[str]
    explanation: str


class HealthResponse(BaseModel):
    status: str
    api_reachable: bool
    model: str
