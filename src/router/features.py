"""Deterministic, LLM-free feature extraction.

Everything the classifier looks at is computed from the raw task text with no
model call -- the whole point of a routing layer is to make the routing
decision itself free.
"""
from __future__ import annotations

from dataclasses import dataclass

_HARD_SIGNALS = (
    "root cause", "race condition", "trade-off", "trade off", "architecture",
    "concurrent", "intermittent", "profile", "memory leak", "no maintenance "
    "window", "cannot tolerate downtime", "disagree", "make the call",
    "design a migration",
)

_TRIVIAL_SIGNALS = (
    "what does the", "rename the variable", "fix the typo", "pinned in",
    "convert this timestamp", "http status",
)

_MODERATE_SIGNALS = (
    "write a function", "write unit tests", "refactor", "summarize",
    "add a retry",
)


@dataclass(frozen=True)
class Features:
    length: int
    word_count: int
    question_marks: int
    hard_hits: int
    moderate_hits: int
    trivial_hits: int


def extract(text: str) -> Features:
    lowered = text.lower()
    return Features(
        length=len(text),
        word_count=len(text.split()),
        question_marks=text.count("?"),
        hard_hits=sum(1 for s in _HARD_SIGNALS if s in lowered),
        moderate_hits=sum(1 for s in _MODERATE_SIGNALS if s in lowered),
        trivial_hits=sum(1 for s in _TRIVIAL_SIGNALS if s in lowered),
    )
