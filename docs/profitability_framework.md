# Risk-Adjusted Profitability Framework

## Purpose

The framework prevents propensity from becoming the sole sales objective. It asks whether a
potentially relevant conversation is economically attractive after transparent risk and capital
charges.

## Product notional

Each product uses an auditable business-volume proxy, for example 12% of turnover for working
capital, two times six-month flow for transaction products, and 65% of average deposits for term
deposits. Values are capped between TRY 50,000 and TRY 250m.

## Profit bridge

```text
Active exposure = estimated notional × utilization
Gross income = active exposure × annual revenue rate + notional × fee rate
Expected loss = active exposure × PD × LGD              [credit products]
Capital = active exposure × product capital factor × 12%
Capital charge = capital × 18% cost of capital
Risk-adjusted profit = gross income - funding cost - expected loss - capital charge - service cost
Expected incremental profit = max(contact uplift, 0) × risk-adjusted profit - TRY 420 contact cost
RAROC-style ratio = risk-adjusted profit / allocated capital
```

All rates are internal synthetic assumptions in `config/assumptions.yml`. They are not Aurelia
Bank actuals, market quotations, regulatory parameters, accounting policy or pricing guidance.

## Interpretation

- Negative economics suppresses policy qualification even when propensity is high.
- A high RAROC-style ratio on a low-capital service does not automatically outrank customer need.
- The framework is first-year and static; it excludes lifetime behavior, taxes, optionality,
  liquidity horizons, hedging costs and portfolio concentration.
- Production implementation would reconcile with Finance, Treasury, Credit Risk and regulatory
  capital systems and apply independently approved assumptions.
