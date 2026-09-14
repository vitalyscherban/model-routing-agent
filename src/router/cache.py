"""Exact-after-normalisation task cache.

Real semantic caches use embedding similarity; that is a model call, which
would spend tokens to save tokens on the hot path. This cache uses a cheap
deterministic normalisation instead -- it will not catch a genuine paraphrase,
but it does catch the extremely common case in support and dev-task traffic
of the same question restated with a different greeting or framing, which is
exactly what `tasks.py` generates as duplicates.

This is a real limitation, not swept under the rug: see docs/evaluation.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_FILLER_PREFIXES = (
    "quick one:", "following up --", "following up:", "hey,",
)

_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    lowered = text.strip().lower()
    for prefix in _FILLER_PREFIXES:
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix):].strip()
            break
    return _WHITESPACE.sub(" ", lowered)


@dataclass
class Cache:
    _store: dict[str, str] = field(default_factory=dict)  # normalised text -> answer
    hits: int = 0
    misses: int = 0

    def get(self, text: str) -> str | None:
        key = normalize(text)
        hit = self._store.get(key)
        if hit is not None:
            self.hits += 1
        else:
            self.misses += 1
        return hit

    def put(self, text: str, answer: str) -> None:
        self._store[normalize(text)] = answer

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
