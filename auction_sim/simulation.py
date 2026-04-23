from __future__ import annotations

import csv
import json
import os
import random
import tempfile
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List

from .core import Allocation, AuctionConfig, AuctionResult, Bidder, SimulationConfig
from .metrics import summarize_metrics
from .scenarios import BALANCED_TYPE_MIX, HETEROGENEOUS_MIXES, TRUTHFUL_ONLY_TYPE_MIX, build_bidders, compute_bids, default_slot_ctrs


def _rank_bidders(
    bidders: Iterable[Bidder],
    bids: Dict[str, float],
    arrival_times: Dict[str, int],
    config: AuctionConfig,
) -> List[Bidder]:
    eligible = [bidder for bidder in bidders if arrival_times[bidder.bidder_id] <= config.bid_deadline_ms]
    eligible.sort(key=lambda bidder: (bids[bidder.bidder_id], bidder.true_value, -arrival_times[bidder.bidder_id]), reverse=True)
    return eligible[: len(config.slot_ctrs)]


def _gsp_allocations(
    ranked: List[Bidder],
    bidders: List[Bidder],
    bids: Dict[str, float],
    arrival_times: Dict[str, int],
    config: AuctionConfig,
) -> List[Allocation]:
    bidder_map = {bidder.bidder_id: bidder for bidder in bidders}
    ordered_bids = [bids[bidder.bidder_id] for bidder in ranked]
    if ranked:
        ordered_bids.append(config.reserve_price)
    allocations: List[Allocation] = []
    for idx, bidder in enumerate(ranked):
        ctr = config.slot_ctrs[idx]
        next_bid = max(config.reserve_price, ordered_bids[idx + 1] if idx + 1 < len(ordered_bids) else config.reserve_price)
        payment = ctr * next_bid
        utility = ctr * bidder_map[bidder.bidder_id].true_value - payment
        allocations.append(
            Allocation(
                slot=idx + 1,
                bidder_id=bidder.bidder_id,
                ctr=ctr,
                bid=bids[bidder.bidder_id],
                payment=round(payment, 4),
                utility=round(utility, 4),
                value=bidder_map[bidder.bidder_id].true_value,
                on_time=arrival_times[bidder.bidder_id] <= config.bid_deadline_ms,
            )
        )
    return allocations


def _vcg_allocations(
    ranked: List[Bidder],
    bidders: List[Bidder],
    bids: Dict[str, float],
    arrival_times: Dict[str, int],
    config: AuctionConfig,
) -> List[Allocation]:
    bidder_map = {bidder.bidder_id: bidder for bidder in bidders}
    ext_bids = [bids[bidder.bidder_id] for bidder in ranked] + [config.reserve_price]
    ctrs = list(config.slot_ctrs) + [0.0]
    allocations: List[Allocation] = []
    for idx, bidder in enumerate(ranked):
        payment = 0.0
        for follower in range(idx + 1, len(ranked) + 1):
            payment += (ctrs[follower - 1] - ctrs[follower]) * ext_bids[follower]
        ctr = config.slot_ctrs[idx]
        utility = ctr * bidder_map[bidder.bidder_id].true_value - payment
        allocations.append(
            Allocation(
                slot=idx + 1,
                bidder_id=bidder.bidder_id,
                ctr=ctr,
                bid=bids[bidder.bidder_id],
                payment=round(payment, 4),
                utility=round(utility, 4),
                value=bidder_map[bidder.bidder_id].true_value,
                on_time=arrival_times[bidder.bidder_id] <= config.bid_deadline_ms,
            )
        )
    return allocations


def run_single_auction(
    mechanism: str,
    scenario: str,
    bidders: List[Bidder],
    bids: Dict[str, float],
    truthful_bids: Dict[str, float],
    auction_config: AuctionConfig,
) -> AuctionResult:
    arrival_times = {bidder.bidder_id: bidder.latency_ms for bidder in bidders}
    ranked = _rank_bidders(bidders, bids, arrival_times, auction_config)
    if mechanism.upper() == "GSP":
        allocations = _gsp_allocations(ranked, bidders, bids, arrival_times, auction_config)
    else:
        allocations = _vcg_allocations(ranked, bidders, bids, arrival_times, auction_config)

    metrics = summarize_metrics(
        allocations=allocations,
        bidders=bidders,
        bids=bids,
        truthful_bids=truthful_bids,
        arrival_times=arrival_times,
        deadline_ms=auction_config.bid_deadline_ms,
    )
    return AuctionResult(
        mechanism=mechanism.upper(),
        scenario=scenario,
        bidders=bidders,
        allocations=allocations,
        bids=bids,
        truthful_bids=truthful_bids,
        arrival_times=arrival_times,
        metrics=metrics,
    )


def run_single_scenario(
    scenario: str,
    mechanism: str,
    sim_config: SimulationConfig,
    seed_offset: int = 0,
    type_mix: Dict[str, float] | None = None,
    type_counts: Dict[str, int] | None = None,
    collusion_rate_override: float | None = None,
) -> AuctionResult:
    rng = random.Random(sim_config.seed + seed_offset)
    slot_ctrs = default_slot_ctrs(sim_config.num_slots)
    bidders, _ = build_bidders(
        scenario=scenario,
        sim_config=sim_config,
        rng=rng,
        type_mix=type_mix,
        type_counts=type_counts,
        collusion_rate_override=collusion_rate_override,
    )
    bids, truthful_bids = compute_bids(
        bidders=bidders,
        scenario=scenario,
        reserve_price=0.05,
        slot_ctrs=slot_ctrs,
    )
    auction_config = AuctionConfig(slot_ctrs=slot_ctrs, reserve_price=0.05, bid_deadline_ms=sim_config.bid_deadline_ms)
    return run_single_auction(
        mechanism=mechanism,
        scenario=scenario,
        bidders=bidders,
        bids=bids,
        truthful_bids=truthful_bids,
        auction_config=auction_config,
    )


