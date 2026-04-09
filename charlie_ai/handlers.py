"""Phase handlers — one class per lesson phase.

Each handler receives the current ``LessonState`` and the child's text input,
then returns ``(charlie_reply, updated_state)``.

Handlers are intentionally **stateless**: all mutable context lives in
``LessonState``.  This makes sessions trivially serialisable and testable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from . import prompts
from .config import settings
from .llm_client import LLMClient
from .models import (
    CharlieMessage,
    EvalResponse,
    EvalStatus,
    LessonState,
    Message,
    Phase,
    SubPhase,
)


class PhaseHandler(ABC):
    """Abstract base for lesson-phase handlers."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    @abstractmethod
    async def handle(
        self, state: LessonState, user_input: str
    ) -> tuple[str, LessonState]:
        """Process *user_input* and return ``(charlie_text, new_state)``."""


# Greeting 

class GreetingHandler(PhaseHandler):
    """Manages the opening greeting exchange.

    Turn 1 (``greeting_sent=False``): Charlie introduces himself.
    Turn 2 (``greeting_sent=True``):  Charlie acknowledges the child's
    response and introduces the first vocabulary word, transitioning into
    the VOCABULARY / PRACTICE phase.
    """

    async def handle(
        self, state: LessonState, user_input: str
    ) -> tuple[str, LessonState]:
        if not state.greeting_sent:
            resp = await self.llm.generate(
                prompts.greeting(state.words),
                CharlieMessage,
            )
            state.greeting_sent = True
            state.history.append(Message(role="charlie", text=resp.message))
            return resp.message, state

        # Child responded (or was silent) — acknowledge + introduce word #1.
        state.history.append(Message(role="child", text=user_input))
        resp = await self.llm.generate(
            prompts.greeting_reply(user_input, state.words[0]),
            CharlieMessage,
        )
        state.phase = Phase.VOCABULARY
        state.sub_phase = SubPhase.PRACTICE  # word was introduced in reply
        state.attempt = 0
        state.history.append(Message(role="charlie", text=resp.message))
        return resp.message, state


# Vocabulary 

class VocabularyHandler(PhaseHandler):
    """Manages word introduction and practice cycles.

    Sub-phases:
      INTRODUCE — Charlie presents a new word (no user input needed).
      PRACTICE  — Child attempts the word; LLM evaluates.

    After evaluation the handler advances ``word_index`` when the child
    succeeds or exhausts all attempts.
    """

    async def handle(
        self, state: LessonState, user_input: str
    ) -> tuple[str, LessonState]:
        if state.sub_phase == SubPhase.INTRODUCE:
            return await self._introduce(state)
        return await self._practice(state, user_input)

    # private 

    async def _introduce(
        self, state: LessonState
    ) -> tuple[str, LessonState]:
        word = state.words[state.word_index]
        resp = await self.llm.generate(
            prompts.word_intro(
                word, state.word_index + 1, len(state.words)
            ),
            CharlieMessage,
        )
        state.sub_phase = SubPhase.PRACTICE
        state.attempt = 0
        state.history.append(Message(role="charlie", text=resp.message))
        return resp.message, state

    async def _practice(
        self, state: LessonState, user_input: str
    ) -> tuple[str, LessonState]:
        state.history.append(Message(role="child", text=user_input))
        word = state.words[state.word_index]
        state.attempt += 1

        resp = await self.llm.generate(
            prompts.evaluate_attempt(
                word,
                user_input,
                state.attempt,
                settings.max_attempts_per_word,
            ),
            EvalResponse,
            temperature=0.3,  # low temp → consistent evaluation
        )
        state.history.append(Message(role="charlie", text=resp.message))

        if (
            resp.status == EvalStatus.CORRECT
            or state.attempt >= settings.max_attempts_per_word
        ):
            self._advance_word(state)

        return resp.message, state

    @staticmethod
    def _advance_word(state: LessonState) -> None:
        """Move to the next word, or to FAREWELL if all words are done."""
        state.word_index += 1
        state.attempt = 0
        if state.word_index >= len(state.words):
            state.phase = Phase.FAREWELL
        else:
            state.sub_phase = SubPhase.INTRODUCE


# Farewell 

class FarewellHandler(PhaseHandler):
    """Wraps up the lesson with a warm goodbye."""

    async def handle(
        self, state: LessonState, user_input: str
    ) -> tuple[str, LessonState]:
        resp = await self.llm.generate(
            prompts.farewell(state.words),
            CharlieMessage,
        )
        state.phase = Phase.ENDED
        state.history.append(Message(role="charlie", text=resp.message))
        return resp.message, state
