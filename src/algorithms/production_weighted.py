"""
Production-rule variant of Reputation-Weighted Aggregation.

The simulation's Reputation-Weighted Aggregation uses a multiplicative
reputation update (x1.1 correct, x0.9 incorrect, clamped to
[0.01, 10.0]) and weights each report by the reputation value directly.
The deployed KudiLoc system instead uses an additive update (+2 correct,
-3 incorrect, clamped to [0, 100]) and a weight of 0.5 + reputation/100,
which confines every report to the range [0.5, 1.5].

This class implements the production weighting so that the two rules can
be compared under identical conditions, testing whether the conclusions
of this thesis depend on the specific arithmetic used.
"""

from src.simulation.models import AggregationAlgorithm, Report, Reporter


class ProductionWeightedAggregation(AggregationAlgorithm):
    """
    Weights each report by 0.5 + reputation/100, reading a separate
    production_reputation attribute maintained on the Reporter by
    update_production_reputations(). Tie-breaking matches the other
    algorithms: returns True (stocked) on a tie or with no reports.
    """

    def aggregate(
        self,
        reports: list[Report],
        query_time: float,
        reporters: dict[str, Reporter] | None = None,
    ) -> bool:
        if reporters is None:
            raise ValueError(
                "ProductionWeightedAggregation requires a reporters lookup."
            )

        stocked_weight = 0.0
        empty_weight = 0.0

        for report in reports:
            reporter = reporters[report.reporter_id]
            score = getattr(reporter, "production_reputation", 50.0)
            weight = 0.5 + (score / 100.0)
            if report.claimed_state:
                stocked_weight += weight
            else:
                empty_weight += weight

        return stocked_weight >= empty_weight
