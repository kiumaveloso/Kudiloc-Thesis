"""
Reputation update logic for the KudiLoc simulation.

Implements the periodic ground-truth-reveal mechanism described in
Section 5 of the methodology: at fixed intervals during the simulation,
ground truth for a batch of ATMs is revealed, and every reporter who
submitted a report on one of those ATMs has their `reputation` updated
based on whether their claim matched the revealed truth.

Reputation is intentionally cross-ATM (global): it lives on the
Reporter object itself (see models.py), not per-ATM, so a reporter's
track record on any subset of ATMs informs how much their future
reports are trusted anywhere in the system. This is a deliberate
modeling choice, not an oversight — see dev_log.md, Day 2 entry, and
the "Threats to Validity" discussion it implies.

Update rule: multiplicative reward/penalty.
    correct report:   reputation *= REWARD_FACTOR   (default 1.1)
    incorrect report: reputation *= PENALTY_FACTOR   (default 0.9)
    clamped to [MIN_REPUTATION, MAX_REPUTATION] to prevent runaway
    growth/decay over a long simulation.

This module does not decide *when* ground truth is revealed — that is
an experiment-harness concern (fixed-interval scheduling). It only
implements *what happens* to reputations once a reveal occurs, given
the reports and the true states for the revealed batch of ATMs.
"""

from src.simulation.models import ATM, Report, Reporter

REWARD_FACTOR: float = 1.1
PENALTY_FACTOR: float = 0.9
MIN_REPUTATION: float = 0.01
MAX_REPUTATION: float = 10.0


def update_reputations(
    reports: list[Report],
    atms: dict[str, ATM],
    reporters: dict[str, Reporter],
    reward_factor: float = REWARD_FACTOR,
    penalty_factor: float = PENALTY_FACTOR,
    min_reputation: float = MIN_REPUTATION,
    max_reputation: float = MAX_REPUTATION,
) -> None:
    """
    Apply a ground-truth reveal event: update reporter reputations based
    on whether each report matched the true state of the ATM it concerned.

    Mutates the Reporter objects in `reporters` in place (consistent with
    how ground_truth.py's maybe_flip_states() mutates ATMs in place).

    Args:
        reports: The reports being scored in this reveal event. Typically
            all reports submitted for the batch of ATMs whose ground
            truth is being revealed at this interval — filtering which
            reports belong to this reveal is an experiment-harness
            concern, not this function's.
        atms: Lookup of atm_id -> ATM, used to read true_state for each
            report's atm_id. Only ATMs referenced by `reports` are read.
        reporters: Lookup of reporter_id -> Reporter. Every reporter who
            appears in `reports` must have an entry here; their
            `reputation` field is updated in place.
        reward_factor: Multiplier applied to reputation when a report's
            claimed_state matches the ATM's true_state.
        penalty_factor: Multiplier applied to reputation when a report's
            claimed_state does not match the ATM's true_state.
        min_reputation: Lower clamp bound, prevents reputation collapsing
            to zero (which would make a reporter's weight permanently
            irrecoverable regardless of future good behavior).
        max_reputation: Upper clamp bound, prevents a single reporter's
            weight from dominating the aggregate indefinitely.

    Raises:
        KeyError: if a report references an atm_id or reporter_id not
            present in `atms` / `reporters`. This is intentional — a
            missing lookup indicates a bug in how the reveal batch was
            constructed upstream, and should fail loudly rather than
            silently skip reputation updates.
    """
    for report in reports:
        atm = atms[report.atm_id]
        reporter = reporters[report.reporter_id]

        was_correct = report.claimed_state == atm.true_state
        factor = reward_factor if was_correct else penalty_factor

        new_reputation = reporter.reputation * factor
        reporter.reputation = max(min_reputation, min(max_reputation, new_reputation))