def _mean_metric(results: List[AuctionResult], metric_name: str) -> float:
    return round(mean(getattr(result.metrics, metric_name) for result in results), 4)


def _payoff_by_type(results: List[AuctionResult]) -> Dict[str, Dict[str, float]]:
    type_totals: Dict[str, Dict[str, float]] = {}
    for result in results:
        utility_map = {allocation.bidder_id: allocation.utility for allocation in result.allocations}
        for bidder in result.bidders:
            bucket = type_totals.setdefault(
                bidder.bidder_type,
                {"count": 0, "total_payoff": 0.0, "wins": 0, "total_bid": 0.0},
            )
            utility = utility_map.get(bidder.bidder_id, 0.0)
            bucket["count"] += 1
            bucket["total_payoff"] += utility
            bucket["wins"] += 1 if bidder.bidder_id in utility_map else 0
            bucket["total_bid"] += result.bids[bidder.bidder_id]

    summary: Dict[str, Dict[str, float]] = {}
    for bidder_type, payload in type_totals.items():
        count = max(payload["count"], 1)
        summary[bidder_type] = {
            "mean_payoff": round(payload["total_payoff"] / count, 4),
            "win_rate": round(payload["wins"] / count, 4),
            "mean_bid": round(payload["total_bid"] / count, 4),
        }
    return summary


def _aggregate_results(results: Dict[str, List[AuctionResult]]) -> Dict[str, object]:
    summary = {}
    for mechanism, items in results.items():
        summary[mechanism] = {
            "revenue": _mean_metric(items, "revenue"),
            "social_welfare": _mean_metric(items, "social_welfare"),
            "efficiency": _mean_metric(items, "efficiency"),
            "payoff_mean": _mean_metric(items, "payoff_mean"),
            "payoff_std": _mean_metric(items, "payoff_std"),
            "utility_gini": _mean_metric(items, "utility_gini"),
            "truthful_gap": _mean_metric(items, "truthful_gap"),
            "late_bid_rate": _mean_metric(items, "late_bid_rate"),
            "collusion_discount": _mean_metric(items, "collusion_discount"),
            "payoff_by_type": _payoff_by_type(items),
        }

    gsp_revenue = summary["GSP"]["revenue"]
    vcg_revenue = summary["VCG"]["revenue"]
    revenue_loss = gsp_revenue - vcg_revenue
    revenue_loss_pct = (revenue_loss / gsp_revenue * 100.0) if gsp_revenue else 0.0
    return {
        "summary": summary,
        "comparisons": {
            "vcg_minus_gsp_welfare": round(summary["VCG"]["social_welfare"] - summary["GSP"]["social_welfare"], 4),
            "vcg_minus_gsp_efficiency": round(summary["VCG"]["efficiency"] - summary["GSP"]["efficiency"], 4),
            "vcg_minus_gsp_payoff_std": round(summary["VCG"]["payoff_std"] - summary["GSP"]["payoff_std"], 4),
            "vcg_revenue_loss_vs_gsp": round(revenue_loss, 4),
            "vcg_revenue_loss_pct_vs_gsp": round(revenue_loss_pct, 2),
        },
        "samples": {
            mechanism: {
                "top_round_metrics": asdict(items[0].metrics),
                "top_round_allocations": [asdict(allocation) for allocation in items[0].allocations],
            }
            for mechanism, items in results.items()
        },
    }


def compare_mechanisms(
    scenario: str,
    sim_config: SimulationConfig,
    type_mix: Dict[str, float] | None = None,
    type_counts: Dict[str, int] | None = None,
    collusion_rate_override: float | None = None,
) -> Dict[str, object]:
    by_mechanism: Dict[str, List[AuctionResult]] = {"GSP": [], "VCG": []}
    for round_idx in range(sim_config.rounds):
        for mechanism in by_mechanism:
            by_mechanism[mechanism].append(
                run_single_scenario(
                    scenario=scenario,
                    mechanism=mechanism,
                    sim_config=sim_config,
                    seed_offset=round_idx * 17 + (0 if mechanism == "GSP" else 1),
                    type_mix=type_mix,
                    type_counts=type_counts,
                    collusion_rate_override=collusion_rate_override,
                )
            )
    aggregated = _aggregate_results(by_mechanism)
    return {
        "scenario": scenario,
        "rounds": sim_config.rounds,
        "num_bidders": sim_config.num_bidders,
        "num_slots": sim_config.num_slots,
        "value_range": {"min": sim_config.value_min, "max": sim_config.value_max},
        "bid_deadline_ms": sim_config.bid_deadline_ms,
        "latency_scale_ms": sim_config.latency_scale_ms,
        "type_mix": type_mix or BALANCED_TYPE_MIX,
        "type_counts": type_counts,
        "collusion_rate": sim_config.collusion_rate if collusion_rate_override is None else collusion_rate_override,
        **aggregated,
    }


