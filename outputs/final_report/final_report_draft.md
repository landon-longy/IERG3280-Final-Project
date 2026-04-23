# Robustness and Efficiency Analysis of GSP and VCG Auctions in Heterogeneous Networked Environments

## 1. Introduction

Auction mechanisms are a core component of many networked markets, especially sponsored search and online advertising systems where multiple bidders compete for a limited number of ranked positions. In this setting, two representative mechanisms are the Generalized Second Price (GSP) auction and the Vickrey-Clarke-Groves (VCG) mechanism. The VCG family is grounded in the classical mechanism-design work of Vickrey, Clarke, and Groves [1]–[3]. GSP, by contrast, became especially influential in sponsored search and position auctions because of its simplicity and strong revenue performance [4], [5]. From a mechanism-design perspective, VCG is attractive because truthful bidding is a dominant strategy and the allocation is socially efficient in the standard model [1]–[3].

However, practical networked environments deviate from the ideal assumptions used in classical mechanism analysis. Real systems contain heterogeneous bidder behaviors, collusive bid suppression, and latency-induced asynchrony. These factors may reduce revenue, distort welfare, and alter bidder payoff distributions. Therefore, the goal of this project is to evaluate how robust GSP and VCG remain when these non-ideal conditions are introduced in a controlled simulation environment.

Recent literature confirms that auction-based digital advertising remains economically important and technically complex. Waisman, Nair, and Carrion study real-time bidding (RTB) auctions directly and show that auction structure is central to how advertising effectiveness is inferred in practice [6]. Bergemann, Bonatti, and Wu further analyze modern digital advertising auctions in environments where platforms use data and auction-like allocation rules [7]. Recent empirical and analytical work also supports the practical relevance of the three distortions examined in this report. First, advertiser heterogeneity is real: Ghoshal, Mookerjee, and Sun explicitly model heterogeneous advertisers operating through RTB contracts in a real aggregator setting [8], while Xu, Zhu, and Dutta show that asymmetric advertisers with different quality efficiencies can materially change position-auction outcomes [9]. Second, collusion-like coordination risks are also realistic in digital advertising: Decarolis et al. study algorithmic bidding in online advertising and report that bidding through a common intermediary, which they describe as commonly observed in the data, lowers auctioneer revenue relative to individual bidding [10]. Third, latency is not merely a modeling convenience. Aqeel et al. analyze 393,400 real header-bidding auctions and directly measure latency overheads and their revenue implications [11]. Finally, recent empirical work on sponsored search auctions continues to document substantial variation in bidder behavior across product categories and quality-scoring environments, which further motivates simulation with heterogeneous bidder types [12].

Following the proposal and subsequent feedback, this project implements a multi-slot auction simulator and evaluates the two mechanisms under a one-factor-at-a-time design. Three experiment groups are studied. First, we vary the bidder-type mixture while keeping the rest of the market fixed. Second, we introduce collusion through a bidding ring and study a 0% balanced-market baseline together with collusion ratios from 10% to 90%. Third, we fix the baseline market and add network latency through late bid arrivals. For each experiment, we record seller revenue, social welfare, allocation efficiency, and bidder payoff distribution, and we visualize the results using summary figures. To make the baselines more interpretable, two reference markets are used: an all-truthful market for theoretical comparison and a balanced heterogeneous market with a 1:1:1:1 type ratio for the main robustness experiments.

The main findings are as follows. GSP consistently yields substantially higher seller revenue than VCG in all tested environments. VCG, in contrast, tends to produce lower payoff dispersion and lower utility inequality, which is consistent with its incentive-compatible structure. In the collusion experiment, the key quantity is not whether the VCG revenue-loss percentage relative to GSP is positive, since VCG already tends to earn less revenue than GSP in the standard model, but how that percentage changes with collusion intensity. The loss percentage decreases slightly from 51.88% at 0% collusion to 51.49% at 40% collusion, suggesting that VCG is relatively more resilient in the low-to-moderate collusion region, but then rises to 68.05% at 90% collusion, suggesting that GSP is relatively more resilient under high collusion. Even so, GSP maintains the higher absolute revenue throughout.

