"""Data models — lesson state and LLM response schemas.

All mutable session data lives in ``LessonState``.
LLM response contracts are modelled as separate Pydantic schemas so that
``llm_client`` can validate every response before business logic touches it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# Lesson state enums 

class Phase(str, Enum):
    """Top-level lesson phase."""
    GREETING = "greeting"
    VOCABULARY = "vocabulary"
    FAREWELL = "farewell"
    ENDED = "ended"


class SubPhase(str, Enum):
    """Sub-phase within the VOCABULARY phase."""
    INTRODUCE = "introduce"
    PRACTICE = "practice"


class EvalStatus(str, Enum):
    """LLM evaluation of a child's vocabulary attempt."""
    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"
    OFF_TOPIC = "off_topic"
    SILENCE = "silence"


# Conversation history 

class Message(BaseModel):
    role: str  # "charlie" | "child"
    text: str


# Session state

class LessonState(BaseModel):
    """Complete snapshot of a lesson session.

    Designed to be serialisable (e.g. to Redis / DB) so the service can
    be stateless between HTTP requests.
    """
    phase: Phase = Phase.GREETING
    sub_phase: SubPhase = SubPhase.INTRODUCE
    word_index: int = 0
    attempt: int = 0
    words: list[str] = Field(default_factory=list)
    history: list[Message] = Field(default_factory=list)
    greeting_sent: bool = False


# LLM response schemas 

class CharlieMessage(BaseModel):
    """Generic single-message response from Charlie."""
    message: str


class EvalResponse(BaseModel):
    """Structured evaluation of a child's vocabulary attempt."""
    status: EvalStatus
    confidence: float = Field(ge=0.0, le=1.0)
    message: str
