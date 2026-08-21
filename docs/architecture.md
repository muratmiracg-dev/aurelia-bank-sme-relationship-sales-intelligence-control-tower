# Architecture

## Design objective

The platform separates raw relationship evidence, predictive analytics, economics, policy
gates and human execution so each layer can be challenged independently.

```text
Controlled synthetic sources
  -> Customer 360 and product-need features
  -> Temporal propensity and T-learner uplift
  -> Product economics and RAROC-style bridge
  -> Permission / KYC / AML / credit / suitability gates
  -> Customer-level next-best conversation
  -> RM capacity and worklist
  -> Controls, API, BI, Excel and executive reporting
```

## Components

| Component | Responsibility | Primary output |
|---|---|---|
| `generator.py` | Deterministic customers, RMs, flows, holdings, interactions and campaigns | Source CSVs |
| `features.py` | Customer 360, relationship depth, wallet share and product need | Customer/candidate features |
| `propensity.py` | Temporal champion/challenger, T-learner uplift and reasons | Scores and validation |
| `economics.py` | Product notional, funding, expected loss, capital and profit | Economics bridge |
| `decisioning.py` | Suppressions, score, customer deduplication and RM capacity | Worklist and funnel |
| `controls.py` | Data quality, conduct diagnostics and management limits | Control register |
| `reporting.py` | Offline management figures | PNG evidence |
| `pipeline.py` | Orchestration, CSV, SQLite, summary and digest | Reproducible pack |
| `api.py` | Read-only access to generated outputs | FastAPI service |

## Trust boundaries

1. Synthetic source generation is isolated from analytical decisions.
2. Campaign labels are used only for model development and temporal validation.
3. Risk and conduct gates are configuration-driven and run after scoring.
4. Capacity allocation cannot override a suppression.
5. Every selected task retains evidence, economics, reason codes and a human owner.
6. The API is read-only and cannot execute customer contact.

## Deployment boundary

Docker and Compose demonstrate packaging, not production approval. A live banking deployment
would additionally require identity and access management, customer-secret controls, encryption,
data retention, change approval, independent model validation, monitoring, incident response,
business continuity, audit evidence and integration with authoritative CRM, KYC, AML, credit and
product systems.
