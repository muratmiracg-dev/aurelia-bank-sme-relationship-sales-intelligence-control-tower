# Operations Runbook

## Local generation

```bash
python -m pip install -e ".[dev]"
make demo
```

Expected outcomes include 3,200 customers, 661 capacity-allocated conversations, 14/14 passing
data-quality controls and one visible KYC-backlog management breach.

## Quality gates

```bash
make lint
make coverage
make manifest
make verify
```

Stop delivery if data quality fails, any automated sale appears, a suppressed record enters the
worklist, coverage is below 90%, the digest changes without an explained code/config change or the
manifest does not verify.

## API

```bash
uvicorn aurelia_sme_sales.api:app --host 127.0.0.1 --port 8000
```

The API requires generated artifacts. It is read-only and synthetic. Production identity,
authorisation, rate limits, audit, encryption, secrets and observability are not implemented.

## Troubleshooting

- Missing output: run `make demo` from the repository root.
- Digest change: verify seed, package versions, configuration and code diff.
- Model threshold breach: review validation output; do not lower the limit to force a pass.
- KYC control breach: keep it visible and follow the remediation owner/action in the control table.
- Workbook/deck/report mismatch: regenerate management artifacts from the same summary cutoff.
