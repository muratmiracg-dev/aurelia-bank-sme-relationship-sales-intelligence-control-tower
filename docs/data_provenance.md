# Data Provenance

## Classification

| Class | Contents | Permitted use |
|---|---|---|
| `CONTROLLED_SYNTHETIC` | Customers, RMs, holdings, flows, interactions and campaigns | Reproducible portfolio demonstration |
| `DERIVED_ANALYTICS` | Scores, economics, worklists, validation and controls | Demonstration and review only |
| `PUBLIC_REFERENCE` | Official URLs and high-level sector context | Methodology and benchmarking context |

No real bank system, customer, employee, account, transaction, contact permission, credit file or
marketing outcome is represented.

## Official public references

- [BDDK Monthly Banking Sector Data](https://www.bddk.org.tr/BultenAylik/) provides public
  sector-level balance sheet, credit, SME credit and deposit context.
- [TCMB EVDS user documentation](https://evds2.tcmb.gov.tr/index.php?/evds/userDocs=) documents
  access to interest-rate, FX and macroeconomic series.
- [Türkiye Bankalar Birliği statistical reports](https://www.tbb.org.tr/banka-ve-sektor-bilgileri/istatistiki-raporlar)
  provide additional public sector context.

Public figures do not train the model or set legal thresholds. They are kept in
`data/reference/market_context.csv` with source date, unit, URL and usage boundary.

## Reproducibility

`make demo` rebuilds source and analytical CSVs, figures, the SQLite database and the executive
summary using seed `20260821`. The summary contains a canonical SHA-256 digest over selected key
outputs. `make manifest` hashes committed deliverables; `make verify` checks those hashes.

## Large-file policy

High-volume deterministic tables are ignored in Git and recreated locally. This keeps the public
repository reviewable while preserving the full generation and validation logic.
