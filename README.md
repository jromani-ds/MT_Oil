# MT Oil Analytics Platform

A professional full-stack application for Oil & Gas data analysis, featuring advanced Decline Curve Analysis (DCA), economic modeling (NPV, ROI), and an interactive geospatial dashboard.

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
