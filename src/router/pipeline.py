"""Orchestration: cache lookup, classification, tiered call, verify, escalate.

Call order per task is fixed and deliberate: cache is checked before the
classifier runs, because a cache hit makes the routing decision moot and
should cost nothing at all, not even the (free but non-zero-latency)
classification step.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import classifier
from .cache import Cache
from .config import DEFAULT, Settings
from .model import Answer, OfflineModel
from .tasks import Task
from .tiers import BY_NAME, STRONG, Tier, next_tier


@dataclass
class _TierBucket:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class Ledger:
    buckets: dict[str, _TierBucket] = field(
        default_factory=lambda: {name: _TierBucket() for name in ("cheap", "mid", "strong")}
    )
    cache_hits: int = 0
    cache_misses: int = 0
    escalations: int = 0
    correct: int = 0
    incorrect: int = 0

    def record(self, tier: Tier, answer: Answer) -> None:
        bucket = self.buckets[tier.name]
        bucket.requests += 1
        bucket.input_tokens += answer.input_tokens
        bucket.output_tokens += answer.output_tokens


@dataclass
class Report:
    total_tasks: int
    cache_hits: int
    cache_hit_rate: float
    requests_by_tier: dict[str, int]
    requests: int  # model calls, excluding cache hits
    escalations: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    correct: int
    incorrect: int
    accuracy: float


def _cost(buckets: dict[str, _TierBucket]) -> float:
    from .tiers import BY_NAME

    total = 0.0
    for name, bucket in buckets.items():
        tier = BY_NAME[name]
        total += bucket.input_tokens / 1_000_000 * tier.input_price
        total += bucket.output_tokens / 1_000_000 * tier.output_price
    return total


class RoutingAgent:
    def __init__(self, settings: Settings = DEFAULT, model: OfflineModel | None = None):
        self.settings = settings
        self.model = model or OfflineModel()
        self.cache = Cache()

    def run(self, tasks: list[Task]) -> Report:
        ledger = Ledger()

        for task in tasks:
            if self.settings.caching_enabled:
                cached = self.cache.get(task.text)
                if cached is not None:
                    ledger.cache_hits += 1
                    ledger.correct += 1
                    continue
                ledger.cache_misses += 1

            if self.settings.force_tier is not None:
                tier = BY_NAME[self.settings.force_tier]
            elif self.settings.routing_enabled:
                tier, _ = classifier.pick_tier(task.text, self.settings.thresholds)
            else:
                tier = STRONG

            answer = self.model.ask(task, tier)
            ledger.record(tier, answer)

            escalated = 0
            while (
                not answer.correct
                and self.settings.escalation_enabled
                and escalated < self.settings.max_escalations
            ):
                nxt = next_tier(tier)
                if nxt is None:
                    break
                tier = nxt
                answer = self.model.ask(task, tier)
                ledger.record(tier, answer)
                ledger.escalations += 1
                escalated += 1

            if answer.correct:
                ledger.correct += 1
                # Only correct answers are cached. A wrong answer served from
                # cache would compound a single mistake across every future
                # duplicate of that question -- worse than the cost of asking
                # again. This mirrors why migration-agent never caches a
                # rule that failed verification.
                if self.settings.caching_enabled:
                    self.cache.put(task.text, answer.text)
            else:
                ledger.incorrect += 1

        total_requests = sum(b.requests for b in ledger.buckets.values())
        input_tokens = sum(b.input_tokens for b in ledger.buckets.values())
        output_tokens = sum(b.output_tokens for b in ledger.buckets.values())
        cache_total = ledger.cache_hits + ledger.cache_misses
        return Report(
            total_tasks=len(tasks),
            cache_hits=ledger.cache_hits,
            cache_hit_rate=(ledger.cache_hits / cache_total) if cache_total else 0.0,
            requests_by_tier={name: b.requests for name, b in ledger.buckets.items()},
            requests=total_requests,
            escalations=ledger.escalations,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=_cost(ledger.buckets),
            correct=ledger.correct,
            incorrect=ledger.incorrect,
            accuracy=(ledger.correct / len(tasks)) if tasks else 0.0,
        )
