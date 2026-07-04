# Dev Log

## Day 1 — [today's date]

- Ground truth, reporters, and report stream are seed-reproducible.
- Adversarial reporters deliberately flip state; unreliable reporters make
  random honest mistakes — kept these conceptually distinct.
- Majority Vote tie-break defaults to `True` (stocked) — a documented
  methodological choice.
- Confirmed baseline behavior: 100% accuracy at low adversarial fraction
  (0.1), collapsing to 14% at high adversarial fraction (0.6) — demonstrates
  the exact failure mode motivating Reputation-Weighted/Time-Decayed
  algorithms.

**Open question for tomorrow:** exact learning rule for reputation updates
(how often ground truth is "revealed," how much reporters gain/lose
reputation per correct/incorrect report).

