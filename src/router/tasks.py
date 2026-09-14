"""Deterministic synthetic task corpus with a ground-truth answer key.

Mirrors the corpus design in the sibling `migration-agent` repo: a fixed seed,
a generator that also emits the ground truth it used, and tests that assert
the rest of the pipeline reproduces that ground truth exactly. A benchmark
that cannot check its own labels is not a benchmark.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

CATEGORIES = ("trivial", "moderate", "hard")

# Deliberately not evenly split. Real support/dev-task traffic is
# trivial-heavy; a routing agent that only shines on a 1/3-1/3-1/3 split is
# not being tested against anything realistic.
_WEIGHTS = {"trivial": 0.45, "moderate": 0.35, "hard": 0.20}

_TRIVIAL_TEMPLATES = [
    "What does the {sym} function return?",
    "Rename the variable {sym} to {sym}_v2 in this file.",
    "Fix the typo in the docstring for {sym}.",
    "What is the current version pinned in requirements.txt?",
    "Convert this timestamp to ISO 8601: {sym}.",
    "What does HTTP status {sym} mean?",
]

_MODERATE_TEMPLATES = [
    "Write a function that validates {sym} against a schema and returns the errors.",
    "Summarize what changed in this diff touching {sym}.",
    "Add a retry with backoff around the {sym} call.",
    "Write unit tests for the {sym} edge cases: empty input, None, and a duplicate key.",
    "Refactor {sym} to accept a config object instead of five positional args.",
]

_HARD_TEMPLATES = [
    "Users report {sym} intermittently returns stale data under concurrent "
    "writes; find the root cause and propose a fix.",
    "We need to decide between {sym} and an alternative architecture for a "
    "system with strict latency SLAs -- what is the trade-off and what do "
    "you recommend?",
    "This service leaks memory only after {sym} runs for several hours under "
    "production load; profile the likely cause without access to a live "
    "process.",
    "Design a migration plan for {sym} that cannot tolerate downtime and has "
    "no maintenance window.",
    "Two teams disagree about who owns a race condition in {sym}; investigate "
    "and make the call.",
]

_SYMBOLS = [
    "checkout_service", "auth_middleware", "event_consumer", "the cache layer",
    "the payment webhook", "the export job", "the session store",
    "the rate limiter", "the retry queue", "the notification worker",
]


@dataclass(frozen=True)
class Task:
    id: str
    text: str
    category: str          # ground truth: trivial / moderate / hard
    duplicate_of: str | None = None  # id of an earlier, near-identical task


def _pick_template(rng: random.Random, category: str) -> str:
    pool = {"trivial": _TRIVIAL_TEMPLATES, "moderate": _MODERATE_TEMPLATES,
            "hard": _HARD_TEMPLATES}[category]
    return rng.choice(pool)


def build_tasks(count: int = 400, duplicate_ratio: float = 0.25,
                seed: int = 20240914) -> list[Task]:
    """Generate a deterministic task corpus.

    `duplicate_ratio` of tasks are near-identical restatements of an earlier
    task (same template, same symbol, trivial wording change) -- this is what
    gives the semantic cache something real to hit. Everything else is unique.
    """
    rng = random.Random(seed)
    originals: list[Task] = []
    tasks: list[Task] = []

    if count <= 0:
        return []

    n_originals = max(1, int(count * (1 - duplicate_ratio)))
    for i in range(n_originals):
        category = rng.choices(list(_WEIGHTS), weights=list(_WEIGHTS.values()))[0]
        template = _pick_template(rng, category)
        sym = rng.choice(_SYMBOLS)
        # A case reference makes every original unique even when template and
        # symbol coincide. Without it, ~300 originals drawn from a template x
        # symbol space of only 60-180 combinations collide by chance far more
        # often than the deliberate `duplicate_of` paraphrases below -- which
        # is exactly what happened the first time this was built (see
        # docs/evaluation.md). That made the cache's benefit real but
        # unattributable: no way to tell "the paraphrase detector worked"
        # from "two originals happened to be identical".
        text = f"{template.format(sym=sym)} (case #{i:04d})"
        task = Task(id=f"t{i}", text=text, category=category)
        originals.append(task)
        tasks.append(task)

    n_dupes = count - n_originals
    _PARAPHRASE_PREFIXES = ["", "Quick one: ", "Following up -- ", "Hey, "]
    for j in range(n_dupes):
        src = rng.choice(originals)
        prefix = rng.choice(_PARAPHRASE_PREFIXES)
        text = prefix + src.text
        tasks.append(Task(id=f"d{j}", text=text, category=src.category,
                           duplicate_of=src.id))

    rng.shuffle(tasks)
    return tasks


def stats(tasks: list[Task]) -> dict:
    by_category = {c: sum(1 for t in tasks if t.category == c) for c in CATEGORIES}
    duplicates = sum(1 for t in tasks if t.duplicate_of is not None)
    return {
        "total": len(tasks),
        "by_category": by_category,
        "duplicates": duplicates,
        "unique": len(tasks) - duplicates,
    }
