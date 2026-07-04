"""
Ground truth generator for the KudiLoc simulation.

Generates a population of ATMs with a known true state, and supports
optional state changes over simulated time. Ground truth is only ever
used by the simulator to generate reports and to score accuracy — the
aggregation algorithms never see it directly (see Methodology, Section 5).
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

    Args:
        num_atms: How many ATMs to generate.
        seed: Random seed, for reproducibility across experiment runs
            with multiple seeds (see Section 6, Experimental Design).
        initial_stocked_probability: Probability that a given ATM starts
            in the "stocked" state. Defaults to 0.7, reflecting that most
            ATMs are usually working; adjust later if experiments call
            for different baseline conditions.

    Returns:
        A list of ATM objects with ids "atm_0", "atm_1", ... and randomly
        assigned true_state values.
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
    Optionally flip each ATM's state with some probability, simulating
    real-world changes (an ATM runs out of cash, or gets refilled)
    between the time reports are generated and query time.

    Mutates the ATM objects in place.

    Args:
        atms: The list of ATMs to potentially update.
        seed: Random seed for this flip pass (use a different seed than
            generate_atms() if you want independent randomness).
        flip_probability: Probability that any given ATM's state flips.
            Defaults to 0.0 (no flipping) so early tests can ignore this
            complexity until it's specifically needed for RQ3 experiments.
    """
    rng = random.Random(seed)
    for atm in atms:
        if rng.random() < flip_probability:
            atm.true_state = not atm.true_state