# Security Policy

This is a public portfolio repository. We take security seriously and appreciate responsible disclosure.

## Reporting a Vulnerability

If you discover a security issue in this repository or its deployed instances, please email the maintainer at the address listed on their GitHub profile. Do not open a public issue for security vulnerabilities.

## Security Practices

- **No secrets in code**: Service-account keys, API keys, passwords, and tokens must never be committed.
- **Credential storage**: Runtime secrets are resolved from Google Secret Manager and GitHub encrypted secrets.
- **CI/CD authentication**: GitHub Actions authenticates to Google Cloud via Workload Identity Federation — no long-lived service-account keys are stored.
- **Least privilege**: Cloud Run, Cloud Run Jobs, and CI/CD service accounts use the minimum IAM roles required.
- **Dependencies**: Automated dependency updates are enabled via Dependabot; security advisories are monitored.
- **In-scope assets**: The public repository, the GCS static website frontend, the Cloud Run API, and the GCP project `<GCP_PROJECT_ID>`.

## What Not to Commit

- `.env` files
- JSON service-account keys (`*-sa.json`, `credentials.json`, etc.)
- Private keys or certificates
- Personal access tokens
- Firebase/GCP project secrets

If you accidentally commit any of the above, rotate the credential immediately and notify the maintainer.