## 2. Auction Model and Simulation Design

### 2.1 Multi-slot auction model

The simulator models a slot-based auction with five ranked positions. Each slot has a click-through rate (CTR) that decreases with rank. In the implementation, the default CTR profile is:

`[1.00, 0.82, 0.64, 0.49, 0.37]`

Each bidder is associated with:

- a true valuation
- a bidder type
- a budget
- a bid shading factor
- a bid arrival latency

For GSP, bidders are ranked by effective bid, and the bidder in each slot pays the next bidder's bid scaled by the slot CTR. This follows the standard logic of sponsored-search position auctions studied in [4], [5]. For VCG, payments are computed by the standard externality formula in the multi-slot environment, following the classic Vickrey-Clarke-Groves principle [1]–[3]. A bid submission deadline is imposed, so late bids are excluded in the latency experiment.

### 2.2 Bidder types

The simulator contains four bidder types:

- `truthful`: bids close to true value
- `shaded`: systematically underbids
- `budget`: underbids and is constrained by affordability
- `aggressive`: slightly overbids relative to true value

This design allows us to study both allocative and distributive effects. In particular, the heterogeneous-bidder experiment examines not only aggregate metrics but also the mean payoff, average bid, and win rate for each bidder type.

This design is also consistent with recent work arguing that modern ad markets contain advertisers with different contracts, budgets, quality scores, and strategic incentives [8], [9], [12].

### 2.3 One-factor-at-a-time experiment design

To make causal interpretation cleaner, the final implementation adopts a one-factor-at-a-time framework.

#### Heterogeneous bidder mixtures

Two baseline references are used.

The first is a theoretical truthful baseline:

- truthful: 100%
- shaded: 0%
- budget: 0%
- aggressive: 0%

The second is the balanced heterogeneous baseline:

- truthful: 25%
- shaded: 25%
- budget: 25%
- aggressive: 25%

On top of the balanced heterogeneous baseline, four heavy market profiles are tested:

- truthful-heavy
- shaded-heavy
- budget-heavy
- aggressive-heavy

Only the type mixture changes in this experiment; no collusion is introduced, and no extra latency stress is added. The all-truthful and balanced markets are treated separately as the two heterogeneous references. Formally, let \(T_i\) denote the type of bidder \(i\). Then

\[
T_i \sim \mathrm{Categorical}(\pi)
\]

where \(\pi\) is the type-mix vector over `(truthful, shaded, budget, aggressive)`. In the balanced market,

\[
\pi^{\text{bal}} = (0.25,\, 0.25,\, 0.25,\, 0.25)
\]

To keep the heavy profiles symmetric, the emphasized type always receives weight `0.55` and the other three types each receive weight `0.15`. For a heavy profile indexed by type \(h\),

\[
\pi_t^{(h)} =
\begin{cases}
0.55, & t = h \\
0.15, & t \neq h
\end{cases}
\]

Thus, `truthful-heavy` is `(0.55, 0.15, 0.15, 0.15)`, and the other heavy profiles are defined analogously. The all-truthful reference is kept as a separate benchmark rather than being treated as one of the heterogeneous profiles.

#### Collusion

In the collusion experiment, the type mix is fixed at the balanced 1:1:1:1 market. A bidding ring is then introduced, and the collusion ratio is increased across:

- 10%
- 30%
- 50%
- 70%
- 90%

Formally, let \(\rho\) denote the collusion ratio, \(n\) the number of bidders, and \(\mathcal{C}\) the colluding set. In the simulator,

\[
|\mathcal{C}| = \max\{2,\lfloor \rho n \rfloor\}
\]

Within the ring, the proxy bidder is the colluding bidder with the highest valuation:

\[
p = \arg\max_{i \in \mathcal{C}} v_i
\]

The collusive bids are then defined as

\[
b_p = \max\{r,\; 0.72\, v_p\}
\]

and

\[
b_j = r, \qquad \forall j \in \mathcal{C}\setminus\{p\}
\]

where \(r\) is the reserve price. All non-colluding bidders keep their normal type-dependent bidding rules. This isolates the effect of coordinated competition reduction.

