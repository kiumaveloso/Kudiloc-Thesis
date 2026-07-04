"""
Report stream generator for the KudiLoc simulation.

Given a set of ATMs (with true states) and a population of Reporters,
generates timestamped Report objects. Reliable reporters report the
true state with probability equal to their reliability; adversarial
reporters deliberately report the opposite of the true state. This
directly powers the report density (independent variable) and, via
timestamps, the staleness experiments for RQ3.
"""

import random

from src.simulation.models import ATM, Reporter, Report


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
        atms: The ATMs to generate reports for (with current true_state).
        reporters: The reporter population submitting reports.
        seed: Random seed, for reproducibility across experiment runs.
        report_probability: Probability that any given reporter submits
            a report for any given ATM. Controls report density — the
            independent variable described in Section 6.
        time_window: Reports are timestamped uniformly at random within
            [0, time_window]. Used later to compute staleness relative
            to a query_time (RQ3).

    Returns:
        A list of Report objects, unsorted, covering all ATMs.
    """
    rng = random.Random(seed)
    reports = []

    for atm in atms:
        for reporter in reporters:
            if rng.random() >= report_probability:
                continue  # this reporter didn't report on this ATM

            if reporter.is_adversarial:
                # Deliberately misreport the opposite of the true state.
                claimed_state = not atm.true_state
            else:
                # Report correctly with probability = reliability,
                # otherwise report the opposite (an honest mistake).
                claimed_state = (
                    atm.true_state
                    if rng.random() < reporter.reliability
                    else not atm.true_state
                )

            timestamp = rng.uniform(0.0, time_window)

            reports.append(
                Report(
                    atm_id=atm.atm_id,
                    reporter_id=reporter.reporter_id,
                    claimed_state=claimed_state,
                    timestamp=timestamp,
                )
            )

    return reports