# Methodology

## 1. Analytical population

The cutoff is 20 August 2026. The portfolio contains 3,200 controlled-synthetic SME customers,
48 synthetic relationship managers, 18 months of monthly flow aggregates, 7,044 product holdings
and 16,000 historical treatment/control campaign observations.

## 2. Customer 360

Customer 360 combines firm profile, RM ownership, annual turnover, workforce, cross-border
activity, digital engagement, six-month cash-flow aggregates, holdings, income, interaction
recency, PD, arrears, KYC review status and AML priority. It contains no real personal data.

## 3. Relationship depth

The relationship-depth score is an explicit weighted indicator:

```text
52% product penetration
+ 28% bank-exposure-to-turnover proxy
+ 20% relationship tenure
```

Wallet share is a bounded proxy based on bank exposure relative to 35% of annual turnover. It is
not a verified share of a customer's total banking wallet.

## 4. Product need

Eight product-specific functions translate observable flows into a 0-1 need signal. Examples:

- POS uses merchant-volume share, digital engagement and business scale.
- Payroll uses payroll outflows, employee count and scale.
- Trade finance uses trade and FX flows plus importer/exporter flags.
- FX risk management requires documented FX activity; it is never a speculative sales signal.

Existing holdings are excluded before opportunity scoring.

## 5. Propensity model

Historical campaigns are ordered by campaign date. The earliest 80% form development data and
the latest 20% form the temporal validation window. The interpretable logistic classifier is the
champion; histogram gradient boosting is a challenger. The operating evidence includes ROC AUC,
PR AUC, Brier score, log loss and top-decile lift.

## 6. Uplift model

Separate logistic models are fitted to randomized synthetic contacted and control observations.
Current uplift is:

```text
P(activation | contacted, X) - P(activation | not contacted, X)
```

This is a synthetic T-learner estimate. It is not a causal claim about real customers.

## 7. Economics

For each product, a transparent notional proxy and governed product parameters produce:

```text
Gross income
- FTP-style funding cost
- expected loss (credit products)
- allocated-capital charge
- servicing cost
= first-year risk-adjusted profit if activated
```

Expected incremental profit equals positive predicted contact uplift multiplied by the
activation-state profit, less the contact cost.

## 8. Opportunity score

```text
32% propensity
+ 18% normalized uplift
+ 22% need
+ 18% profitability percentile
+ 10% relationship gap
```

The weighted score cannot bypass policy thresholds or suppression rules.

## 9. Governance gates

Candidates are suppressed for missing contact permission, incomplete beneficial ownership,
materially overdue KYC, high-priority AML review, out-of-policy credit risk, material arrears,
stale financials for credit products or insufficient documented FX need.

## 10. Capacity allocation

One policy-qualified conversation per customer is retained. Conversations are ranked inside the
RM portfolio and allocated only up to the lower of the configured monthly capacity and the
`max_open_tasks_per_rm` policy ceiling. The authorised RM owns the
final decision and may record contradictory evidence or decline to contact.
