# MT Oil Analytics Platform

[![License](https://img.shields.io/github/license/jromani-ds/MT_Oil)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/jromani-ds/MT_Oil/ci.yml?branch=dev&label=CI)](https://github.com/jromani-ds/MT_Oil/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-blue?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev/)
[![GCP](https://img.shields.io/badge/GCP-Cloud_Run-blue?logo=google-cloud)](https://cloud.google.com/)

A professional full-stack application for Oil & Gas data analysis, featuring advanced Decline Curve Analysis (DCA), economic modeling (NPV, ROI), and an interactive geospatial dashboard.

**Try it live:**

- Dev: https://mt-oil-mt-oil-dashboard-dev.storage.googleapis.com/index.html
- Prod: https://mt-oil-mt-oil-dashboard.storage.googleapis.com/index.html

## Overview

| Item                             | Status                  |
| -------------------------------- | ----------------------- |
| FastAPI backend                  | Live                    |
| React + Vite + Tailwind frontend | Live                    |
| GCP dev + prod deployments       | Live                    |
| BigQuery data warehouse          | Seeded                  |
| GCS static frontend hosting      | Live                    |
| Public API rate limiting         | Enabled                 |
| Cloud Scheduler                  | Enabled in dev and prod |

## Architecture

```
frontend/          React + Vite + TypeScript + Tailwind CSS
src/mt_oil/        FastAPI backend, domain logic, data loaders
tests/             pytest + FastAPI TestClient; frontend Vitest suite
infra/             Terraform modules and environment configurations
scripts/           One-off data seed and operational scripts
.github/           GitHub Actions CI/CD with Workload Identity Federation
```

- **Backend**: Python (FastAPI) with in-memory Pandas analytics, BigQuery loaders, and an optional scikit-learn forecasting pipeline.
- **Frontend**: TypeScript (React + Vite) with `react-leaflet` maps and `recharts` visualizations.
- **Data**: Montana DNRC public well / production data in BigQuery; FracFocus registry loaded by a Cloud Run Job.
- **Hosting**: Cloud Run (API) and Cloud Storage static website (frontend).

## Live Environments

| Environment | Branch | BigQuery Dataset | GCS Static Site Bucket |
| ----------- | ------ | ---------------- | ---------------------- |
| Dev         | `dev`  | `mt_oil_dev`     | `mt-oil-dashboard-dev` |
| Prod        | `main` | `mt_oil_prod`    | `mt-oil-dashboard`     |

The frontend is served from `/index.html` on the GCS static website endpoint (the bucket root returns an object listing).

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 22+

### 1. Backend Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Run tests
pytest tests/

# Start the API Server
uvicorn src.mt_oil.api.main:app --reload
```

_The API will run at `http://localhost:8000`._

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run test        # run the Vitest suite
npm run build       # production build
npm run dev         # start the dev server
```

_The dashboard will run at `http://localhost:5173`._

## Key Features

### Decline Curve Analysis (DCA)

The system fits decline curves to historical production data using `scipy.optimize`:

- **Arps**: Standard hyperbolic decline.
- **Modified Arps**: Hyperbolic with exponential cutoff.
- **Duong**: Logic for unconventional fractured reservoirs.

### Economic Modeling

Calculates key financial metrics based on DCA forecasts:

- **NPV**: Net Present Value (discounted cash flow).
- **ROI**: Return on Investment.
- **Payout**: Time to recover CAPEX.
- **Parameters**: Handles price differentials, taxes (Ad Valorem, Severance), and variable operating costs.

## Development

### Code Quality

- **Formatting**: `black` (Python), `prettier` (frontend).
- **Linting**: `ruff` (Python), `eslint` (TypeScript).
- **Hooks**: `pre-commit` runs these checks automatically.

### Running Tests

```bash
# Backend
pytest tests/

# Frontend
cd frontend
npm run test
```

### Deployment Flow

1. Cut a feature branch from `dev`.
2. Open a PR to `dev`.
3. After `dev` passes CI, open a PR from `dev` to `main` for production.

Direct pushes to `dev` and `main` are blocked by branch protection.

## Operations

### Seeding BigQuery Data

The backend loads well headers and production history from BigQuery. This is a
manual, one-time seed step run from a developer workstation.

Two datasets are used so dev and prod stay isolated, but the data itself is kept
identical by seeding both from the same source files in GCS.

#### Prerequisites

1. Download the Montana DNRC source files to the repository root:

   - `MT_HistoricalWellList.tab`
   - `MT_HistoricalWellProduction.tab`

2. Ensure you have authenticated to GCP (`gcloud auth application-default login`).

#### First-time seed (upload source files to GCS)

```bash
python scripts/seed_bigquery.py \
  --project <GCP_PROJECT_ID> \
  --gcs-bucket <GCS_BUCKET_NAME> \
  --all-datasets \
  --upload-source
```

This uploads the `.tab` files to `gs://<GCS_BUCKET_NAME>/raw/seed/` and then
loads the same data into both `mt_oil_dev` and `mt_oil_prod`. After uploading,
the script verifies that both datasets have identical row counts.

#### Re-seeding from existing GCS files

```bash
python scripts/seed_bigquery.py \
  --project <GCP_PROJECT_ID> \
  --gcs-bucket <GCS_BUCKET_NAME> \
  --all-datasets
```

#### Single-dataset seed (legacy behavior)

```bash
python scripts/seed_bigquery.py \
  --project <GCP_PROJECT_ID> \
  --dataset mt_oil_dev
```

### FracFocus Updates

Cloud Scheduler is enabled and triggers the FracFocus and PDF fetch jobs monthly. For ad-hoc runs, trigger manually:

```bash
gcloud run jobs execute mt-oil-fracfocus-dev --region=us-central1 --project=<GCP_PROJECT_ID>
gcloud run jobs execute mt-oil-fracfocus-prod --region=us-central1 --project=<GCP_PROJECT_ID>
```

Each run downloads the latest FracFocus registry, aggregates proppant/fluid totals by API, loads the result into BigQuery, and archives the raw ZIP to the project's GCS data bucket under `raw/fracfocus/`.

### Configuration

Runtime configuration is externalized through environment variables; see `src/mt_oil/config.py`. Notable settings:

| Variable       | Purpose                                       | Default           |
| -------------- | --------------------------------------------- | ----------------- |
| `RATE_LIMIT`   | Per-IP rate limit string for read endpoints   | `60/minute`       |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins      | `FRONTEND_URL`    |
| `MODEL_PATH`   | Path or `gs://` URL for the ML model artifact | `rf_model.joblib` |

## Security & Cost

- **Public API**: limited via SlowAPI (`60/minute` read, `5/minute` training).
- **Cost cap**: ~$10/month hard ceiling; Cloud Run `max_scale = 1`, CPU throttled, 512 MiB–1 GiB memory.
- **No committed secrets**: Authentication uses Workload Identity Federation and Google Secret Manager.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on branching, commit messages, and PRs.
