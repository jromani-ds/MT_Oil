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

- Python 3.11+
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
- **Duong**: Logic for unconventional fractured reservoirs.

### Economic Modeling

Calculates key financial metrics based on DCA forecasts:

- **NPV**: Net Present Value (discounted cash flow).
- **ROI**: Return on Investment.
- **Payout**: Time to recover CAPEX.
- **Parameters**: Handles price differentials, taxes (Ad Valorem, Severance), and variable operating costs.

### Agentic Wellfile Analysis

Uses a [Google ADK](https://google.github.io/adk-docs/) agent powered by
Gemini 2.5 Flash Lite to extract completion parameters from wellfile PDFs
hosted on the Montana DNRC file server. Results are cached in a BigQuery
table for fast subsequent lookups. The agent computes derived intensity
metrics (proppant lbs/ft, fluid bbls/ft) from extracted specs.

- **BigQuery cache**: repeated requests bypass the LLM entirely.
- **Fallback PDF source**: state DNRC server (primary) / GCS (cached copy).
- **Exposed via**: `POST /agent/wellfile`.

### GIS Layers

Interactive geospatial overlays rendered on the Leaflet map, sourced from
Montana MBOGC shapefiles processed into GeoJSON:

- **WellPaths** — directional / horizontal wellbore path lines
- **WellSurface** — well surface point locations
- **FieldBoundaries** — delineated field boundary polygons
- **Units** — enhanced recovery unit and gas storage unit polygons

Refreshed monthly by the `gis_update` Cloud Run Job.

## Repository Layout

For detailed documentation on each area, see the per-directory READMEs:

- [`frontend/`](frontend/) — React dashboard ([README](frontend/README.md))
- [`src/mt_oil/`](src/mt_oil/) — FastAPI backend ([README](src/mt_oil/README.md))
- [`infra/`](infra/) — Terraform infrastructure ([README](infra/README.md))
- [`scripts/`](scripts/) — Data seeding & GIS processing ([README](scripts/README.md))
- [`tests/`](tests/) — pytest suite
- [`.github/`](.github/) — GitHub Actions CI/CD

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

### Monthly Cloud Run Jobs

Cloud Scheduler triggers four jobs on a monthly cadence. Trigger ad-hoc runs with:

```bash
# FracFocus — download registry, aggregate by API, load to BigQuery
gcloud run jobs execute mt-oil-fracfocus-dev --region=us-central1 --project=<GCP_PROJECT_ID>

# PDF Fetch — download wellfile PDFs from state DNRC, store in GCS
gcloud run jobs execute mt-oil-pdf-fetch-dev --region=us-central1 --project=<GCP_PROJECT_ID>

# GIS Update — refresh shapefile-to-GeoJSON layers in GCS
gcloud run jobs execute mt-oil-gis-update-dev --region=us-central1 --project=<GCP_PROJECT_ID>

# Batch Wellfile Extraction — runs Gemini extraction on all horizontal wells
gcloud run jobs execute mt-oil-batch-wellfile-dev --region=us-central1 --project=<GCP_PROJECT_ID>
```

| Job              | Schedule             | Memory | Description                                                                 |
| ---------------- | -------------------- | ------ | --------------------------------------------------------------------------- |
| `fracfocus`      | 1st day, 2 AM MT     | 4 GiB  | Download FracFocus, aggregate proppant/fluid, archive ZIP, load to BigQuery |
| `pdf-fetch`      | 3rd day, 5 AM MT     | 2 GiB  | Download wellfile PDFs from state DNRC to GCS (incremental)                 |
| `gis-update`     | 5th day, midnight MT | 4 GiB  | Download shapefiles, reproject to GeoJSON, upload to GCS                    |
| `batch-wellfile` | (on-demand)          | 2 GiB  | Gemini extraction of completion params from cached PDFs                     |

### Configuration

Runtime configuration is externalized through environment variables; see `src/mt_oil/config.py`. Notable settings:

| Variable                      | Purpose                                       | Default                            |
| ----------------------------- | --------------------------------------------- | ---------------------------------- |
| `RATE_LIMIT`                  | Per-IP rate limit string for read endpoints   | `60/minute`                        |
| `CORS_ORIGINS`                | Comma-separated allowed frontend origins      | `FRONTEND_URL`                     |
| `MODEL_PATH`                  | Path or `gs://` URL for the ML model artifact | `rf_model.joblib`                  |
| `ENABLE_LOCAL_DATA`           | Use local `.tab` files vs. BigQuery           | `true`                             |
| `GCS_DATA_BUCKET`             | GCS bucket for data / model artifacts         | —                                  |
| `BIGQUERY_DATASET`            | BigQuery dataset ID                           | —                                  |
| `VERTEX_AI_LOCATION`          | Vertex AI region (Gemini)                     | `us-central1`                      |
| `VERTEX_AI_MODEL`             | Vertex AI model for wellfile extraction       | `gemini-2.5-flash-lite`            |
| `WELLFILE_PARSED_TABLE`       | BigQuery table for parsed wellfile cache      | `wellfile_parsed_metadata`         |
| `WELLFILE_STATE_URL_TEMPLATE` | URL template for state DNRC wellfile PDFs     | `https://bogfiles.dnrc.mt.gov/...` |

## Security & Cost

- **Public API**: limited via SlowAPI (`60/minute` read, `5/minute` training).
- **Cost cap**: ~$10/month hard ceiling; Cloud Run `max_scale = 1`, CPU throttled, 2 GiB (API) / 4 GiB (jobs).
- **No committed secrets**: Authentication uses Workload Identity Federation and Google Secret Manager.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on branching, commit messages, and PRs.
