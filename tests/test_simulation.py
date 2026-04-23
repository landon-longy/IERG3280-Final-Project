import unittest

from auction_sim.core import SimulationConfig
from auction_sim.simulation import compare_mechanisms, run_batch_experiments, run_single_scenario


class SimulationTests(unittest.TestCase):
    def test_single_run_produces_reasonable_metrics(self) -> None:
        result = run_single_scenario(
            scenario="heterogeneous",
            mechanism="GSP",
            sim_config=SimulationConfig(rounds=5, seed=100),
        )
        self.assertEqual(result.mechanism, "GSP")
        self.assertGreaterEqual(result.metrics.efficiency, 0)
        self.assertLessEqual(result.metrics.efficiency, 1.2)
        self.assertGreaterEqual(result.metrics.revenue, 0)
        self.assertLessEqual(len(result.allocations), 4)

    def test_compare_mechanisms_contains_collusion_revenue_loss(self) -> None:
        bundle = compare_mechanisms(
            scenario="collusion",
            sim_config=SimulationConfig(rounds=25, seed=42),
        )
        self.assertIn("comparisons", bundle)
        self.assertIn("vcg_revenue_loss_vs_gsp", bundle["comparisons"])
        self.assertIn("vcg_revenue_loss_pct_vs_gsp", bundle["comparisons"])

    def test_batch_experiments_match_one_factor_design(self) -> None:
        bundle = run_batch_experiments(SimulationConfig(rounds=8, seed=7))
        self.assertIn("heterogeneous", bundle)
        self.assertIn("profiles", bundle["heterogeneous"])
        self.assertIn("truthful_reference", bundle["heterogeneous"])
        self.assertIn("truthful_heavy", bundle["heterogeneous"]["profiles"])
        self.assertEqual(len(bundle["collusion"]["sweep"]), 9)
        self.assertIn("latency_case", bundle["latency"])

    def test_custom_market_inputs_are_respected(self) -> None:
        config = SimulationConfig(rounds=6, seed=11, num_bidders=10, num_slots=3, value_min=1.1, value_max=1.4)
        result = run_single_scenario(
            scenario="heterogeneous",
            mechanism="VCG",
            sim_config=config,
            type_counts={"truthful": 2, "shaded": 3, "budget": 1, "aggressive": 4},
        )
        self.assertEqual(len(result.bidders), 10)
        self.assertLessEqual(len(result.allocations), 3)
        self.assertTrue(all(1.1 <= bidder.true_value <= 1.4 for bidder in result.bidders))
        counts = {}
        for bidder in result.bidders:
            counts[bidder.bidder_type] = counts.get(bidder.bidder_type, 0) + 1
        self.assertEqual(counts["truthful"], 2)
        self.assertEqual(counts["shaded"], 3)
        self.assertEqual(counts["budget"], 1)
        self.assertEqual(counts["aggressive"], 4)


if __name__ == "__main__":
    unittest.main()
