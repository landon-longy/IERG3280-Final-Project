from __future__ import annotations

import math
from typing import Dict, Iterable, List

from .core import Allocation, AuctionMetrics, Bidder


def gini(values: Iterable[float]) -> float:
    numbers = sorted(float(value) for value in values)
    if not numbers:
        return 0.0
    total = sum(numbers)
    if abs(total) < 1e-12:
        return 0.0
    weighted_sum = sum((idx + 1) * value for idx, value in enumerate(numbers))
    return round((2 * weighted_sum) / (len(numbers) * total) - (len(numbers) + 1) / len(numbers), 4)


def summarize_metrics(
    allocations: List[Allocation],
    bidders: List[Bidder],
    bids: Dict[str, float],
    truthful_bids: Dict[str, float],
    arrival_times: Dict[str, int],
    deadline_ms: int,
) -> AuctionMetrics:
    bidder_map = {bidder.bidder_id: bidder for bidder in bidders}
    utilities = [allocation.utility for allocation in allocations]
    revenue = sum(allocation.payment for allocation in allocations)
    welfare = sum(allocation.value * allocation.ctr for allocation in allocations)

    sorted_values = sorted((bidder.true_value for bidder in bidders), reverse=True)
    ideal_welfare = 0.0
    for idx, allocation in enumerate(allocations):
        if idx < len(sorted_values):
            ideal_welfare += allocation.ctr * sorted_values[idx]
    efficiency = welfare / ideal_welfare if ideal_welfare else 0.0

    payoff_mean = sum(utilities) / len(utilities) if utilities else 0.0
    variance = sum((value - payoff_mean) ** 2 for value in utilities) / len(utilities) if utilities else 0.0
    payoff_std = math.sqrt(variance)
    on_time = sum(1 for bidder in bidders if arrival_times[bidder.bidder_id] <= deadline_ms)
    late = len(bidders) - on_time
    truthful_gap = sum(abs(bids[bidder.bidder_id] - truthful_bids[bidder.bidder_id]) for bidder in bidders) / len(bidders)
    collusion_discount = 0.0
    colluders = [bidder for bidder in bidders if bidder.collusion_group]
    if colluders:
        collusion_discount = sum(
            truthful_bids[bidder.bidder_id] - bids[bidder.bidder_id] for bidder in colluders
        ) / len(colluders)

    return AuctionMetrics(
        revenue=round(revenue, 4),
        social_welfare=round(welfare, 4),
        efficiency=round(efficiency, 4),
        payoff_mean=round(payoff_mean, 4),
        payoff_std=round(payoff_std, 4),
        utility_gini=gini(max(0.0, utility) for utility in utilities),
        on_time_rate=round(on_time / len(bidders), 4),
        late_bid_rate=round(late / len(bidders), 4),
        truthful_gap=round(truthful_gap, 4),
        winner_count=len(allocations),
        collusion_discount=round(collusion_discount, 4),
    )