def run_batch_experiments(sim_config: SimulationConfig) -> Dict[str, object]:
    truthful_reference = compare_mechanisms(
        scenario="heterogeneous",
        sim_config=sim_config,
        type_mix=TRUTHFUL_ONLY_TYPE_MIX,
    )
    baseline_reference = compare_mechanisms(
        scenario="heterogeneous",
        sim_config=sim_config,
        type_mix=BALANCED_TYPE_MIX,
    )
    heterogeneous_profiles = {
        name: compare_mechanisms(
            scenario="heterogeneous",
            sim_config=sim_config,
            type_mix=profile,
        )
        for name, profile in HETEROGENEOUS_MIXES.items()
    }
    collusion_rates = [rate / 10 for rate in range(1, 10)]
    collusion_sweep = [
        compare_mechanisms(
            scenario="collusion",
            sim_config=sim_config,
            type_mix=BALANCED_TYPE_MIX,
            collusion_rate_override=rate,
        )
        for rate in collusion_rates
    ]
    latency_case = compare_mechanisms(
        scenario="latency",
        sim_config=sim_config,
        type_mix=BALANCED_TYPE_MIX,
    )
    return {
        "heterogeneous": {
            "description": "Only type mix changes.",
            "truthful_reference": truthful_reference,
            "baseline_reference": baseline_reference,
            "profiles": heterogeneous_profiles,
        },
        "collusion": {
            "description": "Type mix is fixed at the balanced 1:1:1:1 market and only bidding-ring size changes.",
            "truthful_reference": truthful_reference,
            "baseline_reference": baseline_reference,
            "sweep": collusion_sweep,
        },
        "latency": {
            "description": "Type mix is fixed at the balanced 1:1:1:1 market and only late arrivals are added.",
            "truthful_reference": truthful_reference,
            "baseline_reference": baseline_reference,
            "latency_case": latency_case,
        },
    }


def _write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _get_matplotlib_pyplot():
    mpl_cache = Path(tempfile.gettempdir()) / "matplotlib"
    mpl_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_cache))
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "axes.edgecolor": "#2f2a24",
            "axes.labelcolor": "#2f2a24",
            "text.color": "#2f2a24",
            "xtick.color": "#2f2a24",
            "ytick.color": "#2f2a24",
        }
    )
    return plt


def _save_matplotlib_figure(fig, output_path: Path) -> None:
    stem = output_path.with_suffix("")
    fig.savefig(stem.with_suffix(".png"), dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt = _get_matplotlib_pyplot()
    plt.close(fig)


def _render_bar_chart_matplotlib(
    title: str,
    labels: List[str],
    values: List[float],
    output_path: Path,
    bar_fill_ratio: float = 0.55,
    headroom_ratio: float = 1.0,
    height_scale: float = 0.8,
    fig_width: float = 7.2,
    fig_height: float = 4.2,
    y_min: float | None = None,
    y_max: float | None = None,
) -> None:
    plt = _get_matplotlib_pyplot()
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    fig.patch.set_facecolor("#f7f1e5")
    ax.set_facecolor("#f7f1e5")
    colors = ["#c44536", "#3c6382", "#6a994e", "#d4a373", "#6d597a", "#e76f51"]
    xs = list(range(len(labels)))
    width = min(max(bar_fill_ratio, 0.15), 0.85)
    bars = ax.bar(xs, values, width=width, color=colors[: len(labels)])
    max_value = max(values) if values else 1.0
    if y_min is not None and y_max is not None:
        ylim_bottom, ylim_top = y_min, y_max
    else:
        ylim_bottom, ylim_top = 0.0, max(max_value, 1.0) * max(headroom_ratio, 1.0) / max(height_scale, 0.1)
    ax.set_ylim(ylim_bottom, ylim_top)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_title(title, fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_ticks([])
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (ylim_top - ylim_bottom) * 0.02, f"{value:.2f}", ha="center", va="bottom", fontsize=10)
    _save_matplotlib_figure(fig, output_path)


def _render_grouped_bar_chart_matplotlib(
    title: str,
    categories: List[str],
    series: Dict[str, List[float]],
    output_path: Path,
    inner_ratio: float = 0.72,
    bar_ratio: float = 0.9,
    headroom_ratio: float = 1.0,
    height_scale: float = 0.8,
    legend_down_shift_ratio: float = 0.0,
) -> None:
    plt = _get_matplotlib_pyplot()
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    fig.patch.set_facecolor("#f7f1e5")
    ax.set_facecolor("#f7f1e5")
    palette = ["#c44536", "#3c6382", "#6a994e", "#d4a373"]
    series_names = list(series.keys())
    x = list(range(len(categories)))
    group_width = min(max(inner_ratio, 0.2), 0.9)
    bar_width = group_width / max(len(series_names), 1) * min(max(bar_ratio, 0.2), 0.95)
    offset_base = -group_width / 2 + bar_width / 2
    all_values = [value for values in series.values() for value in values]
    max_value = max(all_values) if all_values else 1.0
    ylim_top = max(max_value, 1.0) * max(headroom_ratio, 1.0) / max(height_scale, 0.1)
    ax.set_ylim(0, ylim_top)
    for idx, name in enumerate(series_names):
        offsets = [xi + offset_base + idx * bar_width for xi in x]
        bars = ax.bar(offsets, series[name], width=bar_width * 0.92, color=palette[idx % len(palette)], label=name)
        for bar, value in zip(bars, series[name]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + ylim_top * 0.02, f"{value:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_title(title, fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_ticks([])
    anchor_y = 1.0 - max(legend_down_shift_ratio, 0.0) * 0.6
    ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, anchor_y))
    _save_matplotlib_figure(fig, output_path)


