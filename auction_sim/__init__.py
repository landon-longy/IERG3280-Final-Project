"""Auction simulation package for the IERG3280 project."""

from .core import AuctionConfig, AuctionResult, Bidder, SimulationConfig
from .simulation import (
    compare_mechanisms,
    run_batch_experiments,
    run_single_auction,
    run_single_scenario,
)

__all__ = [
    "AuctionConfig",
    "AuctionResult",
    "Bidder",
    "SimulationConfig",
    "compare_mechanisms",
    "run_batch_experiments",
    "run_single_auction",
    "run_single_scenario",
]
