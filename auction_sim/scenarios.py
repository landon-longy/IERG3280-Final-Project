from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .core import Bidder, SimulationConfig


TRUTHFUL_ONLY_TYPE_MIX: Dict[str, float] = {
    "truthful": 1.0,
    "shaded": 0.0,
    "budget": 0.0,
    "aggressive": 0.0,
}

BALANCED_TYPE_MIX: Dict[str, float] = {
    "truthful": 0.25,
    "shaded": 0.25,
    "budget": 0.25,
    "aggressive": 0.25,
}

HETEROGENEOUS_MIXES: Dict[str, Dict[str, float]] = {
    "truthful_heavy": {"truthful": 0.55, "shaded": 0.15, "budget": 0.15, "aggressive": 0.15},
    "shaded_heavy": {"truthful": 0.15, "shaded": 0.55, "budget": 0.15, "aggressive": 0.15},
    "budget_heavy": {"truthful": 0.15, "shaded": 0.15, "budget": 0.55, "aggressive": 0.15},
    "aggressive_heavy": {"truthful": 0.15, "shaded": 0.15, "budget": 0.15, "aggressive": 0.55},
}


def default_slot_ctrs(num_slots: int) -> List[float]:
    presets = [1.0, 0.82, 0.64, 0.49, 0.37, 0.28]
    if num_slots <= len(presets):
        return presets[:num_slots]
    tail = presets[:]
    while len(tail) < num_slots:
        tail.append(max(0.05, round(tail[-1] * 0.78, 3)))
    return tail


def build_bidders(
    scenario: str,
    sim_config: SimulationConfig,
    rng: random.Random,
    type_mix: Optional[Dict[str, float]] = None,
    type_counts: Optional[Dict[str, int]] = None,
    collusion_rate_override: Optional[float] = None,
) -> Tuple[List[Bidder], Dict[str, List[str]]]:
    bidders: List[Bidder] = []
    collusion_groups: Dict[str, List[str]] = {}
    pool = ["truthful", "shaded", "budget", "aggressive"]
    bidder_types: List[str] = []
    weights: List[float] | None = None

    if type_counts:
        for bidder_type in pool:
            bidder_types.extend([bidder_type] * max(0, type_counts.get(bidder_type, 0)))
        rng.shuffle(bidder_types)
    else:
        effective_mix = type_mix or BALANCED_TYPE_MIX
        weights = [effective_mix[bidder_type] for bidder_type in pool]

    for idx in range(sim_config.num_bidders):
        bidder_type = bidder_types[idx] if type_counts else rng.choices(pool, weights=weights)[0]

        true_value = round(rng.uniform(sim_config.value_min, sim_config.value_max), 3)
        budget = round(rng.uniform(0.8, 4.4), 3)
        shading_factor = {
            "truthful": 1.0,
            "shaded": rng.uniform(0.55, 0.9),
            "budget": rng.uniform(0.65, 0.95),
            "aggressive": rng.uniform(1.02, 1.12),
        }[bidder_type]
        latency = max(0, int(rng.gauss(sim_config.latency_scale_ms, sim_config.latency_scale_ms * 0.45)))
        bidders.append(
            Bidder(
                bidder_id=f"b{idx + 1}",
                true_value=true_value,
                bidder_type=bidder_type,
                budget=budget,
                shading_factor=round(shading_factor, 3),
                latency_ms=latency,
            )
        )

    if scenario == "collusion":
        collusion_rate = sim_config.collusion_rate if collusion_rate_override is None else collusion_rate_override
        target = max(2, int(sim_config.num_bidders * collusion_rate))
        members = rng.sample(bidders, k=min(target, len(bidders)))
        group_id = "ring-1"
        collusion_groups[group_id] = [bidder.bidder_id for bidder in members]
        for bidder in members:
            bidder.collusion_group = group_id
            bidder.metadata["collusive"] = 1.0

    if scenario == "latency":
        for bidder in bidders:
            if bidder.bidder_type == "truthful":
                bidder.latency_ms += int(rng.uniform(25, 70))
            if bidder.bidder_type == "budget":
                bidder.latency_ms += int(rng.uniform(10, 45))

    return bidders, collusion_groups


def compute_bids(
    bidders: List[Bidder],
    scenario: str,
    reserve_price: float,
    slot_ctrs: List[float],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    bids: Dict[str, float] = {}
    truthful_bids: Dict[str, float] = {}
    top_ctr = slot_ctrs[0] if slot_ctrs else 1.0
    group_members: Dict[str, List[Bidder]] = {}

    for bidder in bidders:
        truthful = min(bidder.true_value, bidder.budget / max(top_ctr, 0.1))
        truthful = max(reserve_price, round(truthful, 3))
        truthful_bids[bidder.bidder_id] = truthful
        if bidder.collusion_group:
            group_members.setdefault(bidder.collusion_group, []).append(bidder)

    collusive_bids: Dict[str, float] = {}
    for members in group_members.values():
        ordered = sorted(members, key=lambda item: item.true_value, reverse=True)
        proxy = ordered[0]
        collusive_bids[proxy.bidder_id] = max(reserve_price, round(proxy.true_value * 0.72, 3))
        for follower in ordered[1:]:
            collusive_bids[follower.bidder_id] = reserve_price

    for bidder in bidders:
        if bidder.bidder_id in collusive_bids and scenario == "collusion":
            bid = collusive_bids[bidder.bidder_id]
        elif bidder.bidder_type == "truthful":
            bid = truthful_bids[bidder.bidder_id]
        elif bidder.bidder_type == "shaded":
            bid = bidder.true_value * bidder.shading_factor
        elif bidder.bidder_type == "budget":
            affordable = bidder.budget / max(top_ctr, 0.1)
            bid = min(bidder.true_value * bidder.shading_factor, affordable)
        else:
            bid = bidder.true_value * bidder.shading_factor

        bids[bidder.bidder_id] = max(reserve_price, round(min(bid, bidder.budget / max(top_ctr, 0.1) * 1.1), 3))

    return bids, truthful_bids