def _render_line_chart_matplotlib(
    title: str,
    labels: List[str],
    values: List[float],
    output_path: Path,
    vertical_scale: float = 0.8,
    first_tick_dx: float = 0.0,
    first_value_dx: float = 0.0,
    y_min: float | None = None,
    y_max: float | None = None,
) -> None:
    plt = _get_matplotlib_pyplot()
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    fig.patch.set_facecolor("#f7f1e5")
    ax.set_facecolor("#f7f1e5")
    xs = list(range(len(labels)))
    ax.plot(xs, values, color="#c44536", linewidth=2.5, marker="o", markerfacecolor="#3c6382", markeredgecolor="#3c6382")
    max_value = max(values) if values else 1.0
    if y_min is not None and y_max is not None:
        ylim_bottom, ylim_top = y_min, y_max
    else:
        ylim_bottom, ylim_top = 0.0, max(max_value, 1.0) / min(max(vertical_scale, 0.1), 1.5)
    ax.set_ylim(ylim_bottom, ylim_top)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_title(title, fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_ticks([])
    for idx, (x, value) in enumerate(zip(xs, values)):
        tick_dx = first_tick_dx / 20 if idx == 0 else 0.0
        value_dx = first_value_dx / 20 if idx == 0 else 0.0
        ax.text(x + value_dx, value + (ylim_top - ylim_bottom) * 0.03, f"{value:.2f}", ha="center", va="bottom", fontsize=9)
        if idx == 0 and tick_dx != 0.0:
            labels[idx] = labels[idx]
    if first_tick_dx != 0.0:
        tick_texts = ax.get_xticklabels()
        if tick_texts:
            tick_texts[0].set_x(xs[0] + first_tick_dx / 20)
    _save_matplotlib_figure(fig, output_path)


def _render_multi_line_chart_matplotlib(
    title: str,
    labels: List[str],
    series: Dict[str, List[float]],
    output_path: Path,
    headroom_ratio: float = 1.0,
    label_y_offsets: List[float] | None = None,
    label_x_offsets: List[float] | None = None,
    vertical_scale: float = 0.8,
    first_tick_dx: float = 0.0,
    first_value_dx_by_series: List[float] | None = None,
) -> None:
    plt = _get_matplotlib_pyplot()
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    fig.patch.set_facecolor("#f7f1e5")
    ax.set_facecolor("#f7f1e5")
    palette = ["#c44536", "#3c6382", "#6a994e", "#d4a373"]
    xs = list(range(len(labels)))
    all_values = [value for values in series.values() for value in values]
    max_value = max(all_values) if all_values else 1.0
    ylim_top = max(max_value, 1.0) * max(headroom_ratio, 1.0) / max(vertical_scale, 0.1)
    ax.set_ylim(0, ylim_top)
    for idx, (name, values) in enumerate(series.items()):
        color = palette[idx % len(palette)]
        ax.plot(xs, values, color=color, linewidth=2.5, marker="o", markerfacecolor=color, markeredgecolor=color, label=name)
        for j, (x, value) in enumerate(zip(xs, values)):
            dx = 0.0 if not label_x_offsets else label_x_offsets[idx % len(label_x_offsets)] / 20
            dy = 0.0 if not label_y_offsets else label_y_offsets[idx % len(label_y_offsets)] * (ylim_top / 200)
            if j == 0 and first_value_dx_by_series:
                dx += first_value_dx_by_series[idx % len(first_value_dx_by_series)] / 20
            # Keep the same semantics as SVG positioning:
            # positive y-offset means "move text downward on screen".
            pixel_adjust = 2 if idx == 0 else 1
            ax.text(x + dx, value + ylim_top * 0.02 - dy - pixel_adjust * (ylim_top / 200), f"{value:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=10)
    if first_tick_dx != 0.0:
        tick_texts = ax.get_xticklabels()
        if tick_texts:
            tick_texts[0].set_x(xs[0] + first_tick_dx / 20)
    ax.set_title(title, fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_ticks([])
    ax.legend(frameon=False, loc="upper right")
    _save_matplotlib_figure(fig, output_path)


def _svg_bar_chart(
    title: str,
    labels: List[str],
    values: List[float],
    output_path: Path,
    bar_fill_ratio: float = 0.55,
    headroom_ratio: float = 1.0,
    height_scale: float = 0.8,
    width: int = 720,
    height: int = 420,
    y_min: float | None = None,
    y_max: float | None = None,
) -> None:
    margin_left, margin_bottom, margin_top = 90, 70, 60
    chart_height = height - margin_top - margin_bottom
    chart_width = width - margin_left - 40
    max_value = max(values) if values else 1.0
    if y_min is not None and y_max is not None:
        min_value = y_min
        max_value = y_max
    else:
        min_value = 0.0
        max_value = max(max_value, 1.0) * max(headroom_ratio, 1.0)
    unit_width = chart_width / max(len(values), 1)
    bar_width = unit_width * min(max(bar_fill_ratio, 0.15), 0.85)
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<rect width='100%' height='100%' fill='#f7f1e5' />",
        f"<text x='{width/2}' y='32' font-size='22' text-anchor='middle' font-family='Times New Roman'>{title}</text>",
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' y2='{height-margin_bottom}' stroke='#2f2a24'/>",
        f"<line x1='{margin_left}' y1='{height-margin_bottom}' x2='{width-30}' y2='{height-margin_bottom}' stroke='#2f2a24'/>",
    ]
    colors = ["#c44536", "#3c6382", "#6a994e", "#d4a373", "#6d597a", "#e76f51"]
    for idx, (label, value) in enumerate(zip(labels, values)):
        x = margin_left + idx * unit_width + (unit_width - bar_width) / 2
        normalized = 0.0 if max_value == min_value else (value - min_value) / (max_value - min_value)
        bar_height = chart_height * normalized * max(height_scale, 0.1)
        y = height - margin_bottom - bar_height
        color = colors[idx % len(colors)]
        parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_width:.1f}' height='{bar_height:.1f}' fill='{color}' rx='6' />")
        parts.append(f"<text x='{x + bar_width/2:.1f}' y='{height - margin_bottom + 25}' font-size='14' text-anchor='middle' font-family='Times New Roman'>{label}</text>")
        parts.append(f"<text x='{x + bar_width/2:.1f}' y='{max(54, y - 8):.1f}' font-size='13' text-anchor='middle' font-family='Times New Roman'>{value:.2f}</text>")
    parts.append("</svg>")
    output_path.write_text("".join(parts), encoding="utf-8")
    _render_bar_chart_matplotlib(
        title=title,
        labels=labels,
        values=values,
        output_path=output_path,
        bar_fill_ratio=bar_fill_ratio,
        headroom_ratio=headroom_ratio,
        height_scale=height_scale,
        fig_width=width / 100,
        fig_height=height / 100,
        y_min=y_min,
        y_max=y_max,
    )


def _svg_grouped_bar_chart(
    title: str,
    categories: List[str],
    series: Dict[str, List[float]],
    output_path: Path,
    inner_ratio: float = 0.72,
    bar_ratio: float = 0.9,
    headroom_ratio: float = 1.0,
    legend_y: int = 44,
    height_scale: float = 0.8,
    legend_down_shift_ratio: float = 0.0,
) -> None:
    width, height = 920, 460
    margin_left, margin_bottom, margin_top = 90, 85, 60
    chart_height = height - margin_top - margin_bottom
    chart_width = width - margin_left - 40
    all_values = [value for values in series.values() for value in values]
    max_value = max(all_values) if all_values else 1.0
    max_value = max(max_value, 1.0) * max(headroom_ratio, 1.0)
    group_width = chart_width / max(len(categories), 1)
    inner_width = group_width * min(max(inner_ratio, 0.2), 0.9)
    series_names = list(series.keys())
    bar_width = inner_width / max(len(series_names), 1)
    palette = ["#c44536", "#3c6382", "#6a994e", "#d4a373"]
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<rect width='100%' height='100%' fill='#f7f1e5' />",
        f"<text x='{width/2}' y='32' font-size='22' text-anchor='middle' font-family='Times New Roman'>{title}</text>",
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' y2='{height-margin_bottom}' stroke='#2f2a24'/>",
        f"<line x1='{margin_left}' y1='{height-margin_bottom}' x2='{width-30}' y2='{height-margin_bottom}' stroke='#2f2a24'/>",
    ]
    for category_idx, category in enumerate(categories):
        group_x = margin_left + category_idx * group_width + group_width * 0.14
        for series_idx, series_name in enumerate(series_names):
            values = series[series_name]
            value = values[category_idx]
            slot_x = group_x + series_idx * bar_width
            bar_height = 0 if max_value == 0 else chart_height * (value / max_value) * min(max(height_scale, 0.1), 1.0)
            y = height - margin_bottom - bar_height
            color = palette[series_idx % len(palette)]
            actual_width = bar_width * min(max(bar_ratio, 0.2), 0.95)
            x = slot_x + (bar_width - actual_width) / 2
            parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{actual_width:.1f}' height='{bar_height:.1f}' fill='{color}' rx='5' />")
            parts.append(f"<text x='{x + actual_width/2:.1f}' y='{max(54, y - 8):.1f}' font-size='11' text-anchor='middle' font-family='Times New Roman'>{value:.2f}</text>")
        parts.append(
            f"<text x='{group_x + inner_width/2:.1f}' y='{height - margin_bottom + 28}' font-size='12' text-anchor='middle' font-family='Times New Roman'>{category}</text>"
        )
    legend_x = width - 230
    legend_y_adjusted = legend_y + width * max(legend_down_shift_ratio, 0.0)
    for idx, series_name in enumerate(series_names):
        y = legend_y_adjusted + idx * 20
        color = palette[idx % len(palette)]
        parts.append(f"<rect x='{legend_x}' y='{y - 10}' width='14' height='14' fill='{color}' rx='3' />")
        parts.append(f"<text x='{legend_x + 22}' y='{y + 1}' font-size='13' font-family='Times New Roman'>{series_name}</text>")
    parts.append("</svg>")
    output_path.write_text("".join(parts), encoding="utf-8")
    _render_grouped_bar_chart_matplotlib(
        title=title,
        categories=categories,
        series=series,
        output_path=output_path,
        inner_ratio=inner_ratio,
        bar_ratio=bar_ratio,
        headroom_ratio=headroom_ratio,
        height_scale=height_scale,
        legend_down_shift_ratio=legend_down_shift_ratio,
    )


