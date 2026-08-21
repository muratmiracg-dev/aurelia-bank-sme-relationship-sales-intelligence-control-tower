# Data Dictionary

## Source tables

| Table | Grain | Key fields | Description |
|---|---|---|---|
| `relationship_managers` | One row per synthetic RM | `rm_id`, region, capacity, target | Portfolio ownership and capacity |
| `customers` | One row per synthetic SME | `customer_id`, `rm_id`, sector, size, turnover | Firm and relationship profile |
| `risk_profile` | One row per customer | PD, rating, DPD, stage, KYC, AML | Restricted decision context |
| `monthly_flows` | Customer-month | inflow, outflow, POS, payroll, FX, trade | Aggregated activity evidence |
| `product_holdings` | Customer-product holding | product, exposure, income | Existing relationship footprint |
| `interactions` | Customer interaction | date, channel, outcome | CRM contact history |
| `campaign_history` | Customer-product campaign | treatment, activation, features | Synthetic model development data |

## Analytical tables

| Table | Grain | Key outputs |
|---|---|---|
| `customer_360` | Customer | relationship depth, wallet share, six-month flows, risk context |
| `candidate_features` | Customer-product not currently held | need, relationship gap and model features |
| `propensity_scores` | Candidate | propensity, contact uplift and three reason codes |
| `product_opportunities` | Candidate | economics, eligibility, score, status and suppression |
| `next_best_conversations` | Best policy-qualified product per customer | conversation prompt, task status and owner |
| `rm_worklist` | Capacity-allocated task | RM action queue |
| `rm_performance` | RM | capacity, expected profit and target coverage |
| `sales_funnel` | Expected stage | capacity-constrained funnel counts |
| `model_performance` | Candidate model | temporal discrimination and calibration metrics |
| `uplift_deciles` | Uplift decile | treatment/control response and incremental rate |
| `conduct_monitoring` | Operational segment | selection rate and expected economics |
| `management_controls` | Control | actual, threshold, status, owner and action |

## Important fields

| Field | Definition | Boundary |
|---|---|---|
| `wallet_share_proxy` | Bank exposure divided by 35% of turnover, bounded 0-1 | Not verified external wallet share |
| `need_signal` | Product-specific 0-1 observable-activity indicator | Not proof of customer intent |
| `propensity_probability` | Logistic champion activation probability under contact | Synthetic model estimate |
| `predicted_contact_uplift` | T-learner contact minus no-contact probability | Synthetic causal approximation |
| `expected_incremental_profit_try` | Positive uplift times risk-adjusted profit less contact cost | Not accounting forecast |
| `opportunity_score` | Weighted prioritisation score | Cannot override policy gates |
| `suppression_reason` | Pipe-delimited control reasons | Must be resolved by authoritative process |
| `automated_sale_flag` | Whether the system executes a sale | Always `false` by contract |

Dates use ISO `YYYY-MM-DD`. TRY amounts are nominal synthetic values. Boolean fields are true/false.
