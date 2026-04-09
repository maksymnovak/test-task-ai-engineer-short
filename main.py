#!/usr/bin/env python3
"""Interactive CLI for Charlie AI — run a vocabulary lesson in the terminal."""

from __future__ import annotations

import asyncio
import sys

from charlie_ai.config import settings
from charlie_ai.engine import LessonEngine

BANNER = """
╔══════════════════════════════════════════════════╗
║            Charlie AI — English Lesson           ║
╠══════════════════════════════════════════════════╣
║  Type what the child says and press Enter.       ║
║  Empty input = the child stayed silent.          ║
║  Type "quit" to exit at any time.                ║
╚══════════════════════════════════════════════════╝
"""


async def main(words: list[str] | None = None) -> None:
    lesson_words = words or settings.default_words
    print(BANNER)
    print(f"  Words for today: {', '.join(lesson_words)}\n")

    engine = LessonEngine(words=lesson_words)

    # Charlie speaks first — send empty input to trigger the greeting.
    greeting = await engine.process("")
    print(f" Charlie: {greeting}\n")

    while not engine.is_finished:
        try:
            user_input = input(" Child:   ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            return

        if user_input.strip().lower() == "quit":
            print("Lesson ended early. Bye!")
            return

        reply = await engine.process(user_input)
        print(f"\n Charlie: {reply}\n")

    print(" Lesson complete!\n")


if __name__ == "__main__":
    # Optional: pass custom words as CLI arguments.
    #   python main.py apple house tree
    custom_words = sys.argv[1:] if len(sys.argv) > 1 else None
    asyncio.run(main(custom_words))
