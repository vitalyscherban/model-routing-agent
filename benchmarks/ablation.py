"""Per-lever contribution, plus two floor-of-the-ladder reference points.

    python benchmarks/ablation.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from router.config import DEFAULT
from router.pipeline import RoutingAgent
from router.tasks import build_tasks


def _row(label, report, baseline_tokens):
    delta = (report.total_tokens / baseline_tokens - 1) * 100 if baseline_tokens else 0.0
    sign = "+" if delta >= 0 else ""
    print(f"{label:34}{report.total_tokens:>10,}{report.requests:>7}"
          f"{report.accuracy * 100:>10.1f}%   {sign}{delta:.0f}% tokens vs all-levers-on")


def main() -> None:
    tasks = build_tasks()

    naive_settings = dataclasses.replace(
        DEFAULT, routing_enabled=False, caching_enabled=False, escalation_enabled=False
    )
    naive = RoutingAgent(settings=naive_settings).run(tasks)
    baseline = RoutingAgent().run(tasks)

    print(f"{'configuration':34}{'tokens':>10}{'reqs':>7}{'accuracy':>11}   change")
    print("-" * 88)
    _row("naive (always strong)", naive, baseline.total_tokens)
    _row("all levers on", baseline, baseline.total_tokens)
    print("-" * 88)

    no_caching = RoutingAgent(
        settings=dataclasses.replace(DEFAULT, caching_enabled=False)
    ).run(tasks)
    _row("no caching", no_caching, baseline.total_tokens)

    no_escalation = RoutingAgent(
        settings=dataclasses.replace(DEFAULT, escalation_enabled=False)
    ).run(tasks)
    _row("no escalation", no_escalation, baseline.total_tokens)

    forced_cheap = RoutingAgent(
        settings=dataclasses.replace(DEFAULT, force_tier="cheap", caching_enabled=False)
    ).run(tasks)
    _row("no routing -- forced to cheap", forced_cheap, baseline.total_tokens)

    forced_strong = RoutingAgent(
        settings=dataclasses.replace(DEFAULT, force_tier="strong", caching_enabled=False)
    ).run(tasks)
    _row("no routing -- forced to strong", forced_strong, baseline.total_tokens)

    print()
    print("Read tokens/requests as 'cost of removing this lever'.")
    print("Read accuracy as 'correctness cost of removing this lever' -- this")
    print("is the column a pure token-savings table would hide.")


if __name__ == "__main__":
    main()
