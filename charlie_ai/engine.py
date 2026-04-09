"""Lesson engine — the single entry-point for processing conversation turns.

The engine:
1. Routes each user turn to the appropriate ``PhaseHandler``.
2. **Auto-advances** through phases that need no user input (word
   introductions, farewell) so that every ``process()`` call returns a
   complete, displayable Charlie reply.
3. Catches unexpected errors and returns a safe fallback so the lesson
   never crashes from the child's perspective.
"""

from __future__ import annotations

import logging

from .handlers import (
    FarewellHandler,
    GreetingHandler,
    PhaseHandler,
    VocabularyHandler,
)
from .llm_client import LLMClient
from .models import LessonState, Phase, SubPhase

logger = logging.getLogger(__name__)


class LessonEngine:
    """Orchestrates a single lesson session.

    Usage::

        engine = LessonEngine(words=["cat", "dog", "bird"])
        greeting = await engine.process("")    # Charlie greets
        reply    = await engine.process("hi")  # child responds → lesson starts
    """

    def __init__(
        self,
        words: list[str] | None = None,
        *,
        llm: LLMClient | None = None,
    ) -> None:
        from .config import settings

        lesson_words = words if words is not None else list(settings.default_words)

        if not lesson_words:
            raise ValueError("At least one word is required for a lesson.")

        self._llm = llm or LLMClient()

        self.state = LessonState(words=lesson_words)

        self._handlers: dict[Phase, PhaseHandler] = {
            Phase.GREETING: GreetingHandler(self._llm),
            Phase.VOCABULARY: VocabularyHandler(self._llm),
            Phase.FAREWELL: FarewellHandler(self._llm),
        }

    @property
    def is_finished(self) -> bool:
        return self.state.phase == Phase.ENDED

    async def process(self, user_input: str = "") -> str:
        """Accept one user turn and return Charlie's complete reply.

        Automatically chains handler calls for phases that require no
        user input.  For example, after a correct answer the response
        includes both the celebration **and** the next word introduction.
        """
        if self.is_finished:
            return "The lesson is already over. Start a new lesson to play again!"

        try:
            handler = self._handlers[self.state.phase]
            reply, self.state = await handler.handle(self.state, user_input)

            # Auto-advance through non-interactive states.
            while self._needs_auto_advance():
                handler = self._handlers[self.state.phase]
                extra, self.state = await handler.handle(self.state, "")
                reply = f"{reply}\n\n{extra}"

            return reply

        except Exception:
            logger.exception("Error during lesson processing")
            return (
                "Oops! Charlie got a bit confused. "
                "Can you say that again?"
            )

    def _needs_auto_advance(self) -> bool:
        """Return True when the current state can proceed without input."""
        if (
            self.state.phase == Phase.VOCABULARY
            and self.state.sub_phase == SubPhase.INTRODUCE
        ):
            return True
        if self.state.phase == Phase.FAREWELL:
            return True
        return False
