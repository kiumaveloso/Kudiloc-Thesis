"""
Ground truth generator for the KudiLoc simulation.

Generates a population of ATMs with a known true state, and supports
state changes over simulated time via two mechanisms:

1. maybe_flip_states() — the original Phase 1 mechanism. An
   instantaneous, timestamp-blind flip: it decides an ATM's final
   true_state without regard to when reports about that ATM were
   submitted. Every report for a flipped ATM becomes equally
   right/wrong regardless of its timestamp. This is adequate for
   testing algorithms that don't reason about report age (Majority
   Vote, Reputation-Weighted), but it eliminates the very
   recency-correctness gradient that Time-Decayed Trust Scoring is
   designed to exploit — see dev_log.md staleness-fix entry.

2. generate_flip_times() — the Phase 2 fix. Assigns each flipping ATM
   an explicit flip_time within the report window, and records its
   pre_flip_state. Combined with report_stream.generate_reports()
   (which now checks true_state_at() per report instead of a single
   static true_state), this produces genuine staleness: reports before
   flip_time correctly describe the old state, reports after correctly
   describe the new state, and only reports whose timestamp is close to
   flip_time are ambiguous. This is the scenario Time-Decayed needs to
   demonstrate a real, non-noise advantage over Reputation-Weighted.
"""
import random
from src.simulation.models import ATM


def generate_atms(
    num_atms: int,
    seed: int,
    initial_stocked_probability: float = 0.7,
) -> list[ATM]:
    """
    Create a population of ATMs with randomly assigned initial states.
    """
    rng = random.Random(seed)
    atms = []
    for i in range(num_atms):
        true_state = rng.random() < initial_stocked_probability
        atms.append(ATM(atm_id=f"atm_{i}", true_state=true_state))
    return atms


def maybe_flip_states(
    atms: list[ATM],
    seed: int,
    flip_probability: float = 0.0,
) -> None:
    """
    Original Phase 1 mechanism: instantaneous, timestamp-blind flip.
    Mutates ATM.true_state in place. Does NOT set flip_time or
    pre_flip_state — any report generated afterward via
    report_stream.generate_reports() will treat the ATM as having
    always been in its (new) true_state, since there is no flip_time
    for it to compare a report's timestamp against.

    Kept for scenarios that don't need per-report staleness (e.g.
    testing Majority Vote / Reputation-Weighted robustness to sudden,
    uniform ground-truth changes between report generation and query).
    """
    rng = random.Random(seed)
    for atm in atms:
        if rng.random() < flip_probability:
            atm.true_state = not atm.true_state


def generate_flip_times(
    atms: list[ATM],
    seed: int,
    flip_probability: float = 0.0,
    time_window: float = 60.0,
) -> None:
    """
    Assign a subset of ATMs a flip_time within [0, time_window] and
    record their pre_flip_state, producing a genuine per-report
    staleness gradient rather than an instantaneous, timestamp-blind
    change (see module docstring).

    Mutates ATMs in place:
        - For a chosen fraction (flip_probability) of ATMs:
            pre_flip_state = current true_state (the "old" state)
            flip_time = a time drawn uniformly from [0, time_window]
            true_state = NOT pre_flip_state (the new, current/final
                state, used for scoring against via compute_accuracy())
        - For all other ATMs: flip_time stays None, pre_flip_state
          stays None (true_state applies for the entire window).

    Args:
        atms: The ATMs to potentially assign flip times to.
        seed: Random seed for this pass.
        flip_probability: Probability that a given ATM changes state
            partway through the report window.
        time_window: The report-generation window; flip_time is drawn
            from within this range so it aligns with report timestamps
            (which are also drawn from [0, time_window] — see
            report_stream.generate_reports()).
    """
    rng = random.Random(seed)
    for atm in atms:
        if rng.random() < flip_probability:
            atm.pre_flip_state = atm.true_state
            atm.flip_time = rng.uniform(0.0, time_window)
            atm.true_state = not atm.pre_flip_state


def true_state_at(atm: ATM, timestamp: float) -> bool:
    """
    The ATM's true state as of a given simulated timestamp, accounting
    for a mid-window flip if one was assigned via generate_flip_times().

    Args:
        atm: The ATM to check.
        timestamp: The simulated time to evaluate state at (typically a
            report's timestamp, when called from report generation).

    Returns:
        atm.pre_flip_state if the ATM has a flip_time and timestamp is
        before it; atm.true_state otherwise (covers both "never
        flipped" and "at/after flip_time").
    """
    if atm.flip_time is not None and timestamp < atm.flip_time:
        return atm.pre_flip_state
    return atm.true_state
