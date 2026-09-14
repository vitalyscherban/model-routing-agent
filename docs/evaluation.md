# Evaluation

## What is actually being measured

Token counts come from `tiktoken` (`cl100k_base`) over the exact system prompt
and task text sent to each tier, and over the exact synthesized answer
returned. They are not estimates. `tokens.is_exact` reports whether `tiktoken`
loaded; if not, a `len(text) / 3.4` approximation is used and the flag flips
false, so a degraded run can never be mistaken for a precise one.

Costs use per-million-token rates in `tiers.py`, shaped like a real provider's
tiered lineup. There is no prefix-cache discount in this repo — that lever
belongs to the other two repos in this series (`langchain-token-efficient-agent`,
`migration-agent`); this one's distinguishing lever is *which* model answers,
not *how much context* it sees.

## The corpus

`tasks.py` generates 400 tasks from templates across three categories with a
fixed seed (`20240914`): 45% trivial, 35% moderate, 20% hard, plus 100
deliberately paraphrased duplicates of earlier tasks. The generator also
records the ground truth it used — each task's true category — so the rest of
the pipeline can be checked against it rather than trusted.

**A bug was found and fixed here.** The first version drew each original task
from roughly 60–180 possible template×symbol combinations per category, and
with ~300 originals, independent tasks collided by chance far more often than
the 100 deliberately-injected paraphrases did (118 unique normalised texts out
of 400 tasks — a cache hit rate over 70%, almost none of it attributable to
the paraphrase mechanism being tested). The fix appends a unique case
reference to every original, so every cache hit now traces to a specific,
labelled duplicate, checked exactly in
`test_caching_eliminates_requests_for_duplicate_tasks`. A benchmark whose
headline cache number can't be attributed to the mechanism it's supposed to
demonstrate isn't measuring that mechanism.

## The model

`OfflineModel` is not a coin flip. It builds the real prompt each tier would
receive (a tier-specific system prompt plus the task text), counts its tokens,
and derives correctness from whether the task's category is inside that
tier's declared `solves` set — with a small, deterministic, seeded chance of
an outcome outside that ceiling, so tiers are not perfectly bimodal but are
still reproducible run to run (`test_answers_are_deterministic`,
`test_run_is_deterministic`).

This means a real bug in the pipeline — the wrong tier passed to `ask()`, a
truncated task string, a classifier that stops discriminating — shows up as a
correctness regression in the test suite, not as a change nobody would notice
in a mocked response.

## What this harness cannot tell you

Stated plainly, because the precision of the token counts above could be
mistaken for completeness:

**Answer quality is unmeasured, deliberately and unavoidably.** "Correct" here
means "within the tier's declared capability ceiling for this task's
category" — a modeling assumption I chose, not something a real verifier
checked. A real deployment's escalation trigger would be a rubric score, a
test suite, a user complaint, or a human review, and calibrating that trigger
against real failure rates is a different, harder problem this repo does not
solve. It answers a narrower one: *given a correctness signal, how much can
tiering and caching save without touching it.*

**The task corpus is synthetic and its categories are given, not inferred.**
Real traffic doesn't arrive labeled "trivial." The corpus's category is used
twice — once (indirectly, via keyword templates) to generate text a heuristic
classifier can plausibly read signal from, and once as the answer key the
model's capability ceiling checks against. A harder and more honest test would
generate text whose difficulty is uncorrelated with the classifier's chosen
keywords; this repo's classifier would perform worse against that corpus, and
that gap is real and not measured here.

**The escalation-cost story is specific to a 3-tier ladder capped at one
rung.** A deployment with more tiers, or a classifier with a different error
profile (e.g., systematically under- rather than over-cautious), would need
its own ablation, not an extrapolation from this one.

## Regression protection

Both benchmarks run in CI alongside the unit tests, so a change that quietly
shifts routing behavior or token accounting fails the build instead of making
the README wrong at leisure.

| claim | test |
|---|---|
| trivial/moderate routing has zero tolerance for drift | `test_classifier.py::test_trivial_and_moderate_are_never_misclassified` |
| hard-task misrouting is bounded, not silently worsening | `test_classifier.py::test_hard_misclassification_rate_is_bounded` |
| misrouted hard tasks land on mid, never cheap | `test_classifier.py::test_all_misrouted_hard_tasks_go_to_mid_not_cheap` |
| escalation is what keeps accuracy at 100%, not the classifier | `test_pipeline.py::test_escalation_recovers_misclassified_hard_tasks` |
| forcing everything to cheap breaks correctness | `test_pipeline.py::test_forcing_everything_to_cheap_breaks_correctness` |
| cache hits equal the labelled duplicate count exactly | `test_pipeline.py::test_caching_eliminates_requests_for_duplicate_tasks` |
| a wrong answer is never cached | `test_pipeline.py::test_only_correct_answers_populate_the_cache` |
| the corpus is deterministic and reproducible | `test_tasks.py::test_corpus_is_deterministic` |
| routing beats naive on cost without an accuracy cost | `test_pipeline.py::test_routed_run_is_far_cheaper_than_naive_at_no_accuracy_cost` |

34 tests, well under a second, no network.
