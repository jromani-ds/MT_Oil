# Plan: Well PDF Batch Ingestion Workflow

## Overview

A monthly Cloud Run Job that queries BigQuery for all loaded `api_wellno` values, fetches the corresponding well report PDF from the Montana DNRC DataMiner, and stores each PDF in GCS at `wells/pdfs/{api_wellno}.pdf`. The job is incremental — it skips wells whose PDF already exists in GCS with matching content size, only re-downloading when the remote file size has changed.

## URL Pattern

```
https://bogapps.dnrc.mt.gov/dataminer/Wells/WellData.aspx?Name={API_WellNo}
```

The `Name` query parameter corresponds to the 14-digit `API_WellNo` (e.g., `25091212570000`).

## Key Design Decisions

| Decision    | Choice                          | Rationale                                                   |
| ----------- | ------------------------------- | ----------------------------------------------------------- |
| Fetch scope | Incremental, skip if same size  | Avoid hammering DNRC; only re-fetch when file changes       |
| Schedule    | Monthly, 3rd day at 5 AM MT     | Staggered from FracFocus (1st at 2 AM)                      |
| GCS path    | `wells/pdfs/{api_wellno}.pdf`   | Clean, flat namespace for direct lookup                     |
| Access      | Private                         | Same data-bucket ACL as other artifacts                     |
| Concurrency | Single-threaded with 1.5s delay | Be polite to DNRC; 512MiB memory is sufficient              |
| Job timeout | 12 hours (43200s)               | Covers ~20k wells at 1.5s each with headroom                |
| Scheduler   | Disabled initially              | Same pattern as FracFocus; enable manually after validation |

## Steps

### Step 1 — Create feature branch from `dev`

```bash
git checkout dev && git pull && git checkout -b feat/pdf-batch-ingestion
```

### Step 2 — New job module: `src/mt_oil/jobs/pdf_fetch.py`

Follow the `fracfocus_update.py` pattern (CLI entry point, `run()` → `main()`, `print()` logging, `try/finally` cleanup).

**Flow:**

1. Validate env vars (GCP_PROJECT_ID, BIGQUERY_DATASET, GCS_DATA_BUCKET)
2. Query BigQuery: `SELECT DISTINCT api_wellno FROM wells ORDER BY api_wellno`
3. For each `api_wellno`:
   a. Check GCS blob `wells/pdfs/{api_wellno}.pdf` — get `.size` if it exists
   b. HEAD request to DNRC URL → extract `Content-Length` (if present)
   c. If Content-Length matches GCS blob size → skip
   d. GET request → download to temp file
   e. Upload temp file to GCS blob
   f. Clean up temp file
   g. `time.sleep(1.5)`
   h. Log progress every 100 wells
4. Print summary

**Edge cases:** 404/redirect, non-PDF Content-Type, empty body, missing Content-Length header, GCS upload failure.

### Step 3 — Register CLI entry point in `pyproject.toml`

```toml
pdf-fetch = "mt_oil.jobs.pdf_fetch:main"
```

### Step 4 — Terraform Cloud Run Job + Scheduler (dev + prod)

Add `pdf_fetch_job` module (512MiB, 1 CPU, 43200s timeout) and `pdf_fetch_scheduler` module (disabled, `"0 5 3 * *"`) to both dev and prod `main.tf`. Add `pdf_fetch_job_name` output to both `outputs.tf`.

### Step 5 — Tests

`tests/test_pdf_fetch.py`: unit tests for API number formatting, skip logic, error handling; mock `urllib.request` and GCS.

### Step 6 — Verify

```bash
pytest tests/ -v
pre-commit run --all-files
```

## File Manifest

| File                                 | Action                     |
| ------------------------------------ | -------------------------- |
| `src/mt_oil/jobs/pdf_fetch.py`       | Create                     |
| `pyproject.toml`                     | Edit — add entry point     |
| `infra/environments/dev/main.tf`     | Edit — add job + scheduler |
| `infra/environments/dev/outputs.tf`  | Edit — add output          |
| `infra/environments/prod/main.tf`    | Edit — add job + scheduler |
| `infra/environments/prod/outputs.tf` | Edit — add output          |
| `tests/test_pdf_fetch.py`            | Create                     |
