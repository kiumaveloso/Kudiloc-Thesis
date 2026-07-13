"""
Core data model for the KudiLoc truth-aggregation simulation.

Defines the three basic entities of the simulation (ATM, Reporter, Report)
and the shared AggregationAlgorithm interface that Majority Vote,
Reputation-Weighted Aggregation, and Time-Decayed Trust Scoring will all
implement. Keeping this interface identical across algorithms is what
lets the experiment isolate the effect of the aggregation logic itself
(see Methodology, Section 5 of the thesis proposal).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ATM:
    """
    A single ATM with a true, hidden state that the aggregation
    algorithms are trying to recover from noisy reports.

    Attributes:
        atm_id: Unique identifier for this ATM.
        true_state: The ground-truth state at the current simulated time
            (True = stocked / has cash, False = empty / out of service).
            This value is known to the simulator but NOT visible to the
            aggregation algorithms — they only ever see Reports.
        flip_time: If this ATM's state changed partway through the
            report-generation window, the simulated time at which the
            change occurred. None means the ATM never changed state
            during the window (true_state held throughout the run).
        pre_flip_state: The ATM's state BEFORE flip_time, only
            meaningful when flip_time is not None. Reports timestamped
            before flip_time are checked against this value; reports
            at or after flip_time are checked against true_state. This
            makes staleness a genuine per-report property instead of
            an instantaneous, timestamp-blind toggle on the whole ATM.
    """
    atm_id: str
    true_state: bool
    flip_time: float | None = None
    pre_flip_state: bool | None = None


@dataclass
class Reporter:
    """
    A user in the crowd-sourcing population who submits reports about
    ATM states.

    Attributes:
        reporter_id: Unique identifier for this reporter.
        reliability: Probability (0.0-1.0) that a non-adversarial reporter
            submits the correct state. A reliability of 0.9 means the
            reporter is honest but sometimes mistaken (e.g. misjudges a
            machine, reports stale info they believe is current).
        is_adversarial: If True, this reporter deliberately misreports
            (flips the true state) rather than simply being noisy. This is
            distinct from low reliability: an adversarial reporter is not
            "unlucky," they are actively trying to corrupt the aggregate
            (see RQ2 and the adversarial-bloc scenario in Section 6).
        reputation: Running trust score, updated during the simulation
            when ground truth is periodically revealed (see Section 5).
            Starts neutral; only meaningful once Reputation-Weighted /
            Time-Decayed algorithms begin updating it.
    """
    reporter_id: str
    reliability: float
    is_adversarial: bool = False
    reputation: float = 1.0


@dataclass(frozen=True)
class Report:
    """
    A single timestamped claim submitted by a Reporter about an ATM's
    state. Reports are immutable once created — they are the "observed
    data" the aggregation algorithms consume.

    Attributes:
        atm_id: Which ATM this report concerns.
        reporter_id: Who submitted the report.
        claimed_state: The state the reporter is claiming
            (True = stocked, False = empty).
        timestamp: Simulated time the report was submitted (float, e.g.
            minutes or hours since simulation start). Used for staleness
            calculations (RQ3).
    """
    atm_id: str
    reporter_id: str
    claimed_state: bool
    timestamp: float


class AggregationAlgorithm(ABC):
    """
    Shared interface for all truth-aggregation algorithms.

    Every algorithm (Majority Vote, Reputation-Weighted, Time-Decayed
    Trust Scoring) implements aggregate() with this exact signature.
    This isolates the effect of the aggregation logic: the simulation
    harness, ground truth, reporter population, and report stream are
    identical regardless of which algorithm is plugged in.
    """

    @abstractmethod
    def aggregate(
        self,
        reports: list[Report],
        query_time: float,
        reporters: dict[str, Reporter] | None = None,
    ) -> bool:
        """
        Estimate the true state of an ATM given its available reports.

        Args:
            reports: All reports available for a single ATM at query
                time (already filtered to the relevant atm_id upstream,
                or filtering may happen inside this method — decide and
                document this consistently once implemented).
            query_time: The simulated time at which the estimate is
                requested. Needed by time-aware algorithms to compute
                report staleness (age = query_time - report.timestamp).
            reporters: Optional lookup of reporter_id -> Reporter, needed
                by reputation-aware algorithms to read reliability/
                reputation weights. Majority Vote ignores this.

        Returns:
            The estimated state (True = stocked, False = empty).
        """
        raise NotImplementedError