"""Routing configuration.

Every threshold here is either **measured** (chosen by running
`benchmarks/ablation.py` and observing where the numbers stopped moving) or
**judgement** (chosen by reasoning about the domain, not yet falsified against
a real model). See docs/tuning.md for which is which.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClassifierThresholds:
    # A task scoring below this on the 0-1 complexity scale is routed to the
    # cheap tier. Above `moderate_ceiling` it goes straight to strong.
    # Measured: sweeping this against the corpus's own category labels is
    # exactly what `tests/test_classifier.py::test_thresholds_align_with_ground_truth`
    # checks, so drift here fails CI rather than silently misrouting.
    trivial_ceiling: float = 0.35
    moderate_ceiling: float = 0.70


@dataclass(frozen=True)
class Settings:
    routing_enabled: bool = True
    escalation_enabled: bool = True
    caching_enabled: bool = True
    thresholds: ClassifierThresholds = field(default_factory=ClassifierThresholds)
    # Escalation stops after this many rungs, regardless of ladder length.
    # One rung is enough to reach the top of a 3-tier ladder from the middle,
    # but a longer ladder should not be allowed to escalate every task to the
    # most expensive tier by default -- that would silently reproduce the
    # naive baseline under a routing label.
    max_escalations: int = 1
    # Bypasses the classifier and sends every task to one named tier
    # ("cheap" / "mid" / "strong"). Not a production setting -- it exists so
    # benchmarks/ablation.py can produce the "always cheapest" and "always
    # strongest" reference points without duplicating pipeline logic.
    force_tier: str | None = None


DEFAULT = Settings()
