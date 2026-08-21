# Model Card

## Model purpose

Prioritise human review of synthetic SME product conversations. The champion estimates activation
probability under contact; separate T-learners estimate a synthetic contact-uplift signal.

## Model inventory

| Role | Algorithm | Rationale |
|---|---|---|
| Champion | Logistic regression | Stable probabilities, auditable coefficients and reason support |
| Challenger | Histogram gradient boosting | Nonlinear benchmark |
| Uplift | Treated/control logistic T-learner | Transparent contact/no-contact contrast |

## Features

Need signal, digital engagement, relationship tenure, turnover, employees, PD, arrears,
importer/exporter flags, product, size band, sector, region and randomized treatment indicator.
Protected characteristics are neither generated nor used.

## Validation design

Campaigns are ordered by date. The earliest 80% are development observations; the latest 20% are
an out-of-time-style synthetic validation set from 2 May through 5 August 2026.

## Verified champion result

| Metric | Result |
|---|---:|
| Observations | 3,200 |
| Activation rate | 29.09% |
| ROC AUC | 0.7153 |
| PR AUC | 0.4945 |
| Brier score | 0.1820 |
| Log loss | 0.5426 |
| Top-decile lift | 2.073x |

## Limitations

- Synthetic outcomes are constructed from known functions and cannot demonstrate production
  generalisation.
- T-learner estimates are sensitive to overlap, calibration and treatment-assignment quality.
- Reason codes are prioritisation evidence, not causal explanations of customer intent.
- Region and SME size diagnostics do not replace legal fairness or discrimination assessment.
- Macroeconomic, channel-cost and competitive-offer dynamics are simplified.

## Prohibited use

Automated sale, pricing, credit approval, adverse action, customer restriction, speculative FX
recommendation, marketing without a lawful basis or contact without authorised review.

## Monitoring proposal

Monthly discrimination/calibration, score and feature drift, uplift-decile stability, selection
rates, suppression mix, override outcomes, complaints, conversion, realized economics, RM capacity
and KYC/AML/credit control breaches. Production thresholds require independent approval.
