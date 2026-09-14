"""The routing decision itself.

Deliberately a small deterministic heuristic, not a model call -- classifying
a task with an LLM before deciding which LLM should handle it would spend
tokens to save tokens. Real routing layers use a similar cheap heuristic
(often a small classifier trained on logs) for exactly this reason.
"""
from __future__ import annotations

from .config import ClassifierThresholds
from .features import Features, extract
from .tiers import CHEAP, MID, STRONG, Tier

_HARD_WEIGHT = 0.35
_MODERATE_WEIGHT = 0.30
_TRIVIAL_WEIGHT = -0.25
_BASE = 0.10
_LENGTH_CAP_WORDS = 50
_LENGTH_WEIGHT = 0.10
_HIT_CAP = 2


def score(features: Features) -> float:
    hard = min(features.hard_hits, _HIT_CAP) * _HARD_WEIGHT
    moderate = min(features.moderate_hits, _HIT_CAP) * _MODERATE_WEIGHT
    trivial = min(features.trivial_hits, _HIT_CAP) * _TRIVIAL_WEIGHT
    length_bonus = min(features.word_count, _LENGTH_CAP_WORDS) / _LENGTH_CAP_WORDS * _LENGTH_WEIGHT
    raw = _BASE + hard + moderate + trivial + length_bonus
    return max(0.0, min(1.0, raw))


def pick_tier(text: str, thresholds: ClassifierThresholds) -> tuple[Tier, float]:
    s = score(extract(text))
    if s < thresholds.trivial_ceiling:
        return CHEAP, s
    if s < thresholds.moderate_ceiling:
        return MID, s
    return STRONG, s