The coefficient \(0.72\) is a modeling choice rather than a theoretical constant. It is selected as a moderate collusive shading factor: low enough to suppress price competition and reduce seller revenue, but still high enough for the proxy bidder to remain competitive in the auction. The \(\max\{r,\cdot\}\) term ensures that the collusive proxy bid does not fall below the reserve price.

Although our collusion implementation is stylized, it is motivated by recent evidence that algorithmic bidding and bidding through common intermediaries are relevant concerns in online advertising markets [10].

#### Network latency

In the latency experiment, the type mix is again fixed at the balanced 1:1:1:1 market. Bid delays are generated from a Gaussian distribution and then adjusted by bidder type. In the implementation, the baseline latency of bidder \(i\) is:

\[
L_i^{(0)} = \max\{0,\; \mathcal{N}(\mu,\, 0.45\mu)\}
\]

where \(\mu\) is the configured latency scale in milliseconds. In the reported experiments, \(\mu = 58\).

The final latency is:

\[
L_i = L_i^{(0)} + \Delta_i
\]

where

\[
\Delta_i =
\begin{cases}
U(25,70), & \text{if bidder } i \text{ is truthful} \\
U(10,45), & \text{if bidder } i \text{ is budget-constrained} \\
0, & \text{otherwise}
\end{cases}
\]

Let \(D\) denote the submission deadline. In the simulator,

\[
D = 120 \text{ ms}
\]

Bidder \(i\) is eligible only if

\[
L_i \le D
\]

Equivalently, the eligible set is:

\[
\mathcal{E} = \{i : L_i \le D\}
\]

Only bidders in \(\mathcal{E}\) enter the ranking and payment computation. Intuitively, this rule models two realistic effects at the same time. First, bid arrival time is noisy, so different bidders experience different network delays. Second, some bidder types may face more delay than others because of slower decision or delivery pipelines. The deadline then turns latency into an economically meaningful factor: a bid that arrives too late is simply excluded from the auction.

This setting is intended to reflect the fact that real ad auctions are highly time-sensitive and that measured latency overheads can affect both system performance and revenue outcomes [11].

### 2.4 Evaluation metrics

For every experiment group, the following metrics are recorded:

- seller revenue
- social welfare
- allocation efficiency
- bidder payoff mean
- bidder payoff standard deviation
- utility Gini coefficient
- truthful-gap proxy
- late-bid rate
- bidder payoff by type

This metric set directly follows the final report requirement that each experiment should record seller revenue, social welfare, allocation efficiency, and bidder payoff distribution.

## 3. Experimental Results

All aggregate results are produced from 300 simulation rounds with 20 bidders and 5 slots. The figures are generated directly from the simulator outputs in `outputs/final_report/`.

### 3.1 Baseline comparison

The revised design uses two baseline markets.

In the all-truthful baseline:

- GSP revenue: 7.2639
- VCG revenue: 3.5263
- GSP social welfare: 8.8983
- VCG social welfare: 8.8643
- GSP efficiency: 0.9354
- VCG efficiency: 0.9387
- GSP truthful gap: 0.0000
- VCG truthful gap: 0.0000

In the balanced heterogeneous baseline:

- GSP revenue: 6.8093
- VCG revenue: 3.2764
- GSP social welfare: 8.7601
- VCG social welfare: 8.6977
- GSP efficiency: 0.9209
- VCG efficiency: 0.9209
- GSP payoff standard deviation: 0.3120
- VCG payoff standard deviation: 0.2634
- GSP utility Gini: 0.4284
- VCG utility Gini: 0.1300

These two baselines serve different purposes. The all-truthful market is useful for connecting the simulator to standard theory, while the balanced heterogeneous market is the main empirical reference used for the collusion and latency experiments. In both cases, GSP is substantially stronger in seller revenue, whereas VCG yields lower payoff dispersion and lower inequality.

### 3.2 Heterogeneous bidder mixtures

The heterogeneous-mixture results are summarized in the following figures:

- `heterogeneous_revenue.svg`
- `heterogeneous_welfare.svg`
- `heterogeneous_payoff_table.csv`