def _svg_line_chart(
    title: str,
    labels: List[str],
    values: List[float],
    output_path: Path,
    vertical_scale: float = 0.8,
    first_tick_dx: float = 0.0,
    first_value_dx: float = 0.0,
    y_min: float | None = None,
    y_max: float | None = None,
) -> None:
    width, height = 760, 420
    margin_left, margin_bottom, margin_top = 80, 70, 60
    chart_height = height - margin_top - margin_bottom
    chart_width = width - margin_left - 40
    max_value = max(values) if values else 1.0
    if y_min is not None and y_max is not None:
        min_value = y_min
        max_value = y_max
    else:
        min_value = 0.0
        max_value = max(max_value, 1.0)
    xs: List[float] = []
    ys: List[float] = []
    for idx, value in enumerate(values):
        x = margin_left + (chart_width * idx / max(len(values) - 1, 1))
        normalized = 0.0 if max_value == min_value else (value - min_value) / (max_value - min_value)
        y = height - margin_bottom - chart_height * normalized * min(max(vertical_scale, 0.1), 1.5)
        xs.append(x)
        ys.append(y)
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<rect width='100%' height='100%' fill='#f7f1e5' />",
        f"<text x='{width/2}' y='32' font-size='22' text-anchor='middle' font-family='Times New Roman'>{title}</text>",
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' y2='{height-margin_bottom}' stroke='#2f2a24'/>",
        f"<line x1='{margin_left}' y1='{height-margin_bottom}' x2='{width-30}' y2='{height-margin_bottom}' stroke='#2f2a24'/>",
        f"<polyline points='{polyline}' fill='none' stroke='#c44536' stroke-width='3' />",
    ]
    for idx, (label, value, x, y) in enumerate(zip(labels, values, xs, ys)):
        tick_dx = first_tick_dx if idx == 0 else 0.0
        value_dx = first_value_dx if idx == 0 else 0.0
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='5' fill='#3c6382' />")
        parts.append(f"<text x='{x + tick_dx:.1f}' y='{height - margin_bottom + 22}' font-size='13' text-anchor='middle' font-family='Times New Roman'>{label}</text>")
        parts.append(f"<text x='{x + value_dx:.1f}' y='{max(52, y - 10):.1f}' font-size='12' text-anchor='middle' font-family='Times New Roman'>{value:.2f}</text>")
    parts.append("</svg>")
    output_path.write_text("".join(parts), encoding="utf-8")
    _render_line_chart_matplotlib(
        title=title,
        labels=labels.copy(),
        values=values,
        output_path=output_path,
        vertical_scale=vertical_scale,
        first_tick_dx=first_tick_dx,
        first_value_dx=first_value_dx,
        y_min=y_min,
        y_max=y_max,
    )


