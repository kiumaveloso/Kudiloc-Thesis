"""
Time-Decayed Trust Scoring algorithm.

Combines Reputation-Weighted Aggregation's trust weighting with an
exponential decay based on report age (query_time - report.timestamp).
A report's influence on the aggregate is highest when fresh and fades
smoothly the older it gets, on top of (not instead of) the reporter's
underlying reputation weight.

    weight = reputation * exp(-lambda_ * age)

This targets a different failure mode than Reputation-Weighted alone:
a highly reputable reporter's OLD report about an ATM can still be
wrong simply because the ATM's real-world state has since changed
(e.g. it was stocked yesterday but is empty now). Reputation alone
cannot capture that; decay can.

Default decay rate corresponds to a 12-hour half-life, under the
modeling assumption that one simulated time unit represents one hour
(see dev_log.md and the methodology chapter's staleness discussion,
RQ3). This value is a deliberate modeling choice reflecting realistic
ATM cash-availability volatility in the Angola crowd-sourcing context,
not an empirically derived constant — flagged accordingly as a
methodology assumption rather than a cited fact.

lambda_ is exposed as a parameter specifically to support a decay-rate
sensitivity check (e.g. re-running with 6h/12h/24h half-lives) as a
robustness argument in the results chapter.
"""

import math

from src.simulation.models import AggregationAlgorithm, Report, Reporter

# Half-life in simulated time units (see module docstring: 1 unit = 1 hour
# under the modeling assumption used throughout this thesis).
DEFAULT_HALF_LIFE: float = 12.0
DEFAULT_LAMBDA: float = math.log(2) / DEFAULT_HALF_LIFE  # ~0.0578


class TimeDecayedTrustScoring(AggregationAlgorithm):
    """
    Aggregates reports by weighting each report with
    reputation * exp(-lambda_ * age), then returning whichever side
    ("stocked" or "empty") has the greater total weight.

    Requires the `reporters` lookup (same reason as
    ReputationWeightedAggregation: reputation lives on the Reporter
    object, not the Report).

    Attributes:
        lambda_: Decay rate constant. Larger values make reports go
            stale faster. Defaults to DEFAULT_LAMBDA (12-hour
            half-life). Exposed as a constructor parameter so the same
            class can be re-instantiated with different half-lives for
            a decay-rate sensitivity experiment.
    """

    def __init__(self, lambda_: float = DEFAULT_LAMBDA) -> None:
        """
        Args:
            lambda_: Exponential decay rate. Use
                `math.log(2) / half_life` to derive this from a chosen
                half-life in simulated time units, rather than picking
                lambda_ directly — half-life is the more interpretable
                and more easily justified quantity for the methodology
                chapter.
        """
        self.lambda_ = lambda_

    def aggregate(
        self,
        reports: list[Report],
        query_time: float,
        reporters: dict[str, Reporter] | None = None,
    ) -> bool:
        """
        Estimate ATM state via reputation-and-recency-weighted vote.

        Args:
            reports: Reports for a single ATM at query time.
            query_time: The simulated time the estimate is requested.
                Used to compute each report's age as
                query_time - report.timestamp. Reports newer than
                query_time (negative age) are not expected under normal
                simulation flow; age is not clamped, so such a case
                would produce a decay factor greater than 1 rather than
                silently masking a data-generation bug upstream.
            reporters: Required. Lookup of reporter_id -> Reporter, used
                to read each report's reporter's current reputation.

        Returns:
            True (stocked) if total weight for "stocked" reports is
            >= total weight for "empty" reports, else False.

        Raises:
            ValueError: if `reporters` is None, for the same reason as
                ReputationWeightedAggregation — this algorithm cannot
                function without reputation data.
        """
        if reporters is None:
            raise ValueError(
                "TimeDecayedTrustScoring requires a reporters lookup "
                "(reporter_id -> Reporter) to read reputation weights; "
                "received None."
            )

        stocked_weight = 0.0
        empty_weight = 0.0

        for report in reports:
            reputation = reporters[report.reporter_id].reputation
            age = query_time - report.timestamp
            decay_factor = math.exp(-self.lambda_ * age)
            weight = reputation * decay_factor

            if report.claimed_state:
                stocked_weight += weight
            else:
                empty_weight += weight

        # Tie-breaking mirrors MajorityVote and ReputationWeighted for
        # consistency: defaults to True (stocked) when there are zero
        # reports or weights are exactly tied.
        if stocked_weight >= empty_weight:
            return True
        return False
