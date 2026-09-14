"""Model tiers and their published per-million-token pricing.

Prices are illustrative and in the same shape as a real provider's tiered
lineup: a small fast model, a mid-size general model, and a frontier model,
each roughly an order of magnitude apart in price. The routing decision below
never inspects these prices directly -- pricing only matters at the point
where cost is computed from a token count, exactly like the token-reduction
repos in this series never let the token counter influence the pipeline logic.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    name: str
    input_price: float   # USD per 1M input tokens
    output_price: float  # USD per 1M output tokens
    # Simulated capability ceiling used only by the offline model to decide
    # whether this tier can solve a task of a given category. This stands in
    # for "how good is this model", which cannot be measured offline -- see
    # docs/evaluation.md for what that means for these numbers.
    solves: frozenset[str]
    # For categories this tier does not reliably solve, the deterministic
    # per-task odds it gets lucky anyway (never 0, real models are not
    # perfectly bimodal; never high, or the whole premise of routing breaks).
    partial_odds: float


CHEAP = Tier(
    name="cheap",
    input_price=0.15,
    output_price=0.60,
    solves=frozenset({"trivial"}),
    partial_odds=0.10,
)

MID = Tier(
    name="mid",
    input_price=0.50,
    output_price=1.50,
    solves=frozenset({"trivial", "moderate"}),
    partial_odds=0.35,
)

STRONG = Tier(
    name="strong",
    input_price=2.50,
    output_price=10.0,
    solves=frozenset({"trivial", "moderate", "hard"}),
    partial_odds=1.0,
)

LADDER = (CHEAP, MID, STRONG)
BY_NAME = {t.name: t for t in LADDER}


def next_tier(tier: Tier) -> Tier | None:
    """The next rung up the escalation ladder, or None at the top."""
    idx = LADDER.index(tier)
    if idx + 1 >= len(LADDER):
        return None
    return LADDER[idx + 1]