def _svg_multi_line_chart(
    title: str,
    labels: List[str],
    series: Dict[str, List[float]],
    output_path: Path,
    headroom_ratio: float = 1.0,
    legend_x: int | None = None,
    legend_y: int = 48,
    label_y_offsets: List[float] | None = None,
    label_x_offsets: List[float] | None = None,
    vertical_scale: float = 0.8,
    first_tick_dx: float = 0.0,
    first_value_dx_by_series: List[float] | None = None,
) -> None:
    width, height = 820, 440
    margin_left, margin_bottom, margin_top = 80, 75, 60
    chart_height = height - margin_top - margin_bottom
    chart_width = width - margin_left - 40
    all_values = [value for values in series.values() for value in values]
    max_value = max(all_values) if all_values else 1.0
    max_value = max(max_value, 1.0) * max(headroom_ratio, 1.0)
    palette = ["#c44536", "#3c6382", "#6a994e", "#d4a373"]
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<rect width='100%' height='100%' fill='#f7f1e5' />",
        f"<text x='{width/2}' y='32' font-size='22' text-anchor='middle' font-family='Times New Roman'>{title}</text>",
        f"<line x1='{margin_left}' y1='{margin_top}' x2='{margin_left}' y2='{height-margin_bottom}' stroke='#2f2a24'/>",
        f"<line x1='{margin_left}' y1='{height-margin_bottom}' x2='{width-30}' y2='{height-margin_bottom}' stroke='#2f2a24'/>",
    ]
    legend_x = width - 220 if legend_x is None else legend_x
    for series_idx, (series_name, values) in enumerate(series.items()):
        xs: List[float] = []
        ys: List[float] = []
        for idx, value in enumerate(values):
            x = margin_left + (chart_width * idx / max(len(values) - 1, 1))
            y = height - margin_bottom - chart_height * (value / max_value) * min(max(vertical_scale, 0.1), 1.0)
            xs.append(x)
            ys.append(y)
        color = palette[series_idx % len(palette)]
        polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        parts.append(f"<polyline points='{polyline}' fill='none' stroke='{color}' stroke-width='3' />")
        for label, value, x, y in zip(labels, values, xs, ys):
            label_dx = 0.0 if not label_x_offsets else label_x_offsets[series_idx % len(label_x_offsets)]
            label_dy = -10.0 if not label_y_offsets else label_y_offsets[series_idx % len(label_y_offsets)]
            if label == labels[0] and first_value_dx_by_series:
                label_dx += first_value_dx_by_series[series_idx % len(first_value_dx_by_series)]
            parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4.5' fill='{color}' />")
            parts.append(
                f"<text x='{x + label_dx:.1f}' y='{max(52, y + label_dy):.1f}' font-size='11' text-anchor='middle' font-family='Times New Roman'>{value:.2f}</text>"
            )
            if series_idx == 0:
                tick_dx = first_tick_dx if label == labels[0] else 0.0
                parts.append(f"<text x='{x + tick_dx:.1f}' y='{height - margin_bottom + 24}' font-size='12' text-anchor='middle' font-family='Times New Roman'>{label}</text>")
    for idx, series_name in enumerate(series.keys()):
        y = legend_y + idx * 20
        color = palette[idx % len(palette)]
        parts.append(f"<line x1='{legend_x}' y1='{y - 4}' x2='{legend_x + 14}' y2='{y - 4}' stroke='{color}' stroke-width='3' />")
        parts.append(f"<text x='{legend_x + 22}' y='{y}' font-size='13' font-family='Times New Roman'>{series_name}</text>")
    parts.append("</svg>")
    output_path.write_text("".join(parts), encoding="utf-8")
    _render_multi_line_chart_matplotlib(
        title=title,
        labels=labels.copy(),
        series=series,
        output_path=output_path,
        headroom_ratio=headroom_ratio,
        label_y_offsets=label_y_offsets,
        label_x_offsets=label_x_offsets,
        vertical_scale=vertical_scale,
        first_tick_dx=first_tick_dx,
        first_value_dx_by_series=first_value_dx_by_series,
    )