Relative to the balanced 1:1:1:1 baseline, the heterogeneous-mixture experiment shows that GSP consistently outperforms VCG in revenue across the four heavy profiles:

- truthful-heavy: GSP 6.9760 vs VCG 3.3328
- shaded-heavy: GSP 6.3792 vs VCG 3.0377
- budget-heavy: GSP 6.5605 vs VCG 3.1579
- aggressive-heavy: GSP 7.0471 vs VCG 3.4082

The two heterogeneous references are:

- all-truthful: GSP 7.2639 vs VCG 3.5263 in revenue; GSP 8.8983 vs VCG 8.8643 in welfare
- balanced: GSP 6.8093 vs VCG 3.2764 in revenue; GSP 8.7601 vs VCG 8.6977 in welfare

Figure 1 (`heterogeneous_revenue.svg`) summarizes this seller-revenue comparison across the two heterogeneous references and the four heavy profiles. Its role is to show how revenue changes when the market composition shifts toward one bidder type while the rest of the auction environment is held fixed.

Social welfare is comparatively stable across the four heavy profiles and remains close between the two mechanisms:

- truthful-heavy: GSP 8.7994 vs VCG 8.7542
- shaded-heavy: GSP 8.7869 vs VCG 8.7231
- budget-heavy: GSP 8.8008 vs VCG 8.7250
- aggressive-heavy: GSP 8.7863 vs VCG 8.6767

The corresponding mean payoff-by-type table is:

| Setting | Mechanism | Truthful | Shaded | Budget | Aggressive |
|---|---:|---:|---:|---:|---:|
| All-truthful | GSP | 0.0817 | - | - | - |
| All-truthful | VCG | 0.2669 | - | - | - |
| Balanced | GSP | 0.0995 | 0.0932 | 0.1034 | 0.0939 |
| Balanced | VCG | 0.3197 | 0.1529 | 0.2176 | 0.3882 |
| Truthful-heavy | GSP | 0.0958 | 0.0805 | 0.0887 | 0.0841 |
| Truthful-heavy | VCG | 0.3021 | 0.1431 | 0.2022 | 0.3499 |
| Shaded-heavy | GSP | 0.1234 | 0.1173 | 0.1295 | 0.1204 |
| Shaded-heavy | VCG | 0.3809 | 0.2157 | 0.2811 | 0.4222 |
| Budget-heavy | GSP | 0.1108 | 0.1106 | 0.1209 | 0.1078 |
| Budget-heavy | VCG | 0.3581 | 0.1940 | 0.2492 | 0.4019 |
| Aggressive-heavy | GSP | 0.0869 | 0.0762 | 0.0732 | 0.0753 |
| Aggressive-heavy | VCG | 0.2683 | 0.1122 | 0.1440 | 0.3295 |

The payoff-by-type analysis is particularly informative. Under the balanced market, for example:

- In GSP, mean payoff is relatively similar across types, ranging from 0.0932 to 0.1034.
- In VCG, aggressive bidders obtain the highest mean payoff at 0.3882, while truthful bidders also benefit strongly at 0.3197.

Under the shaded-heavy profile:

- GSP shaded-bidder mean payoff: 0.1163
- VCG shaded-bidder mean payoff: 0.2210

Under the budget-heavy profile:

- GSP budget-bidder mean payoff: 0.1223
- VCG budget-bidder mean payoff: 0.2500

These results suggest that heterogeneity changes the distribution of gains more than it changes aggregate welfare. VCG appears especially favorable to bidder surplus, while GSP remains the stronger revenue mechanism.

### 3.3 Collusion and the revenue-loss question

The collusion results are the central response to the feedback:

> Please quantify the "Revenue Loss" of VCG compared to GSP under the collusion scenario to see if VCG's incentive compatibility still holds practical advantages.

In this report, the revenue loss of VCG relative to GSP is defined as:

\[
\text{Revenue Loss}_{\text{VCG}\mid\text{GSP}} = R_{\text{GSP}} - R_{\text{VCG}}
\]

and the percentage loss is:

\[
\text{Revenue Loss \%}_{\text{VCG}\mid\text{GSP}} =
\frac{R_{\text{GSP}} - R_{\text{VCG}}}{R_{\text{GSP}}}\times 100\%
\]

That is, GSP is treated as the reference mechanism, and we measure how much seller revenue is lost when VCG is used instead.

The relevant figures are:

- `collusion_revenue.svg`
- `collusion_welfare.svg`
- `collusion_vcg_revenue_loss.svg`
- `collusion_vcg_revenue_loss_trend.svg`

The quantified revenue loss of VCG relative to GSP is:

- 0% collusion: 3.5329 loss, 51.88%
- 10% collusion: 3.4586 loss, 51.78%
- 20% collusion: 3.3741 loss, 51.61%
- 30% collusion: 3.2712 loss, 51.51%
- 40% collusion: 3.1534 loss, 51.49%
- 50% collusion: 3.0699 loss, 52.10%
- 60% collusion: 2.9484 loss, 52.85%
- 70% collusion: 2.6840 loss, 53.21%
- 80% collusion: 2.3934 loss, 56.16%
- 90% collusion: 1.6893 loss, 68.05%

At the report-relevant 30% collusion level:

- GSP revenue: 6.3506
- VCG revenue: 3.0794
- Absolute revenue loss of VCG relative to GSP: 3.2712
- Relative revenue loss: 51.51%

Figure 2 (`collusion_vcg_revenue_loss_trend.svg`) visualizes this feedback-driven metric directly. The key point is not that the loss percentage is positive, since VCG is already known to generate lower revenue than GSP in the standard model. Instead, the more informative question is how this percentage changes as collusion intensifies.

The trend is revealing. From 0% to 40% collusion, the loss percentage declines slightly from 51.88% to 51.49%. Under this interpretation, VCG revenue is falling more slowly than GSP revenue as collusion rises, so VCG appears relatively more robust in the low-to-moderate collusion region. After 40%, however, the loss percentage begins to increase, reaching 52.10% at 50%, 53.21% at 70%, 56.16% at 80%, and 68.05% at 90%. This means that beyond moderate collusion, VCG revenue deteriorates faster relative to GSP, so GSP becomes the relatively more robust mechanism at high collusion levels.

This interpretation should be distinguished from absolute revenue ranking. In absolute terms, GSP still produces higher seller revenue at every collusion ratio in the table. What changes is the relative rate at which the two mechanisms deteriorate as collusion increases.

On the welfare side, the 0% baseline is slightly GSP-favoring, but the gap narrows and eventually reverses at some higher collusion levels:

- 0% collusion: GSP 8.7601 vs VCG 8.6977
- 10% collusion: GSP 8.7652 vs VCG 8.6909
- 20% collusion: GSP 8.7506 vs VCG 8.6972
- 30% collusion: GSP 8.7014 vs VCG 8.6698
- 40% collusion: GSP 8.5950 vs VCG 8.6252
- 50% collusion: GSP 8.4824 vs VCG 8.5278
- 60% collusion: GSP 8.3383 vs VCG 8.3664
- 70% collusion: GSP 8.0090 vs VCG 8.0532
- 80% collusion: GSP 7.4438 vs VCG 7.4389
- 90% collusion: GSP 8.1046 vs VCG 8.1138

Compared with the balanced heterogeneous baseline, moderate collusion causes revenue to fall from 6.8093 to 6.3506 in GSP and from 3.2764 to 3.0794 in VCG. At the same time, social welfare changes only from 8.7601 to 8.7014 in GSP and from 8.6977 to 8.6698 in VCG. At higher collusion levels, VCG slightly exceeds GSP in welfare, for example at 40%, 50%, 60%, 70%, and 90%, so the main effect of collusion in this implementation is much stronger on payment competition than on total allocative value.

Therefore, for this project's collusion model, the main practical takeaway is not a simple winner-take-all conclusion. Under low-to-moderate collusion, VCG appears relatively more robust according to the loss-percentage trend, whereas under high collusion, GSP appears relatively more robust. However, in absolute seller revenue, GSP remains larger throughout.

### 3.4 Network latency

