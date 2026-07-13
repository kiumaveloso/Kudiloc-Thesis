"""
Report stream generator for the KudiLoc simulation.

Given a set of ATMs (with true states, optionally with a flip_time —
see ground_truth.py) and a population of Reporters, generates
timestamped Report objects.

Reliable reporters report the true state (AS OF THEIR REPORT'S OWN
TIMESTAMP — see ground_truth.true_state_at()) with probability equal to
their reliability; adversarial reporters deliberately report the
opposite of that state. Checking state per-report-timestamp, rather
than a single static ATM.true_state, is what makes staleness a genuine
property of individual reports: a report submitted before an ATM's
flip_time correctly describes the old state (and only becomes "wrong"
relative to the FINAL true_state used for scoring), while a report
submitted after flip_time already describes the new state. This is the
recency-correctness gradient Time-Decayed Trust Scoring is designed to
exploit — see dev_log.md.
"""
import random
from src.simulation.models import ATM, Reporter, Report
from src.simulation.ground_truth import true_state_at


def generate_reports(
    atms: list[ATM],
    reporters: list[Reporter],
    seed: int,
    report_probability: float = 0.3,
    time_window: float = 60.0,
) -> list[Report]:
    """
    Generate a stream of reports for a set of ATMs from a reporter
    population.

    Args:
        atms: The ATMs to generate reports for. If an ATM has a
            flip_time (set via ground_truth.generate_flip_times()),
            reports are checked against its state AT THEIR OWN
            timestamp, not its final true_state.
        reporters: The reporter population submitting reports.
        seed: Random seed, for reproducibility across experiment runs.
        report_probability: Probability that any given reporter submits
            a report for any given ATM.
        time_window: Reports are timestamped uniformly at random within
            [0, time_window].

    Returns:
        A list of Report objects, unsorted, covering all ATMs.
    """
    rng = random.Random(seed)
    reports = []
    for atm in atms:
        for reporter in reporters:
            if rng.random() >= report_probability:
                continue  # this reporter didn't report on this ATM

            # Draw the timestamp FIRST, then determine what was actually
            # true at that moment — this ordering is what makes staleness
            # a per-report property instead of a single static check.
            timestamp = rng.uniform(0.0, time_window)
            state_at_report_time = true_state_at(atm, timestamp)

            if reporter.is_adversarial:
                claimed_state = not state_at_report_time
            else:
                claimed_state = (
                    state_at_report_time
                    if rng.random() < reporter.reliability
                    else not state_at_report_time
                )

            reports.append(
                Report(
                    atm_id=atm.atm_id,
                    reporter_id=reporter.reporter_id,
                    claimed_state=claimed_state,
                    timestamp=timestamp,
                )
            )
    return reports