def export_results(bundle: Dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_name in [
        "heterogeneous_gsp_revenue.svg",
        "heterogeneous_vcg_revenue.svg",
        "collusion_gsp_revenue_trend.svg",
        "collusion_vcg_revenue_trend.svg",
        "latency_welfare_comparison.svg",
    ]:
        stale_path = output_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()
    flat_rows: List[Dict[str, object]] = []
    heterogeneous_payoff_rows: List[Dict[str, object]] = []
    heterogeneous = bundle["heterogeneous"]["profiles"]
    heterogeneous_baseline = bundle["heterogeneous"]["baseline_reference"]
    truthful_reference = bundle["heterogeneous"]["truthful_reference"]
    for ref_name, ref_payload in [("all_truthful", truthful_reference), ("balanced_market", heterogeneous_baseline)]:
        for mechanism, metrics in ref_payload["summary"].items():
            flat_rows.append(
                {
                    "experiment_group": "heterogeneous_reference",
                    "profile": ref_name,
                    "mechanism": mechanism,
                    **{key: value for key, value in metrics.items() if key != "payoff_by_type"},
                }
            )
    for mechanism, metrics in truthful_reference["summary"].items():
        truthful_payoff = metrics["payoff_by_type"].get("truthful", {}).get("mean_payoff", 0.0)
        heterogeneous_payoff_rows.append(
            {
                "setting": "all_truthful",
                "mechanism": mechanism,
                "truthful": truthful_payoff,
                "shaded": "-",
                "budget": "-",
                "aggressive": "-",
            }
            )
    for mechanism, metrics in heterogeneous_baseline["summary"].items():
        heterogeneous_payoff_rows.append(
            {
                "setting": "balanced_market",
                "mechanism": mechanism,
                "truthful": metrics["payoff_by_type"].get("truthful", {}).get("mean_payoff", 0.0),
                "shaded": metrics["payoff_by_type"].get("shaded", {}).get("mean_payoff", 0.0),
                "budget": metrics["payoff_by_type"].get("budget", {}).get("mean_payoff", 0.0),
                "aggressive": metrics["payoff_by_type"].get("aggressive", {}).get("mean_payoff", 0.0),
            }
        )
    for profile_name, payload in heterogeneous.items():
        for mechanism, metrics in payload["summary"].items():
            row = {"experiment_group": "heterogeneous", "profile": profile_name, "mechanism": mechanism}
            row.update({key: value for key, value in metrics.items() if key != "payoff_by_type"})
            flat_rows.append(row)
            for bidder_type, payoff_stats in metrics["payoff_by_type"].items():
                flat_rows.append(
                    {
                        "experiment_group": "heterogeneous_payoff",
                        "profile": profile_name,
                        "mechanism": mechanism,
                        "bidder_type": bidder_type,
                        **payoff_stats,
                    }
                )
            heterogeneous_payoff_rows.append(
                {
                    "setting": profile_name,
                    "mechanism": mechanism,
                    "truthful": metrics["payoff_by_type"].get("truthful", {}).get("mean_payoff", 0.0),
                    "shaded": metrics["payoff_by_type"].get("shaded", {}).get("mean_payoff", 0.0),
                    "budget": metrics["payoff_by_type"].get("budget", {}).get("mean_payoff", 0.0),
                    "aggressive": metrics["payoff_by_type"].get("aggressive", {}).get("mean_payoff", 0.0),
                }
            )

    hetero_categories = ["all-truthful", "balanced", "truthful-heavy", "shaded-heavy", "budget-heavy", "aggressive-heavy"]
    heavy_order = ["truthful_heavy", "shaded_heavy", "budget_heavy", "aggressive_heavy"]
    _svg_grouped_bar_chart(
        title="Seller Revenue: Baseline vs Heterogeneous Type Mixes (GSP and VCG)",
        categories=hetero_categories,
        series={
            "GSP": [
                truthful_reference["summary"]["GSP"]["revenue"],
                heterogeneous_baseline["summary"]["GSP"]["revenue"],
            ]
            + [heterogeneous[label]["summary"]["GSP"]["revenue"] for label in heavy_order],
            "VCG": [
                truthful_reference["summary"]["VCG"]["revenue"],
                heterogeneous_baseline["summary"]["VCG"]["revenue"],
            ]
            + [heterogeneous[label]["summary"]["VCG"]["revenue"] for label in heavy_order],
        },
        output_path=output_dir / "heterogeneous_revenue.svg",
        legend_down_shift_ratio=0.02,
    )
    _svg_grouped_bar_chart(
        title="Social Welfare: Baseline vs Heterogeneous Type Mixes (GSP and VCG)",
        categories=hetero_categories,
        series={
            "GSP": [
                truthful_reference["summary"]["GSP"]["social_welfare"],
                heterogeneous_baseline["summary"]["GSP"]["social_welfare"],
            ]
            + [heterogeneous[label]["summary"]["GSP"]["social_welfare"] for label in heavy_order],
            "VCG": [
                truthful_reference["summary"]["VCG"]["social_welfare"],
                heterogeneous_baseline["summary"]["VCG"]["social_welfare"],
            ]
            + [heterogeneous[label]["summary"]["VCG"]["social_welfare"] for label in heavy_order],
        },
        output_path=output_dir / "heterogeneous_welfare.svg",
        height_scale=0.8,
        legend_down_shift_ratio=0.02,
    )

    collusion_entries = bundle["collusion"]["sweep"]
    collusion_baseline = bundle["collusion"]["baseline_reference"]
    for mechanism, metrics in collusion_baseline["summary"].items():
        row = {"experiment_group": "collusion", "profile": "0pct", "mechanism": mechanism}
        row.update({key: value for key, value in metrics.items() if key != "payoff_by_type"})
        if mechanism == "VCG":
            row["vcg_revenue_loss_vs_gsp"] = collusion_baseline["summary"]["GSP"]["revenue"] - collusion_baseline["summary"]["VCG"]["revenue"]
            row["vcg_revenue_loss_pct_vs_gsp"] = (
                (collusion_baseline["summary"]["GSP"]["revenue"] - collusion_baseline["summary"]["VCG"]["revenue"])
                / collusion_baseline["summary"]["GSP"]["revenue"]
                * 100.0
            )
        flat_rows.append(row)
    for payload in collusion_entries:
        rate_label = int(payload["collusion_rate"] * 100)
        for mechanism, metrics in payload["summary"].items():
            row = {"experiment_group": "collusion", "profile": f"{rate_label}pct", "mechanism": mechanism}
            row.update({key: value for key, value in metrics.items() if key != "payoff_by_type"})
            if mechanism == "VCG":
                row["vcg_revenue_loss_vs_gsp"] = payload["comparisons"]["vcg_revenue_loss_vs_gsp"]
                row["vcg_revenue_loss_pct_vs_gsp"] = payload["comparisons"]["vcg_revenue_loss_pct_vs_gsp"]
            flat_rows.append(row)

    collusion_labels = ["0%"] + [f"{int(item['collusion_rate'] * 100)}%" for item in collusion_entries]
    _svg_multi_line_chart(
        title="Seller Revenue: Baseline vs Increasing Collusion (GSP and VCG)",
        labels=collusion_labels,
        series={
            "GSP": [collusion_baseline["summary"]["GSP"]["revenue"]]
            + [item["summary"]["GSP"]["revenue"] for item in collusion_entries],
            "VCG": [collusion_baseline["summary"]["VCG"]["revenue"]]
            + [item["summary"]["VCG"]["revenue"] for item in collusion_entries],
        },
        output_path=output_dir / "collusion_revenue.svg",
    )
    _svg_multi_line_chart(
        title="Social Welfare: Baseline vs Increasing Collusion (GSP and VCG)",
        labels=collusion_labels,
        series={
            "GSP": [collusion_baseline["summary"]["GSP"]["social_welfare"]]
            + [item["summary"]["GSP"]["social_welfare"] for item in collusion_entries],
            "VCG": [collusion_baseline["summary"]["VCG"]["social_welfare"]]
            + [item["summary"]["VCG"]["social_welfare"] for item in collusion_entries],
        },
        output_path=output_dir / "collusion_welfare.svg",
        headroom_ratio=1.08,
        legend_y=76,
        label_y_offsets=[-4, 16],
    )
    _svg_line_chart(
        title="Revenue Loss of VCG Relative to GSP Under Increasing Collusion (%)",
        labels=["0%"] + [f"{int(item['collusion_rate'] * 100)}%" for item in collusion_entries],
        values=[
            round(
                (collusion_baseline["summary"]["GSP"]["revenue"] - collusion_baseline["summary"]["VCG"]["revenue"])
                / collusion_baseline["summary"]["GSP"]["revenue"]
                * 100.0,
                2,
            )
        ]
        + [item["comparisons"]["vcg_revenue_loss_pct_vs_gsp"] for item in collusion_entries],
        output_path=output_dir / "collusion_vcg_revenue_loss_trend.svg",
        y_min=40.0,
        y_max=70.0,
    )

    latency_base = bundle["latency"]["baseline_reference"]
    latency_case = bundle["latency"]["latency_case"]
    for label, payload in [("baseline", latency_base), ("latency", latency_case)]:
        for mechanism, metrics in payload["summary"].items():
            row = {"experiment_group": "latency", "profile": label, "mechanism": mechanism}
            row.update({key: value for key, value in metrics.items() if key != "payoff_by_type"})
            flat_rows.append(row)

    _svg_bar_chart(
        title="Late Bid Rate: Baseline vs Network Latency",
        labels=["Baseline GSP", "Latency GSP", "Baseline VCG", "Latency VCG"],
        values=[
            latency_base["summary"]["GSP"]["late_bid_rate"],
            latency_case["summary"]["GSP"]["late_bid_rate"],
            latency_base["summary"]["VCG"]["late_bid_rate"],
            latency_case["summary"]["VCG"]["late_bid_rate"],
        ],
        output_path=output_dir / "latency_late_bid_rate.svg",
        bar_fill_ratio=0.275,
        height=210,
        y_min=0.0,
        y_max=0.3,
    )
    _svg_grouped_bar_chart(
        title="Seller Revenue: Baseline vs Network Latency (GSP and VCG)",
        categories=["baseline", "latency"],
        series={
            "GSP": [latency_base["summary"]["GSP"]["revenue"], latency_case["summary"]["GSP"]["revenue"]],
            "VCG": [latency_base["summary"]["VCG"]["revenue"], latency_case["summary"]["VCG"]["revenue"]],
        },
        output_path=output_dir / "latency_revenue.svg",
        inner_ratio=0.52,
        bar_ratio=0.72,
        headroom_ratio=1.14,
        legend_down_shift_ratio=0.02,
    )
    _svg_grouped_bar_chart(
        title="Social Welfare: Baseline vs Network Latency (GSP and VCG)",
        categories=["baseline", "latency"],
        series={
            "GSP": [latency_base["summary"]["GSP"]["social_welfare"], latency_case["summary"]["GSP"]["social_welfare"]],
            "VCG": [latency_base["summary"]["VCG"]["social_welfare"], latency_case["summary"]["VCG"]["social_welfare"]],
        },
        output_path=output_dir / "latency_welfare.svg",
        inner_ratio=0.52,
        bar_ratio=0.72,
        headroom_ratio=1.14,
        legend_down_shift_ratio=0.02,
    )
    _svg_grouped_bar_chart(
        title="Allocation Efficiency: Baseline vs Network Latency (GSP and VCG)",
        categories=["baseline", "latency"],
        series={
            "GSP": [latency_base["summary"]["GSP"]["efficiency"], latency_case["summary"]["GSP"]["efficiency"]],
            "VCG": [latency_base["summary"]["VCG"]["efficiency"], latency_case["summary"]["VCG"]["efficiency"]],
        },
        output_path=output_dir / "latency_efficiency.svg",
        inner_ratio=0.52,
        bar_ratio=0.72,
        headroom_ratio=1.14,
        legend_down_shift_ratio=0.02,
    )

    collusion = collusion_entries[1]
    _svg_bar_chart(
        title="Revenue Loss of VCG Relative to GSP Under Collusion",
        labels=["Absolute Loss", "Loss Percentage"],
        values=[
            collusion["comparisons"]["vcg_revenue_loss_vs_gsp"],
            collusion["comparisons"]["vcg_revenue_loss_pct_vs_gsp"],
        ],
        output_path=output_dir / "collusion_vcg_revenue_loss.svg",
        bar_fill_ratio=0.34,
        headroom_ratio=1.18,
    )
    _write_csv(output_dir / "experiment_summary.csv", flat_rows)
    _write_csv(output_dir / "heterogeneous_payoff_table.csv", heterogeneous_payoff_rows)
    (output_dir / "experiment_summary.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
