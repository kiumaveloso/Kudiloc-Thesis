"""
Reporter population generator for the KudiLoc simulation.

Generates a population of Reporters with varying reliability and a
configurable fraction of adversarial reporters. This directly powers
RQ2 (how each algorithm responds as the proportion of unreliable/
adversarial reporters increases) via the adversarial_fraction sweep.
"""

import random

from src.simulation.models import Reporter


def generate_reporters(
    num_reporters: int,
    seed: int,
    adversarial_fraction: float = 0.1,
    reliability_mean: float = 0.85,
    reliability_spread: float = 0.1,
) -> list[Reporter]:
    """
    Create a population of reporters with randomly assigned reliability,
    and mark a fraction of them as adversarial.

    Args:
        num_reporters: How many reporters to generate.
        seed: Random seed, for reproducibility across experiment runs.
        adversarial_fraction: Fraction (0.0-1.0) of reporters who are
            adversarial (deliberately misreport). This is the independent
            variable swept in RQ2 experiments.
        reliability_mean: Target average reliability for non-adversarial
            reporters. Reliability is drawn from a distribution centered
            here and clamped to [0.0, 1.0].
        reliability_spread: Roughly how much individual reliability varies
            around the mean (higher = more variation between reporters).

    Returns:
        A list of Reporter objects with ids "reporter_0", "reporter_1", ...
    """
    rng = random.Random(seed)
    num_adversarial = round(num_reporters * adversarial_fraction)

    # Decide which reporter indices are adversarial, chosen randomly
    # rather than just the first N, to avoid any accidental ordering bias.
    adversarial_indices = set(
        rng.sample(range(num_reporters), k=num_adversarial)
    )

    reporters = []
    for i in range(num_reporters):
        is_adversarial = i in adversarial_indices

        # Reliability drawn from a normal distribution, clamped to [0, 1].
        # Adversarial reporters still get a reliability value for data
        # consistency, but algorithms should generally treat is_adversarial
        # reporters as untrustworthy regardless of this number, since it's
        # their deliberate misreporting (not noise) that matters.
        raw_reliability = rng.gauss(reliability_mean, reliability_spread)
        reliability = min(1.0, max(0.0, raw_reliability))

        reporters.append(
            Reporter(
                reporter_id=f"reporter_{i}",
                reliability=reliability,
                is_adversarial=is_adversarial,
            )
        )
    return reporters