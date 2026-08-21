# Security Policy

## Supported version

Only the latest `main` revision is maintained. This repository is a controlled-synthetic
portfolio demonstration and is not approved for production banking use.

## Reporting a vulnerability

Please use GitHub's private vulnerability-reporting feature. Do not include real customer,
credential, bank-secret or personal data in an issue, pull request or sample payload.

## Security boundaries

- The API is read-only and serves generated synthetic outputs.
- No authentication implementation is represented as production-ready.
- No real customer identifiers, financial records or marketing-consent records are used.
- Container examples use a non-root user, a read-only filesystem and `no-new-privileges`.
- Production deployment would require bank-approved identity, secrets, network, audit,
  encryption, privacy, model-risk and secure-SDLC controls.
