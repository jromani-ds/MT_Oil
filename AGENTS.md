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

> Note: Firebase Hosting was replaced by a Cloud Storage static website bucket because the Firebase Management API was not provisionable in this GCP project under Terraform.
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn, Pandas, NumPy, SciPy, scikit-learn
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, Recharts, react-leaflet
- **Data**: BigQuery (analytical warehouse), Google Cloud Storage (data lake / model artifacts)
- **Compute**: Cloud Run (API), Cloud Run Jobs (monthly FracFocus ETL)
- **IaC**: Terraform with GCS remote state backend
- **CI/CD**: GitHub Actions using Workload Identity Federation (no leaked keys)

## Repository Rules

1. **Never commit secrets, keys, or credentials.** All runtime secrets are resolved from Google Secret Manager / GitHub encrypted variables; authentication in CI uses Workload Identity Federation.
2. **Branch workflow**: always cut a feature branch from `dev`, open PR to `dev`, then PR `dev` → `master`. Direct pushes to `dev` and `master` are blocked by branch protection.
3. **Pre-commit hooks must pass**: `pre-commit run --all-files` before any PR.
4. **Tests must pass**: `pytest tests/` for backend; `npm run lint && npm run build` for frontend.
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
npm run build

# Pre-commit
pre-commit run --all-files

# Terraform (bootstrap is run once locally with elevated permissions)
cd infra/environments/dev
terraform init
terraform plan
terraform apply
```

## Important Code Conventions

- Backend source lives at `src/mt_oil/`. Always use the package namespace.
- Environment-specific configuration must be externalized (env vars, Secret Manager). Avoid hardcoded paths and URLs.
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

## Cost Guardrails

This is a personal demo with a strict ~$10/month budget. Key limits:

- Cloud Run: `max_scale = 1`, CPU throttled, 512 MiB–1 GiB memory.
- BigQuery: production table partitioned by `Rpt_Date` and clustered by `API_WellNo`.
- GCP budget alert set at $5/month.
- No long-running VMs, no dedicated load balancers, no Vertex AI training.

## Gotchas

- `src/mt_oil/data/loader.py` historically downloads large ZIPs on startup. In the cloud deployment, data is loaded from BigQuery; the downloader is only used by the optional monthly FracFocus job.
- Frontend API client base URL is set at build time via `VITE_API_BASE_URL`.
- Local development still uses the local `.tab`/`.csv` files for fast iteration.

## Deployment Environments

| Environment | Branch   | Cloud Run Service | BigQuery Dataset | GCS Static Site Bucket |
| ----------- | -------- | ----------------- | ---------------- | ---------------------- |
| Dev         | `dev`    | `mt-oil-api-dev`  | `mt_oil_dev`     | `mt-oil-dashboard-dev` |
| Prod        | `master` | `mt-oil-api-prod` | `mt_oil_prod`    | `mt-oil-dashboard`     |
