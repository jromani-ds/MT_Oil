# MT Oil Analytics — Agent Context

This document provides context for AI coding agents working on this repository.

## Project Overview

Full-stack Oil & Gas analytics application built as a public portfolio / showcase project. It analyzes Montana DNRC public production and completion data to provide interactive well mapping, Decline Curve Analysis (DCA), economic modeling, and machine-learning forecasts.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                              Public Repo                                │
├────────────────────────────────────────────────────────────────────────┤
│  frontend/          React + Vite + TypeScript + Tailwind CSS          │
│  src/mt_oil/        FastAPI backend, domain logic, data loaders        │
│  tests/             pytest + FastAPI TestClient                        │
│  infra/             Terraform modules and environment configurations   │
│  scripts/           One-off data seed and operational scripts          │
│  .github/           GitHub Actions CI/CD with Workload Identity      │
└────────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  GCS static website    Cloud Run            BigQuery + GCS
  (static frontend)     (FastAPI backend)    (data warehouse + lake)

> Note: Firebase Hosting was replaced by a Cloud Storage static website bucket because the Firebase Management API was not provisionable in this GCP project under Terraform. The unused `firebase_hosting` Terraform module has been removed from the repository.
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn, Pandas, NumPy, SciPy, scikit-learn, SlowAPI
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Recharts, react-leaflet, Vitest
- **Data**: BigQuery (analytical warehouse), Google Cloud Storage (data lake / model artifacts)
- **Compute**: Cloud Run (API), Cloud Run Jobs (monthly FracFocus ETL)
- **IaC**: Terraform with GCS remote state backend
- **CI/CD**: GitHub Actions using Workload Identity Federation (no leaked keys)

## Repository Rules

1. **Never commit secrets, keys, or credentials.** All runtime secrets are resolved from Google Secret Manager / GitHub encrypted variables; authentication in CI uses Workload Identity Federation.
2. **Branch workflow**: always cut a feature branch from `dev`, open PR to `dev`, then PR `dev` → `master`. Direct pushes to `dev` and `master` are blocked by branch protection.
3. **Pre-commit hooks must pass**: `pre-commit run --all-files` before any PR.
4. **Tests must pass**: `pytest tests/` for backend; `npm run lint && npm run build && npm run test` for frontend.
5. **Terraform**: never apply locally to shared environments; use CI/CD or review `terraform plan` carefully.

## Common Commands

```bash
# Backend
cd /Users/josephromani/MT_Oil
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/
uvicorn src.mt_oil.api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
npm run test
npm run build

# Pre-commit
pre-commit run --all-files

# Terraform (bootstrap is run once locally with elevated permissions)
cd infra/environments/dev
terraform init \
  -backend-config="bucket=<GCP_PROJECT_ID>-tfstate" \
  -backend-config="prefix=dev/terraform.tfstate"
terraform plan -var="project_id=<GCP_PROJECT_ID>" -var="region=<REGION>" -var="api_image=<IMAGE_URL>"
terraform apply -var="project_id=<GCP_PROJECT_ID>" -var="region=<REGION>" -var="api_image=<IMAGE_URL>"
```

## Important Code Conventions

- Backend source lives at `src/mt_oil/`. Always use the package namespace.
- Environment-specific configuration must be externalized (env vars, Secret Manager). Avoid hardcoded paths and URLs. `RATE_LIMIT` controls the default per-IP read limit.
- The backend reads well/production data from **BigQuery**, not from local `.tab` files, in deployed environments.
- Model artifact (`rf_model.joblib`) is loaded from **GCS**; do not commit it.

## Infrastructure Conventions

- **Project-agnostic IaC**: never hardcode GCP Project IDs, regions, zones, or account IDs in Terraform or GitHub Actions. Use variables, data sources, and WIF.
- **Variables + examples**: define environment-specific inputs as variables in `variables.tf` and provide a `terraform.tfvars.example` for each environment.
- **Dynamic naming**: derive globally unique resource names (GCS buckets, Artifact Registry repos) from `var.project_id` or a `random_id` suffix.
- **Project metadata**: use `data "google_project"` rather than hardcoding project numbers.
- **Backend flexibility**: keep Terraform backend blocks empty by default; configure remote state via `-backend-config`.
- **Required APIs**: explicitly enable GCP APIs with `google_project_service` and `disable_on_destroy = false`.
- **No service account JSON keys in CI**: use Workload Identity Federation and GitHub variables/secrets for any per-project values.

## GitHub Variables

The reusable `deploy.yml` workflow reads per-project configuration from repository variables (Settings > Secrets and variables > Actions > Variables). Configure these before running CI/CD in a new GCP project:

| Name                             | Description                                               | Example                                                                                                              |
| -------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `GCP_PROJECT_ID`                 | GCP project ID to deploy into                             | `<GCP_PROJECT_ID>`                                                                                                   |
| `GCP_REGION`                     | Primary GCP region for Cloud Run, Artifact Registry, etc. | `us-central1`                                                                                                        |
| `GCP_SERVICE_ACCOUNT_EMAIL`      | Workload Identity service account used by GitHub Actions  | `github-actions@<GCP_PROJECT_ID>.iam.gserviceaccount.com`                                                            |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full Workload Identity Provider resource name             | `projects/<GCP_PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider` |

Environment-specific inputs (bucket names, locations, alert email, etc.) are set in Terraform (`terraform.tfvars` or via `-var` flags in CI). The current CI passes `project_id`, `region`, and `api_image` directly; remaining variables can keep their generic defaults or be overridden per environment.

## Cost Guardrails

This is a personal demo with a strict ~$10/month budget. Key limits:

- Cloud Run: `max_scale = 1`, CPU throttled, 512 MiB–1 GiB memory.
- BigQuery: production table partitioned by `Rpt_Date` and clustered by `API_WellNo`.
- GCP budget alert set at $5/month.
- No long-running VMs, no dedicated load balancers, no Vertex AI training.

## Gotchas

- `src/mt_oil/data/loader.py` historically downloads large ZIPs on startup. In the cloud deployment, data is loaded from BigQuery; the downloader is only used by the optional monthly FracFocus job.
- The FracFocus Cloud Run Job now archives the raw downloaded ZIP to `raw/fracfocus/` in the GCS data bucket before cleanup.
- A GCS lifecycle rule deletes objects under the `models/` prefix after 180 days to keep model-artifact storage from growing under the tight budget cap.
- Frontend API client base URL is set at build time via `VITE_API_BASE_URL`.
- Local development still uses the local `.tab`/`.csv` files for fast iteration.
- The public API is rate-limited with SlowAPI; configure `RATE_LIMIT` to change the default read limit.

## Deployment Environments

| Environment | Branch   | Cloud Run Service | BigQuery Dataset | GCS Static Site Bucket |
| ----------- | -------- | ----------------- | ---------------- | ---------------------- |
| Dev         | `dev`    | `mt-oil-api-dev`  | `mt_oil_dev`     | `mt-oil-dashboard-dev` |
| Prod        | `master` | `mt-oil-api-prod` | `mt_oil_prod`    | `mt-oil-dashboard`     |