The latency results are shown in:

- `latency_revenue.svg`
- `latency_welfare.svg`
- `latency_efficiency.svg`
- `latency_late_bid_rate.svg`

Compared with the balanced heterogeneous baseline:

- GSP revenue decreases from 6.8093 to 6.5741
- VCG revenue decreases from 3.2764 to 3.1755
- GSP social welfare decreases from 8.7601 to 8.6393
- VCG social welfare decreases from 8.6977 to 8.5896
- GSP efficiency decreases from 0.9209 to 0.9082
- VCG efficiency decreases from 0.9209 to 0.9094

The most direct effect is on participation timing:

- GSP late-bid rate rises from 0.0072 to 0.1058
- VCG late-bid rate rises from 0.0092 to 0.1040

Figure 3 (`latency_late_bid_rate.svg`) is used to visualize this timing effect. It compares the late-bid rates of GSP and VCG under the balanced baseline and under the latency-stress setting, making the participation loss caused by delayed submission immediately visible.

This means that latency substantially reduces the share of valid bids and, as a result, mildly degrades both revenue and allocative quality. The bidder-type breakdown also shows that truthful bidders are affected more strongly than aggressive bidders:

- truthful mean payoff in GSP falls from 0.0995 to 0.0777
- aggressive mean payoff in GSP rises from 0.0939 to 0.1060
- truthful mean payoff in VCG falls from 0.3197 to 0.2453
- aggressive mean payoff in VCG rises from 0.3882 to 0.4177

This pattern suggests that asynchronous bidding can amplify strategic advantages for bidders whose behavior is less sensitive to delayed submission.

## 4. Discussion

The simulation results reveal a consistent pattern across all experiment groups. GSP is the stronger mechanism for seller revenue, while VCG is the stronger mechanism for bidder surplus smoothness and payoff equality. This pattern appears both in the all-truthful reference and in the balanced heterogeneous reference, and it persists under heterogeneity and latency.

However, the feedback-driven collusion experiment shows that these theoretical advantages do not necessarily translate into practical robustness. If the evaluation criterion is seller-side performance, VCG is clearly dominated by GSP in the collusion environment studied here. The measured revenue loss of around 60% across a wide range of collusion ratios is too large to ignore.

The heterogeneous-mixture experiment also shows that market composition matters. Revenue is lowest in the shaded-heavy profile and highest in the aggressive-heavy profile, which is intuitive because more aggressive bidding raises price pressure. Yet the welfare differences are relatively small, meaning that type mixtures affect payment distribution more than total allocative value.

The latency experiment emphasizes that network effects do not need to be strategic to matter. Simply excluding late bids already reduces revenue, welfare, and efficiency in both mechanisms. This highlights the importance of system-level factors when evaluating auction robustness.

There are also limitations. First, the collusion model uses a single-ring proxy strategy, which is intentionally simple. More complex ring strategies could yield different outcomes. Second, bidder values and budgets are sampled from stylized distributions rather than calibrated from real auction logs. Third, latency is modeled through a deadline rule instead of a full event-driven market. These limitations do not invalidate the conclusions, but they suggest useful directions for future work.

## 5. Conclusion

This project implemented a simulation framework for comparing GSP and VCG auctions in a multi-slot networked environment. The final design followed the proposal goals and the later feedback by evaluating heterogeneous bidder mixtures, collusion, and network latency in a one-factor-at-a-time framework with two reference baselines: an all-truthful market and a balanced 1:1:1:1 heterogeneous market.

Three conclusions stand out.

First, GSP consistently achieves much higher seller revenue than VCG. Second, VCG tends to produce more equal and less volatile bidder payoffs, which reflects its incentive-compatible design. Third, under collusion, VCG experiences a very large revenue loss relative to GSP: 51.51% at 30% collusion and 68.05% at 90% collusion. Therefore, in this project's simulated environment, VCG's theoretical truthfulness does not yield a practical revenue advantage under collusive pressure.

Overall, the project shows that robustness in networked markets should be evaluated not only through mechanism-theoretic properties, but also through heterogeneous behavior, coordinated strategy, and network timing effects.

