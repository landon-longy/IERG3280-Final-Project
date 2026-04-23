# IERG 3280 Auction Simulation Project

This repository contains the course project for `IERG 3280: Networks: Technology, Economics, and Social Interactions`.

The project studies the robustness of two multi-slot auction mechanisms:

- `GSP` (Generalized Second Price)
- `VCG` (Vickrey-Clarke-Groves)

The simulator evaluates these mechanisms under three non-ideal factors:

- `heterogeneous bidders`
- `collusion`
- `network latency`

The report and experiments follow a one-factor-at-a-time design with two reference baselines:

- `all-truthful`
- `balanced 1:1:1:1 heterogeneous market`

## Repository Structure

- `auction_sim/`: core data structures, scenario generation, simulation logic, metrics, and the local web app
- `experiments/run_experiments.py`: entry point for the full report experiment bundle
- `tests/`: regression tests for the simulator
- `outputs/final_report/`: generated figures, summary tables, bibliography, and report files

## Quick Start

Run the main experiment bundle:

```bash
python3 experiments/run_experiments.py
```

This generates report-ready outputs in `outputs/final_report/`, including:

- `experiment_summary.json`
- `experiment_summary.csv`
- heterogeneous revenue and welfare figures
- collusion revenue, welfare, and VCG revenue-loss figures
- latency revenue, welfare, efficiency, and late-bid figures

The current main experiment configuration in `experiments/run_experiments.py` uses:

- `20` bidders
- `5` slots
- `300` rounds
- seed `3280`
- collusion rate `0.3`
- latency scale `58 ms`

## Web App

Start the local interface with:

```bash
python3 -m auction_sim.webapp
```

Then open:

```text
http://127.0.0.1:8000
```

If port `8000` is already in use, stop the existing process first:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
kill <PID>
```

### What the Web App Supports

The web app is a lightweight local control panel for exploring the simulator. It supports:

- scenario selection: `heterogeneous`, `collusion`, `latency`
- mechanism selection: `GSP` or `VCG`
- custom `number of users`
- custom `number of slots`
- custom bounded value range through `value_min` and `value_max`
- adjustable summary rounds

It also exposes scenario-specific controls:

- `heterogeneous`: manually assign the number of `truthful`, `shaded`, `budget`, and `aggressive` bidders
- `collusion`: choose the number of collusive users
- `latency`: adjust base latency and the bid deadline within preset bounds

After running, the page shows:

- a summary card view for key metrics
- the full JSON response for the single-run result
- the scenario-level comparison summary

### Notes on Inputs

- In the `heterogeneous` view, the four bidder-type counts must sum to the total number of users.
- In the `collusion` view, the app converts the collusive-user count into a collusion ratio internally.
- In the `latency` view, the app still uses the built-in type-specific latency stress logic; the UI only adjusts the global latency scale and deadline.

## Simulation Design

The simulator currently uses these built-in modeling choices:

- slot CTRs are generated from a preset decay pattern
- bidder values are sampled uniformly within a configurable range
- bidder heterogeneity is represented by four stylized bidder types
- collusion is modeled through a simple proxy-bidding rule
- latency is modeled through random delays plus type-specific penalties

These simplifications match the report design and keep the experiments interpretable.

## Testing

Run the regression tests with:

```bash
python3 -m unittest tests.test_simulation
```

The tests cover:

- basic single-run sanity checks
- collusion comparison outputs
- batch experiment structure
- custom market inputs such as bidder count, slot count, value range, and bidder-type counts

## Current Status

The following checks have been run successfully on the current codebase:

- `python3 -m unittest tests.test_simulation`
- `python3 experiments/run_experiments.py`

So the simulator, report experiment pipeline, and current UI-backed parameter path are all working consistently with the present code structure.
