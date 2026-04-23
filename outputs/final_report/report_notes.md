# Final Report Notes

This project directly supports a 5-page final report around the following sections:

1. Introduction and motivation
2. Auction model and mechanism design
3. Experimental setup
4. Results and discussion
5. Conclusion

## What the implementation covers

- Multi-slot ranking with click-through-rate decay
- `GSP` payment rule
- `VCG` payment rule
- Heterogeneous bidder types:
  - truthful
  - shaded
  - budget-constrained
  - aggressive
- One-factor-at-a-time experiments:
  - heterogeneous type-mix sweep
  - collusion-rate sweep
  - baseline-versus-latency comparison
- Two baseline references:
  - all-truthful baseline
  - balanced 1:1:1:1 heterogeneous baseline
- Collusion via a bidding ring that suppresses follower bids
- Latency via bid arrival times and a submission deadline

## Metrics available for the report

- Seller revenue
- Social welfare
- Allocation efficiency
- Bidder payoff mean and standard deviation
- Bidder payoff by type
- Utility Gini coefficient
- Late bid rate
- Truthful gap
- Collusion discount

## Feedback-specific metric

For the collusion scenario the simulator outputs:

- `vcg_revenue_loss_vs_gsp`
- `vcg_revenue_loss_pct_vs_gsp`

Suggested sentence pattern for the report:

`Under bidder collusion, VCG generated lower seller revenue than GSP by X (Y%), although it still preserved stronger welfare/efficiency behavior in our simulation.`
