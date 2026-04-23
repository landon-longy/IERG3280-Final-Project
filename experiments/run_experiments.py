from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from auction_sim.core import SimulationConfig
from auction_sim.simulation import export_results, run_batch_experiments


def main() -> None:
    output_dir = Path("outputs/final_report")
    config = SimulationConfig(rounds=300, num_bidders=20, num_slots=5, seed=3280, collusion_rate=0.3, latency_scale_ms=58)
    bundle = run_batch_experiments(config)
    export_results(bundle, output_dir)
    collusion = next(item["comparisons"] for item in bundle["collusion"]["sweep"] if abs(item["collusion_rate"] - 0.3) < 1e-9)
    print("Experiment bundle written to", output_dir)
    print("Collusion revenue loss of VCG vs GSP:")
    print("  absolute loss:", collusion["vcg_revenue_loss_vs_gsp"])
    print("  percentage loss:", f"{collusion['vcg_revenue_loss_pct_vs_gsp']:.2f}%")


if __name__ == "__main__":
    main()
