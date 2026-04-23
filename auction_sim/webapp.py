from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .core import SimulationConfig
from .simulation import compare_mechanisms, run_single_scenario

LOGO_PATH = Path(__file__).with_name("cuhklogo.svg")

HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>IERG3280 Auction Simulator</title>
  <style>
    :root {
      --paper: #f7f1e5;
      --ink: #2f2a24;
      --accent: #c44536;
      --accent-2: #3c6382;
      --card: #fffaf0;
      --line: #d9c7a5;
    }
    body {
      margin: 0;
      font-family: "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(196, 69, 54, 0.16), transparent 30%),
        radial-gradient(circle at top right, rgba(60, 99, 130, 0.16), transparent 30%),
        linear-gradient(180deg, #fcf8f0 0%, var(--paper) 100%);
      color: var(--ink);
    }
    .masthead {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 2;
      display: flex;
      align-items: center;
      gap: 18px;
      min-height: 120px;
      padding: 10px 24px;
      box-sizing: border-box;
      background: linear-gradient(180deg, rgba(252, 248, 240, 0.96) 0%, rgba(252, 248, 240, 0.88) 75%, rgba(252, 248, 240, 0.0) 100%);
      transform: translateY(-60px);
    }
    .logo-wrap {
      width: 340px;
      display: flex;
      align-items: center;
      justify-content: flex-start;
      flex: 0 0 auto;
    }
    .logo-wrap img {
      width: 300px;
      height: auto;
      display: block;
    }
    .course-copy {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .course-code {
      font-size: 1.45rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent-2);
    }
    .course-title {
      font-size: 1.45rem;
      line-height: 1.2;
      max-width: 760px;
    }
    main {
      max-width: 980px;
      margin: 0 auto;
      padding: 150px 20px 48px;
    }
    h1 { font-size: 2.2rem; margin-bottom: 0.2rem; margin-top: 0; }
    .lead { max-width: 760px; line-height: 1.5; }
    .panel {
      background: rgba(255, 250, 240, 0.88);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      margin-top: 20px;
      box-shadow: 0 12px 35px rgba(47, 42, 36, 0.08);
    }
    .controls {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      align-items: end;
    }
    .subpanel {
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid var(--line);
    }
    .subpanel[hidden] { display: none; }
    h2 {
      font-size: 1.1rem;
      margin: 0 0 12px;
    }
    label { display: block; font-size: 0.95rem; margin-bottom: 6px; }
    select, input, button {
      width: 100%;
      border-radius: 10px;
      border: 1px solid #bda57f;
      padding: 10px 12px;
      font-family: inherit;
      font-size: 1rem;
      box-sizing: border-box;
    }
    button {
      background: linear-gradient(135deg, var(--accent), #dd6b4d);
      color: white;
      font-weight: bold;
      cursor: pointer;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }
    .metric {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
    }
    .metric strong {
      display: block;
      font-size: 1.6rem;
      color: var(--accent-2);
      margin-top: 6px;
    }
    pre {
      overflow: auto;
      white-space: pre-wrap;
      background: #fdfbf7;
      border-radius: 14px;
      padding: 14px;
      border: 1px solid var(--line);
    }
    .hint {
      margin-top: 10px;
      color: #6d5b45;
      font-size: 0.92rem;
    }
    .error {
      margin-top: 14px;
      padding: 12px 14px;
      border-radius: 12px;
      background: rgba(196, 69, 54, 0.09);
      border: 1px solid rgba(196, 69, 54, 0.28);
      color: #8c2f24;
      display: none;
    }
    @media (max-width: 720px) {
      .masthead {
        position: static;
        align-items: flex-start;
        flex-direction: column;
        gap: 10px;
        min-height: auto;
        padding: 18px 18px 8px;
      }
      .logo-wrap {
        width: auto;
      }
      .logo-wrap img {
        width: 200px;
      }
      .course-title {
        font-size: 1.2rem;
      }
      .course-code {
        font-size: 1.2rem;
      }
      main {
        padding-top: 20px;
      }
    }
  </style>
</head>
<body>
<header class="masthead">
  <div class="logo-wrap">
    <img src="/assets/cuhklogo.svg" alt="The Chinese University of Hong Kong logo" />
  </div>
  <div class="course-copy">
    <div class="course-code">IERG 3280</div>
    <div class="course-title">Networks: Technology, Economics, and Social Interactions</div>
  </div>
</header>
<main>
  <h1>GSP vs VCG Auction Simulator</h1>
  <p class="lead">This lightweight interface lets you inspect single-run outcomes and scenario-level summaries for heterogeneous bidders, collusion, and network latency. You can also adjust market size and a bounded value range.</p>

  <section class="panel">
    <div class="controls">
      <div>
        <label for="scenario">Scenario</label>
        <select id="scenario">
          <option value="heterogeneous">heterogeneous</option>
          <option value="collusion">collusion</option>
          <option value="latency">latency</option>
        </select>
      </div>
      <div>
        <label for="mechanism">Mechanism</label>
        <select id="mechanism">
          <option value="GSP">GSP</option>
          <option value="VCG">VCG</option>
        </select>
      </div>
      <div>
        <label for="rounds">Rounds for summary</label>
        <input id="rounds" type="number" value="120" min="20" max="1000" />
      </div>
      <div>
        <label for="num_bidders">Users</label>
        <input id="num_bidders" type="number" value="12" min="4" max="40" />
      </div>
      <div>
        <label for="num_slots">Slots</label>
        <input id="num_slots" type="number" value="4" min="1" max="8" />
      </div>
      <div>
        <label for="value_min">Value Min</label>
        <input id="value_min" type="number" value="0.35" min="0.10" max="5.00" step="0.05" />
      </div>
      <div>
        <label for="value_max">Value Max</label>
        <input id="value_max" type="number" value="3.20" min="0.20" max="6.00" step="0.05" />
      </div>
      <div>
        <button id="simulate">Run Simulation</button>
      </div>
    </div>

    <div id="heterogeneous-controls" class="subpanel">
      <h2>Bidder-Type Counts</h2>
      <div class="controls">
        <div>
          <label for="truthful_count">Truthful</label>
          <input id="truthful_count" type="number" value="3" min="0" max="40" />
        </div>
        <div>
          <label for="shaded_count">Shaded</label>
          <input id="shaded_count" type="number" value="3" min="0" max="40" />
        </div>
        <div>
          <label for="budget_count">Budget</label>
          <input id="budget_count" type="number" value="3" min="0" max="40" />
        </div>
        <div>
          <label for="aggressive_count">Aggressive</label>
          <input id="aggressive_count" type="number" value="3" min="0" max="40" />
        </div>
      </div>
      <p class="hint">The four bidder-type counts should sum to the total number of users.</p>
    </div>

    <div id="collusion-controls" class="subpanel" hidden>
      <h2>Collusion Settings</h2>
      <div class="controls">
        <div>
          <label for="collusion_count">Collusive Users</label>
          <input id="collusion_count" type="number" value="3" min="2" max="12" />
        </div>
      </div>
      <p class="hint">The collusion setting uses the balanced bidder mix and converts this count into a collusion ratio internally.</p>
    </div>

    <div id="latency-controls" class="subpanel" hidden>
      <h2>Latency Settings</h2>
      <div class="controls">
        <div>
          <label for="latency_scale_ms">Base Latency (ms)</label>
          <input id="latency_scale_ms" type="number" value="55" min="10" max="150" />
        </div>
        <div>
          <label for="bid_deadline_ms">Bid Deadline (ms)</label>
          <input id="bid_deadline_ms" type="number" value="120" min="40" max="250" />
        </div>
      </div>
      <p class="hint">Latency still follows the built-in type-specific stress model, but you can adjust the base delay and deadline within preset bounds.</p>
    </div>

    <div id="error" class="error"></div>
    <div id="summary" class="summary"></div>
    <pre id="details">Choose a scenario and click "Run Simulation".</pre>
  </section>
</main>
<script>
  const summary = document.getElementById("summary");
  const details = document.getElementById("details");
  const errorBox = document.getElementById("error");

  function showError(message) {
    errorBox.style.display = "block";
    errorBox.textContent = message;
  }

  function clearError() {
    errorBox.style.display = "none";
    errorBox.textContent = "";
  }

  function syncScenarioPanels() {
    const scenario = document.getElementById("scenario").value;
    document.getElementById("heterogeneous-controls").hidden = scenario !== "heterogeneous";
    document.getElementById("collusion-controls").hidden = scenario !== "collusion";
    document.getElementById("latency-controls").hidden = scenario !== "latency";
  }

  function buildParams() {
    const scenario = document.getElementById("scenario").value;
    const numBidders = Number(document.getElementById("num_bidders").value);
    const params = new URLSearchParams({
      scenario,
      mechanism: document.getElementById("mechanism").value,
      rounds: document.getElementById("rounds").value,
      num_bidders: String(numBidders),
      num_slots: document.getElementById("num_slots").value,
      value_min: document.getElementById("value_min").value,
      value_max: document.getElementById("value_max").value,
      latency_scale_ms: document.getElementById("latency_scale_ms").value,
      bid_deadline_ms: document.getElementById("bid_deadline_ms").value,
    });

    if (scenario === "heterogeneous") {
      const counts = {
        truthful: Number(document.getElementById("truthful_count").value),
        shaded: Number(document.getElementById("shaded_count").value),
        budget: Number(document.getElementById("budget_count").value),
        aggressive: Number(document.getElementById("aggressive_count").value),
      };
      const totalAssigned = counts.truthful + counts.shaded + counts.budget + counts.aggressive;
      if (totalAssigned !== numBidders) {
        throw new Error(`Bidder-type counts must sum to ${numBidders}. Current total: ${totalAssigned}.`);
      }
      params.set("truthful_count", String(counts.truthful));
      params.set("shaded_count", String(counts.shaded));
      params.set("budget_count", String(counts.budget));
      params.set("aggressive_count", String(counts.aggressive));
    }

    if (scenario === "collusion") {
      params.set("collusion_count", document.getElementById("collusion_count").value);
    }

    return params;
  }

  document.getElementById("scenario").addEventListener("change", syncScenarioPanels);
  document.getElementById("num_bidders").addEventListener("change", () => {
    document.getElementById("collusion_count").max = document.getElementById("num_bidders").value;
  });
  syncScenarioPanels();

  document.getElementById("simulate").addEventListener("click", async () => {
    clearError();
    summary.innerHTML = "";
    details.textContent = "Running simulation...";
    try {
      const params = buildParams();
      const singleRes = await fetch(`/api/single?${params.toString()}`);
      const single = await singleRes.json();
      if (!singleRes.ok) {
        throw new Error(single.error || "Single-run request failed.");
      }
      const compareParams = new URLSearchParams(params);
      compareParams.delete("mechanism");
      const compareRes = await fetch(`/api/compare?${compareParams.toString()}`);
      const compare = await compareRes.json();
      if (!compareRes.ok) {
        throw new Error(compare.error || "Comparison request failed.");
      }
      const metrics = single.metrics;
      summary.innerHTML = `
        <div class="metric"><span>Revenue</span><strong>${metrics.revenue.toFixed(3)}</strong></div>
        <div class="metric"><span>Welfare</span><strong>${metrics.social_welfare.toFixed(3)}</strong></div>
        <div class="metric"><span>Efficiency</span><strong>${metrics.efficiency.toFixed(3)}</strong></div>
        <div class="metric"><span>Late Bid Rate</span><strong>${metrics.late_bid_rate.toFixed(3)}</strong></div>
        <div class="metric"><span>Truthful Gap</span><strong>${metrics.truthful_gap.toFixed(3)}</strong></div>
        <div class="metric"><span>Winners</span><strong>${metrics.winner_count}</strong></div>
        <div class="metric"><span>VCG Revenue Loss %</span><strong>${compare.comparisons.vcg_revenue_loss_pct_vs_gsp.toFixed(2)}</strong></div>
      `;
      details.textContent = JSON.stringify({ single_run: single, scenario_summary: compare }, null, 2);
    } catch (error) {
      showError(error.message);
      details.textContent = "Fix the input settings and try again.";
    }
  });
</script>
</body>
</html>
"""


class AuctionHandler(BaseHTTPRequestHandler):
    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _parse_int(params: dict[str, list[str]], key: str, default: int, minimum: int, maximum: int) -> int:
        raw = params.get(key, [str(default)])[0]
        value = int(raw)
        return max(minimum, min(maximum, value))

    @staticmethod
    def _parse_float(params: dict[str, list[str]], key: str, default: float, minimum: float, maximum: float) -> float:
        raw = params.get(key, [str(default)])[0]
        value = float(raw)
        return max(minimum, min(maximum, value))

    @classmethod
    def _build_type_counts(cls, params: dict[str, list[str]], num_bidders: int, scenario: str) -> dict[str, int] | None:
        if scenario != "heterogeneous":
            return None
        counts = {
            "truthful": cls._parse_int(params, "truthful_count", 3, 0, num_bidders),
            "shaded": cls._parse_int(params, "shaded_count", 3, 0, num_bidders),
            "budget": cls._parse_int(params, "budget_count", 3, 0, num_bidders),
            "aggressive": cls._parse_int(params, "aggressive_count", 3, 0, num_bidders),
        }
        if sum(counts.values()) != num_bidders:
            raise ValueError(f"Bidder-type counts must sum to {num_bidders}.")
        return counts

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            content = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if parsed.path == "/assets/cuhklogo.svg":
            content = LOGO_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        params = parse_qs(parsed.query)
        scenario = params.get("scenario", ["heterogeneous"])[0]
        mechanism = params.get("mechanism", ["GSP"])[0]
        try:
            rounds = self._parse_int(params, "rounds", 120, 20, 1000)
            num_bidders = self._parse_int(params, "num_bidders", 12, 4, 40)
            num_slots = self._parse_int(params, "num_slots", 4, 1, 8)
            value_min = self._parse_float(params, "value_min", 0.35, 0.1, 5.0)
            value_max = self._parse_float(params, "value_max", 3.2, 0.2, 6.0)
            latency_scale_ms = self._parse_int(params, "latency_scale_ms", 55, 10, 150)
            bid_deadline_ms = self._parse_int(params, "bid_deadline_ms", 120, 40, 250)
            if value_min >= value_max:
                raise ValueError("Value min must be smaller than value max.")
            type_counts = self._build_type_counts(params, num_bidders, scenario)
            collusion_rate_override = None
            if scenario == "collusion":
                collusion_count = self._parse_int(params, "collusion_count", max(2, num_bidders // 4), 2, num_bidders)
                collusion_rate_override = collusion_count / num_bidders
            sim_config = SimulationConfig(
                rounds=rounds,
                num_bidders=num_bidders,
                num_slots=num_slots,
                latency_scale_ms=latency_scale_ms,
                bid_deadline_ms=bid_deadline_ms,
                value_min=value_min,
                value_max=value_max,
            )
        except ValueError as exc:
            self._json({"error": str(exc)}, status=400)
            return

        if parsed.path == "/api/single":
            result = run_single_scenario(
                scenario=scenario,
                mechanism=mechanism,
                sim_config=sim_config,
                type_counts=type_counts,
                collusion_rate_override=collusion_rate_override,
            )
            self._json(
                {
                    "mechanism": result.mechanism,
                    "scenario": result.scenario,
                    "config": {
                        "num_bidders": sim_config.num_bidders,
                        "num_slots": sim_config.num_slots,
                        "value_min": sim_config.value_min,
                        "value_max": sim_config.value_max,
                        "latency_scale_ms": sim_config.latency_scale_ms,
                        "bid_deadline_ms": sim_config.bid_deadline_ms,
                        "type_counts": type_counts,
                        "collusion_rate": collusion_rate_override,
                    },
                    "metrics": result.metrics.__dict__,
                    "allocations": [allocation.__dict__ for allocation in result.allocations],
                    "bids": result.bids,
                    "arrival_times": result.arrival_times,
                }
            )
            return

        if parsed.path == "/api/compare":
            self._json(
                compare_mechanisms(
                    scenario=scenario,
                    sim_config=sim_config,
                    type_counts=type_counts,
                    collusion_rate_override=collusion_rate_override,
                )
            )
            return

        self.send_error(404, "Not Found")


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = HTTPServer((host, port), AuctionHandler)
    print(f"Serving auction simulator at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