## References

[1] William Vickrey, “Counterspeculation, Auctions, and Competitive Sealed Tenders,” *The Journal of Finance*, vol. 16, no. 1, pp. 8–37, 1961. DOI: 10.1111/j.1540-6261.1961.tb02789.x.

[2] Edward H. Clarke, “Multipart Pricing of Public Goods,” *Public Choice*, vol. 11, no. 1, pp. 17–33, 1971. DOI: 10.1007/BF01726210.

[3] Theodore Groves, “Incentives in Teams,” *Econometrica*, vol. 41, no. 4, pp. 617–631, 1973.

[4] Benjamin Edelman, Michael Ostrovsky, and Michael Schwarz, “Internet Advertising and the Generalized Second-Price Auction: Selling Billions of Dollars Worth of Keywords,” *American Economic Review*, vol. 97, no. 1, pp. 242–259, 2007. DOI: 10.1257/aer.97.1.242.

[5] Hal R. Varian, “Position Auctions,” *International Journal of Industrial Organization*, vol. 25, no. 6, pp. 1163–1178, 2007.

[6] Caio Waisman, Harikesh S. Nair, and Carlos Carrion, “Online Causal Inference for Advertising in Real-Time Bidding Auctions,” *Marketing Science*, vol. 44, no. 1, pp. 176–195, 2025. Published online 2024. DOI: 10.1287/mksc.2022.0406.

[7] Dirk Bergemann, Alessandro Bonatti, and Nicholas Wu, “How Do Digital Advertising Auctions Impact Product Prices?” *The Review of Economic Studies*, vol. 92, no. 4, pp. 2330–2358, 2025. Published online 2024. DOI: 10.1093/restud/rdae087.

[8] Abhijeet Ghoshal, Radha Mookerjee, and Zhen Sun, “Serving Two Masters? Optimizing Mobile Ad Contracts with Heterogeneous Advertisers,” *Production and Operations Management*, vol. 32, no. 2, pp. 618–636, 2023. DOI: 10.1111/poms.13890.

[9] Zibin Xu, Yi Zhu, and Shantanu Dutta, “Adverse Inclusion of Asymmetric Advertisers in Position Auctions,” *International Journal of Research in Marketing*, vol. 40, no. 3, pp. 724–740, 2023. DOI: 10.1016/j.ijresmar.2023.01.001.

[10] Francesco Decarolis, Gabriele Rovigatti, Michele Rovigatti, and Ksenia Shakhgildyan, “Artificial Intelligence, Algorithmic Bidding and Collusion in Online Advertising,” IGIER Working Paper No. 708, 2024.

[11] Waqar Aqeel, Debopam Bhattacherjee, Balakrishnan Chandrasekaran, P. Brighten Godfrey, Gregory Laughlin, Bruce Maggs, and Ankit Singla, “Untangling Header Bidding Lore: Some Myths, Some Truths, and Some Hope,” in *Passive and Active Measurement: 21st International Conference (PAM 2020)*, pp. 280–297, 2020. DOI: 10.1007/978-3-030-44081-7_17.

[12] Dongwoo Kim and Pallavi Pal, “Nonparametric Estimation of Sponsored Search Auctions and Impact of Ad Quality on Search Revenue,” *Management Science*, vol. 71, no. 12, pp. 10047–10066, 2025. DOI: 10.1287/mnsc.2023.02052.

## Suggested Figure Placement

- Fig. 1: `heterogeneous_revenue.svg`
- Fig. 2: `heterogeneous_welfare.svg`
- Fig. 3: `collusion_revenue.svg`
- Fig. 4: `collusion_vcg_revenue_loss_trend.svg`
- Fig. 5: `latency_revenue.svg`
- Fig. 6: `latency_late_bid_rate.svg`

For a strict five-page version, a practical choice is to keep only four figures in the main text:

- `heterogeneous_revenue.svg`
- `collusion_revenue.svg`
- `collusion_vcg_revenue_loss_trend.svg`
- `latency_late_bid_rate.svg`

The remaining figures can be summarized numerically in the text or moved to an appendix if allowed.
