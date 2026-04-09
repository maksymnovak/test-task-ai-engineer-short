"""Thin async wrapper around the Groq SDK.

Responsibilities:
- Enforce JSON-mode output via ``response_format``.
- Parse raw JSON into a caller-supplied Pydantic model.
- Retry on transient parse / validation failures.

The client is intentionally stateless — it holds only the API key and model
name.  All session context is managed externally by the lesson engine.
"""

from __future__ import annotations

import json
import logging
from typing import TypeVar

from groq import AsyncGroq
from pydantic import BaseModel, ValidationError

from .config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

SYSTEM_MESSAGE = "Always respond with valid JSON only. No markdown, no extra text."


class LLMClient:
    """Async LLM client that guarantees structured (JSON) responses."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        key = api_key or settings.groq_api_key
        if not key:
            raise ValueError(
                "GROQ_API_KEY is required. "
                "Set it in .env or pass it explicitly."
            )
        self._client = AsyncGroq(api_key=key)
        self._model = model or settings.groq_model

    async def generate(
        self,
        prompt: str,
        response_model: type[T],
        *,
        temperature: float = 0.7,
        max_retries: int = 2,
    ) -> T:
        """Send *prompt* to Groq and return a validated *response_model*.

        Three layers enforce structured output:
        1. ``response_format=json_object`` constrains token generation.
        2. The prompt itself contains the exact JSON schema.
        3. Pydantic validates the parsed dict against *response_model*.

        On parse / validation failure the call is retried up to
        *max_retries* times (fresh LLM call each time).
        """
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 2):
            try:
                completion = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_MESSAGE},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    max_tokens=300,
                )
                raw = completion.choices[0].message.content or ""
                logger.debug("LLM raw (attempt %d): %s", attempt, raw)

                data = json.loads(raw)
                return response_model.model_validate(data)

            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning(
                    "Attempt %d — parse/validation error: %s", attempt, exc
                )
                last_error = exc
            except Exception as exc:
                logger.error("Attempt %d — LLM error: %s", attempt, exc)
                last_error = exc

        raise RuntimeError(
            f"LLM call failed after {max_retries + 1} attempts"
        ) from last_error
