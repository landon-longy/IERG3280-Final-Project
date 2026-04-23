from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AuctionConfig:
    slot_ctrs: List[float]
    reserve_price: float = 0.05
    bid_deadline_ms: int = 120


@dataclass(frozen=True)
class SimulationConfig:
    num_bidders: int = 12
    num_slots: int = 4
    rounds: int = 250
    seed: int = 3280
    collusion_rate: float = 0.25
    latency_scale_ms: int = 55
    bid_deadline_ms: int = 120
    value_min: float = 0.35
    value_max: float = 3.2


@dataclass
class Bidder:
    bidder_id: str
    true_value: float
    bidder_type: str
    budget: float
    shading_factor: float
    latency_ms: int
    collusion_group: Optional[str] = None
    metadata: Dict[str, float] = field(default_factory=dict)


@dataclass
class Allocation:
    slot: int
    bidder_id: str
    ctr: float
    bid: float
    payment: float
    utility: float
    value: float
    on_time: bool


@dataclass
class AuctionMetrics:
    revenue: float
    social_welfare: float
    efficiency: float
    payoff_mean: float
    payoff_std: float
    utility_gini: float
    on_time_rate: float
    late_bid_rate: float
    truthful_gap: float
    winner_count: int
    collusion_discount: float


@dataclass
class AuctionResult:
    mechanism: str
    scenario: str
    bidders: List[Bidder]
    allocations: List[Allocation]
    bids: Dict[str, float]
    truthful_bids: Dict[str, float]
    arrival_times: Dict[str, int]
    metrics: AuctionMetrics
