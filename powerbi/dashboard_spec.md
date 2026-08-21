# Power BI Dashboard Specification

## Purpose

The Power BI layer converts governed CSV outputs into an executive, regional-manager and
relationship-manager decision product. It must never be presented as an automated sales,
credit-approval or suitability engine.

## Recommended model

```text
relationship_managers[rm_id] 1 --- * customer_360[rm_id]
relationship_managers[rm_id] 1 --- * rm_performance[rm_id]
relationship_managers[rm_id] 1 --- * next_best_conversations[rm_id]
customer_360[customer_id]    1 --- * next_best_conversations[customer_id]
```

Use single-direction filters from dimensions to facts. Keep controls and model-performance
tables disconnected so that their enterprise-level values are not multiplied by customer or
product context.

## Page 1 - Executive control tower

- SME customers, prioritised conversations, expected incremental profit and control breaches.
- Product opportunity mix ranked by expected incremental profit.
- Capacity-constrained sales funnel.
- One explicit decision card: approve KYC remediation and weekly backlog governance.

## Page 2 - Relationship depth

- Products per customer, relationship-depth score and wallet-share proxy.
- Size, sector and region distribution.
- Customers with high business scale and shallow product penetration.

## Page 3 - Product opportunity intelligence

- Candidate, eligible and policy-qualified opportunity counts.
- Propensity, treatment uplift, need and profitability decomposition.
- Product drill-through with reason codes and suppression rationale.

## Page 4 - RM cockpit

- Row-level, access-controlled worklist.
- Priority, product, conversation prompt, SLA, expected value and explanation.
- Capacity utilisation, waitlist and target-coverage context.

## Page 5 - Risk-adjusted economics

- Gross income to funding cost, expected loss, capital charge, service cost and profit bridge.
- RAROC-style output by product; label it illustrative and assumption-driven.
- Profitability versus propensity scatter to expose low-value high-propensity candidates.

## Page 6 - Model and uplift validation

- Champion/challenger ROC AUC, PR AUC, Brier and top-decile lift.
- Treatment/control activation by uplift decile.
- Temporal split dates, model boundary and coefficient table.

## Page 7 - Conduct and controls

- Permission, KYC, AML, credit-risk and financial-freshness suppressions.
- Selection rates by size band and region as operational diagnostics, not proof of fairness.
- Data-quality and management controls with owner, threshold and action.

## Row-level security reference

Production implementation should map authenticated users to `rm_id` or approved regional
scope. The portfolio demonstration contains no identity provider, entitlement store or claim of
production-ready access control.
