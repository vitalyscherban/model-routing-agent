"""Per-tier answer simulation.

`OfflineModel` genuinely parses which category a task belongs to and derives
whether a tier's *simulated capability ceiling* covers it -- it does not
inspect the ground-truth label directly through a side channel. This mirrors
`migration-agent`'s `OfflineModel`: a fake that does real work, so a
regression in the pipeline (wrong tier passed, wrong task text truncated)
shows up as a wrong answer instead of being invisible to a canned stub.

What it explicitly cannot simulate is *true* answer quality -- see
docs/evaluation.md.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from . import tokens
from .tasks import Task
from .tiers import Tier

SYSTEM_PROMPTS = {
    "cheap": "You are a fast, low-cost assistant. Answer concisely.",
    "mid": (
        "You are a general-purpose engineering assistant. Answer clearly, "
        "show your reasoning briefly, and flag anything you are unsure of."
    ),
    "strong": (
        "You are a senior engineering assistant handling escalations and "
        "hard, ambiguous, or high-stakes problems. Reason step by step, "
        "state assumptions explicitly, and be precise about trade-offs."
    ),
}

_ANSWER_WORDS = {
    "trivial": 18,
    "moderate": 55,
    "hard": 150,
}
_TIER_THOROUGHNESS = {"cheap": 0.8, "mid": 1.0, "strong": 1.3}

_FILLER = (
    "the observed behavior traces back through the call path, the relevant "
    "state is checked against expectations, edge cases around empty input, "
    "concurrent access, and timing are considered, and the recommendation "
    "follows from weighing correctness, latency, and operational risk"
).split()


def _stable_unit(*parts: str) -> float:
    """A deterministic float in [0, 1) derived from the given strings.

    Used in place of true randomness so a tier's partial success on a task
    is reproducible across runs -- required for `test_run_is_deterministic`.
    """
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _synthesize_answer(task: Task, tier: Tier, correct: bool) -> str:
    target_words = int(_ANSWER_WORDS[task.category] * _TIER_THOROUGHNESS[tier.name])
    words = (_FILLER * (target_words // len(_FILLER) + 1))[:target_words]
    body = " ".join(words)
    prefix = "Answer: " if correct else "Best guess (unverified): "
    return f"{prefix}regarding {task.text[:40]!r}, {body}."


@dataclass(frozen=True)
class Answer:
    text: str
    input_tokens: int
    output_tokens: int
    correct: bool


class OfflineModel:
    def ask(self, task: Task, tier: Tier) -> Answer:
        if task.category in tier.solves:
            correct = True
        else:
            correct = _stable_unit(task.id, tier.name) < tier.partial_odds

        answer_text = _synthesize_answer(task, tier, correct)
        prompt = SYSTEM_PROMPTS[tier.name] + "\n\n" + task.text
        return Answer(
            text=answer_text,
            input_tokens=tokens.count(prompt),
            output_tokens=tokens.count(answer_text),
            correct=correct,
        )
