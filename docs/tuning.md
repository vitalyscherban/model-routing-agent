# Tuning

All settings live in `src/router/config.py`. Each is tagged **measured**
(chosen by running the benchmark and observing the numbers) or **judgement**
(chosen by reasoning about the domain, not yet falsified).

## Classifier thresholds

| setting | default | basis |
|---|---:|---|
| `trivial_ceiling` | 0.35 | measured |
| `moderate_ceiling` | 0.70 | measured |

These were tuned against the corpus's own category labels until
`test_trivial_and_moderate_are_never_misclassified` passed with zero
tolerance and the hard-task misclassification rate (see below) stopped
improving. That second condition matters: pushing `moderate_ceiling` down
further eventually "fixes" the hard-task gap but starts misrouting moderate
tasks into strong, trading a cheap problem for an expensive one.

## The classifier's known gap

At these thresholds, **~14.5% of hard tasks score just under the strong
threshold** and route to mid instead. Investigation traced this to one
template — the memory-leak scenario — which contains exactly one hard-signal
keyword ("memory leak") where other hard templates contain two or three
("root cause", "concurrent", "intermittent" all in the same sentence). The
scoring formula rewards signal density, and this template is sparse.

This is not fixed by patching the template list, because the next domain this
router is pointed at will have its own sparse-signal cases — the point of
documenting it is that **escalation is the actual fix, not a better keyword
list**. `test_escalation_recovers_misclassified_hard_tasks` pins this: turn
escalation off and accuracy drops from 100% to 98.5%, isolating exactly the
6 tasks this gap causes.

The bound is asserted both ways in `test_classifier.py`:
`test_hard_misclassification_rate_is_bounded` fails if the rate gets *worse*
(a regression), and asserts it is not *zero* either — a suspiciously perfect
number here would mean the test corpus stopped exercising the gap, not that
the gap was fixed.

## Escalation

| setting | default | basis |
|---|---:|---|
| `max_escalations` | 1 | judgement |

One rung reaches the top of this 3-tier ladder from the middle, which is
where the classifier's own errors land (mid, not cheap — see
`test_all_misrouted_hard_tasks_go_to_mid_not_cheap`). It is deliberately not
"escalate until correct or the ladder ends": an unlimited escalation budget
would make a bad classifier invisible by always paying to route around it,
which defeats the purpose of measuring the classifier at all.

The floor-of-the-ladder ablation (`force_tier="cheap"`) demonstrates why this
cap matters: with every task starting at the bottom, many need two rungs to
reach a tier that solves them, and the one-rung cap can't deliver that — 92.0%
accuracy, worse than the naive baseline, at *higher* total token cost. A
production router pointed at a bimodal task distribution like this one should
budget escalation depth to the ladder's height minus one, not to a fixed
constant — this default is tuned for a 3-tier ladder specifically.

## Tier definitions and pricing

| tier | input $/1M | output $/1M | declared ceiling |
|---|---:|---:|---|
| cheap | 0.15 | 0.60 | trivial |
| mid | 0.50 | 1.50 | trivial, moderate |
| strong | 2.50 | 10.00 | trivial, moderate, hard |

Pricing is illustrative, shaped like a real provider's tiered lineup (roughly
an order of magnitude apart per rung). `partial_odds` per tier (10% / 35% /
100%) governs how often a tier gets lucky on a category outside its declared
ceiling — never zero, because real models are not perfectly bimodal, and
never high, or the whole premise of routing collapses.

## Cache

The normaliser strips a small, explicit list of filler prefixes
(`"quick one:"`, `"hey,"`, `"following up --"`) and collapses whitespace. It
is judgement, not measurement — a real deployment would derive this list from
actual traffic logs, not invent it. See docs/evaluation.md for the corpus bug
this cache design surfaced.

## Retuning for a different task distribution

The three defaults most likely to need re-deriving for a different traffic
mix, in order of how much they'd move the numbers:

1. **Classifier thresholds** — tuned specifically against this corpus's
   category boundaries. A traffic mix with a different definition of "hard"
   needs new thresholds, not just new keyword lists.
2. **`max_escalations`** — scale with ladder height, not a fixed constant.
3. **Cache filler-prefix list** — derive from real duplicate traffic, not
   guessed patterns.
