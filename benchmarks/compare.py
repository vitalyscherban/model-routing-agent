"""Naive (always the strongest model) vs. routed, on the same task corpus.

    python benchmarks/compare.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from router.config import DEFAULT
from router.pipeline import RoutingAgent
from router.tasks import build_tasks, stats


def main() -> None:
    tasks = build_tasks()
    s = stats(tasks)

    naive_settings = dataclasses.replace(
        DEFAULT, routing_enabled=False, caching_enabled=False, escalation_enabled=False
    )
    naive = RoutingAgent(settings=naive_settings).run(tasks)
    routed = RoutingAgent().run(tasks)

    def pct(before: float, after: float) -> str:
        if before == 0:
            return "n/a"
        return f"{(1 - after / before) * 100:.1f}%"

    print("CORPUS")
    print(f"  {s['total']} tasks  ({s['unique']} unique, {s['duplicates']} paraphrased duplicates)")
    print(f"  by category: {s['by_category']}")
    print()
    print("NAIVE (always strong model) vs ROUTED")
    print("-" * 62)
    print(f"{'':30}{'naive':>12}{'routed':>12}{'saved':>8}")
    print(f"{'model requests':30}{naive.requests:>12}{routed.requests:>12}"
          f"{pct(naive.requests, routed.requests):>8}")
    print(f"{'input tokens':30}{naive.input_tokens:>12,}{routed.input_tokens:>12,}"
          f"{pct(naive.input_tokens, routed.input_tokens):>8}")
    print(f"{'output tokens':30}{naive.output_tokens:>12,}{routed.output_tokens:>12,}"
          f"{pct(naive.output_tokens, routed.output_tokens):>8}")
    print(f"{'total tokens':30}{naive.total_tokens:>12,}{routed.total_tokens:>12,}"
          f"{pct(naive.total_tokens, routed.total_tokens):>8}")
    print(f"{'cost':30}${naive.cost:>11.4f}${routed.cost:>11.4f}"
          f"{pct(naive.cost, routed.cost):>8}")
    print()
    print("WHERE THE TRAFFIC WENT")
    for tier_name in ("cheap", "mid", "strong"):
        print(f"  {tier_name:8} {routed.requests_by_tier[tier_name]:>4} requests")
    print(f"  cache hits    {routed.cache_hits:>4}  (hit rate {routed.cache_hit_rate:.1%})")
    print(f"  escalations   {routed.escalations:>4}")
    print()
    print(f"CORRECTNESS: naive {naive.correct}/{naive.total_tasks}   "
          f"routed {routed.correct}/{routed.total_tasks}")


if __name__ == "__main__":
    main()
