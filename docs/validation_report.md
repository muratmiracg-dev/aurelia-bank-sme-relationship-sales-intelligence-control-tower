# Validation Report

## Scope

Independent-style challenge of synthetic data integrity, temporal model performance, uplift
behavior, economics, conduct gates, capacity and reproducibility. This is not an independent bank
validation or regulatory approval.

## Data controls

All 14 checks passed: uniqueness, RM assignment, customer-risk reconciliation, non-negative flows,
governed product codes, binary campaign labels and treatment, Customer 360 grain, candidate
uniqueness, bounded needs, exclusion of held products, bounded PD and complete flow coverage.

## Champion/challenger result

| Model | ROC AUC | PR AUC | Brier | Log loss | Top-decile lift |
|---|---:|---:|---:|---:|---:|
| Logistic champion | 0.7153 | 0.4945 | 0.1820 | 0.5426 | 2.073x |
| Histogram-gradient challenger | 0.7147 | 0.4918 | 0.1823 | 0.5434 | 2.041x |

The logistic model remains champion because it is marginally stronger across the verified metrics
and materially easier to explain and govern.

## Uplift validation

The T-learner's predicted uplift is checked on the randomized hold-out period
(2026-05-02 to 2026-08-05, 3,200 campaigns: 1,779 treated, 1,421 control), in
`artifacts/results/uplift_validation.csv`:

| Check | Result | Reading |
|---|---:|---|
| Qini area (curve minus random line, per observation) | 0.0035 | ranking finds more incremental activations than random contact |
| Permutation p-value (999 re-orderings, seed 20260821) | 0.096 | not significant at 5%; 9.6% of random orderings match it |
| Observed average uplift (treated minus control rate) | 7.14% | unbiased, because treatment was randomized |
| Mean predicted uplift | 4.96% | understates the observed effect; calibration ratio 0.69 |

The decile table (`uplift_deciles.csv`) shows the same picture: the top decile's observed
incremental rate (6.3%) is below deciles 2-6. The uplift ranking is therefore weak evidence, and
the expected-incremental-profit figure inherits both the ranking noise and the ~30% under-
prediction. The output is diagnostic: it does not certify causal identification, policy
invariance or production transportability.

## Decision controls

- No held product is proposed.
- Suppressed candidates cannot reach the worklist.
- Every task has a human decision owner.
- `automated_sale_flag` is always false.
- RM utilisation is capped by configured monthly capacity.
- Negative expected-profit candidates are not selected.
- Contact permission is required before allocation.

## Management issue

KYC overdue rate is 38.09%, above the 30% internal ceiling. The breach is not hidden or relabelled.
Management should approve a risk-ranked remediation sequence and protect capacity for both KYC and
customer conversations.

## Reproducibility

Seed `20260821` regenerates the same canonical result SHA-256:

```text
61fb583b4488eaa3f07625303fa824037a8929bd8b69042d21536089bf4000c8
```

## Validation conclusion

Suitable for a controlled portfolio demonstration. Not suitable for live bank use without source
system validation, lawful-basis review, independent model validation, production experiments,
security controls, real outcome monitoring and accountable approvals.
