# MT Oil — GCP Deployment Completion Plan

_Living plan incorporating current decisions: dev-first, full data seed, public API, GCS static website endpoint, $10/month hard cap, alert email `joseph.romani@gmail.com`. Keep `master` as the production trigger for now, with a backlog item to migrate to `main` in the future._

## Decisions

| Item              | Decision                                                                                  |
| ----------------- | ----------------------------------------------------------------------------------------- |
| GCP project       | `my-project-1508887546225` (billing-enabled)                                              |
| Bootstrap status  | **Verified**                                                                              |
| First environment | **Dev first** (completed; prod also deployed)                                             |
| Data seeding      | **Full seed completed** in both `mt_oil_dev` and `mt_oil_prod`                            |
| API access        | Fully public (`allUsers`) with future auth in backlog                                     |
| Frontend serving  | GCS static website endpoint; root `/` returns bucket listing, so use `/index.html`        |
| Budget cap        | $10/month hard cap; alert email `joseph.romani@gmail.com`                                 |
| Primary branch    | `master` remains the prod trigger for now; add backlog item to migrate to `main`          |
| Cloud Scheduler   | **Disabled** in both envs because App Engine provisioning fails with a GCP internal error |

## Current Status

- [x] FastAPI backend with local + BigQuery data loaders
- [x] React + Vite + Tailwind frontend
- [x] Terraform-managed dev and prod environments
- [x] GitHub Actions CI/CD with Workload Identity Federation
- [x] Cloud Run service, Cloud Run Job, BigQuery, GCS scaffolding
- [x] Cloud Scheduler module created but currently disabled
- [x] Bootstrap resources verified and CI service account permissions sufficient
- [x] Full data uploaded to BigQuery in `mt_oil_dev` and `mt_oil_prod`
- [x] Model artifact uploaded to GCS in dev and prod buckets
- [x] Dev and prod deployments complete and validated
- [x] Health endpoint, CORS, frontend `/index.html`, and API calls verified
- [x] FracFocus Cloud Run Job fixed and verified in dev and prod
- [x] Prod monitoring module applied during prod deploy
- [ ] Project-agnostic IaC refactor partially complete (Phase 7)
- [ ] Cloud Scheduler re-enablement blocked by GCP App Engine internal error

## Phase 0 — Bootstrap Verification

Before any CI deployment, confirm the following exist. If any are missing, run `infra/bootstrap/bootstrap.sh` once locally as a project owner. All items are now verified in the target project.

| Resource                   | Verification command                                                                                                                   |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Terraform state bucket     | `gsutil ls -b gs://my-project-1508887546225-tfstate`                                                                                   |
| Artifact Registry repo     | `gcloud artifacts repositories describe mt-oil-api --location=us-central1`                                                             |
| CI/CD service account      | `gcloud iam service-accounts describe github-actions@my-project-1508887546225.iam.gserviceaccount.com`                                 |
| Workload Identity Pool     | `gcloud iam workload-identity-pools describe github-actions-pool --location=global`                                                    |
| Workload Identity Provider | `gcloud iam workload-identity-pools providers describe github-provider --location=global --workload-identity-pool=github-actions-pool` |
| Billing & budget alerts    | Cloud Console → Billing                                                                                                                |

## Phase 1 — Completed Pre-Deploy Fixes

All Phase 1 items have been implemented or addressed with a documented workaround.

### Backend

- [x] Fix GCS model save logic in `src/mt_oil/models/pipeline.py` (model is now uploaded directly from seed scripts; runtime save/load path remains functional).
- [x] Wire `CORS_ORIGINS` to `FRONTEND_URL` and strip trailing slashes in `src/mt_oil/config.py`.
- [x] Replace `print()` with structured logging driven by `LOG_LEVEL` in `src/mt_oil/config.py`.
- [x] Improve `/health` so it returns BigQuery/GCS connectivity status in deployed mode.

### Infrastructure

- [x] Bootstrap resources and CI service account permissions verified.
- [x] Cloud Run module exposes `concurrency` and `timeout_seconds` variables.
- [x] Cloud Run Job module exposes `timeout_seconds` and `max_retries` variables.
- [x] Root-level `outputs.tf` for dev and prod exports API URL and frontend website URL.
- [x] `deploy.yml` prints the correct GCS static website endpoint (`.../index.html`).
- [ ] **Cloud Scheduler / App Engine**: attempted; blocked by a persistent GCP internal error. Disabled scheduler module as a workaround.

### Repository / Branch Hygiene

- [x] Keep `master` as the production trigger; `main` migration deferred to backlog.
- [x] Pre-commit `no-commit-to-branch` consistent with protected `dev` and `master` branches.

## Phase 2 — Data Seeding

Both dev and prod datasets were seeded with the full local data, and the model artifact was uploaded to both GCS buckets.

```bash
# Example commands used (already completed)
python scripts/seed_bigquery.py \
  --project my-project-1508887546225 \
  --dataset mt_oil_dev

python scripts/seed_bigquery.py \
  --project my-project-1508887546225 \
  --dataset mt_oil_prod

# Model artifacts
gsutil cp rf_model.joblib \
  gs://my-project-1508887546225-mt-oil-dev/models/rf_model.joblib
gsutil cp rf_model.joblib \
  gs://my-project-1508887546225-mt-oil-prod/models/rf_model.joblib
```

Validation status: `wells`, `production_monthly`, and `frac_focus` tables exist in both datasets.

## Phase 3 — Dev Deployment

- [x] Phase 1 fixes merged into `dev` (PRs #27–#31, #33).
- [x] `.github/workflows/deploy.yml` (dev job) successful.
- [x] API image built and pushed to Artifact Registry.
- [x] Terraform applied dev environment.
- [x] Frontend built with dev API URL and synced to dev GCS bucket.
- [x] `GET https://mt-oil-api-dev-edkxkxbaeq-uc.a.run.app/health` returns 200.
- [x] CORS preflight and frontend `/index.html` load verified.

## Phase 4 — Full Data Seed + Prod Deployment

- [x] Full prod seed completed.
- [x] Prod model artifact uploaded.
- [x] `dev` → `master` promotion PRs (#32, #34) merged.
- [x] `.github/workflows/deploy.yml` (prod job) successful.
- [x] Prod monitoring module applied.
- [x] `GET https://mt-oil-api-prod-edkxkxbaeq-uc.a.run.app/health` returns 200.
- [x] Prod frontend loads from `https://my-project-1508887546225-mt-oil-dashboard.storage.googleapis.com/index.html`.

## Phase 5 — Post-Deploy Backlog

| Item                                                                      | Priority |
| ------------------------------------------------------------------------- | -------- |
| Migrate primary branch from `master` to `main`                            | Medium   |
| Add rate limiting to public API (e.g., SlowAPI)                           | Medium   |
| Add authentication (IAP or API key) for a non-public variant              | Low      |
| Add frontend tests and error boundary                                     | Medium   |
| Add `/train` status/result endpoint                                       | Low      |
| Add lifecycle rule for old model artifacts in GCS                         | Low      |
| Remove dead `firebase_hosting` Terraform module                           | Low      |
| Update `README.md` and `AGENTS.md` status badges / runbook                | Medium   |
| Re-enable Cloud Scheduler if App Engine provisioning issue is resolved    | Medium   |
| Tighten `pull_ff_data()` to read only `FracFocusRegistry*.csv` files      | Low      |
| Fix `pandas-gbq` warning in FracFocus load                                | Low      |
| Address GitHub Actions Node.js 20 deprecation warnings                    | Low      |
| Archive raw FracFocus ZIP in `fracfocus_update.py` after processing       | Low      |
| Review/fix runtime GCS model save path in `src/mt_oil/models/pipeline.py` | Low      |

## Phase 6 — Branch Migration to `main` (Future)

When ready to move from `master` to `main`:

1. Create `main`, set it as the default branch in GitHub.
2. Update `.github/workflows/deploy.yml` prod trigger to `main`.
3. Update `.github/workflows/ci.yml` PR target branches to include `main`.
4. Update `.pre-commit-config.yaml` to block `main` (and/or replace `master`).
5. Retire `master` after a transition period.

## Phase 7 — Project-Agnostic IaC Refactor (Backlog)

Goal: make the repository fully reusable by other GCP projects while keeping the current `my-project-1508887546225` deployment working.

### System Instruction

When generating, reviewing, or refactoring GCP Infrastructure-as-Code (IaC) for this repository, enforce total project agnosticism by requiring parameterization, dynamic naming, and zero hardcoded secrets.

- Never hardcode GCP Project IDs, Regions, Zones, or Account IDs.
- Define all environment-specific inputs as uninitialized variables in `variables.tf` and provide a corresponding `terraform.tfvars.example` file.
- Derive globally unique resource names (GCS buckets, Artifact Registries) from `var.project_id` or a `random_id` suffix.
- Fetch project metadata such as the numerical Project Number using `data "google_project"` rather than hardcoding it.
- Keep backend state blocks empty by default so local execution succeeds without pre-existing remote buckets; remote state should be configured via `terraform init -backend-config="..."`.
- Explicitly enable required GCP APIs using `google_project_service` resources with `disable_on_destroy = false`.
- In CI/CD workflows, avoid long-lived service account JSON keys; use Workload Identity Federation (`actions/checkout@v4`, `google-github-actions/auth@v2`), and rely on GitHub repository secrets/variables for any per-project values.

### Phase 7 Tasks

| #   | Task                                                                                                                                                                                                        | Status         |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| 1   | **Enforce no new hardcoded project IDs / secrets.** Conventions documented in `AGENTS.md`; new changes must use variables, data sources, or WIF.                                                            | Done           |
| 2   | **Refactor existing hardcoded IDs.** Replace literal `my-project-1508887546225`, region, zone, and account IDs in `infra/` and `.github/workflows/` with variables + `terraform.tfvars` / GitHub variables. | Partially done |
|     | - `infra/environments/dev/main.tf` backend bucket                                                                                                                                                           | Done           |
|     | - `infra/environments/prod/main.tf` backend bucket                                                                                                                                                          | Done           |
|     | - `.github/workflows/deploy.yml` project ID, region, service account, WIF provider, Artifact Registry URL                                                                                                   | Pending        |
|     | - `infra/bootstrap/bootstrap.sh` project ID and region defaults                                                                                                                                             | Pending        |
|     | - `scripts/seed_bigquery.py` default project/dataset                                                                                                                                                        | Pending        |
| 3   | **Add `terraform.tfvars.example`** files for dev and prod with all required variables documented.                                                                                                           | Done           |
| 4   | **Add GitHub variables documentation** for the workflow inputs currently hardcoded in `deploy.yml`.                                                                                                         | Pending        |
| 5   | **Validate reuse.** Fork a fresh GCP project, populate `terraform.tfvars`, set GitHub variables, and confirm a full deploy works.                                                                           | Pending        |

## Cost Model

| Service                         | Configuration                          | Approx. Monthly Cost               |
| ------------------------------- | -------------------------------------- | ---------------------------------- |
| Cloud Run (dev + prod)          | `max_scale = 1`, CPU throttled, 1 GiB  | Mostly $0 when idle                |
| Cloud Run Jobs (FracFocus)      | Monthly run, 4 GiB / 2 CPU for minutes | <$0.10                             |
| Cloud Storage (frontend + data) | ~1 GB standard class                   | <$0.05                             |
| BigQuery storage                | ~500 MB–1 GB                           | <$0.05                             |
| BigQuery queries                | UI-scoped reads                        | Usually within free tier           |
| Cloud Monitoring                | Uptime checks + alert policies         | Usually within free tier           |
| Cloud Scheduler                 | 0 active jobs (disabled)               | $0                                 |
| Artifact Registry               | Small container images                 | <$0.10                             |
| **Total**                       |                                        | **<$5 typical, <$10 hard ceiling** |

## Live Endpoints

| Environment | API                                               | Frontend (use `/index.html`)                                                              |
| ----------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Dev         | `https://mt-oil-api-dev-edkxkxbaeq-uc.a.run.app`  | `https://my-project-1508887546225-mt-oil-dashboard-dev.storage.googleapis.com/index.html` |
| Prod        | `https://mt-oil-api-prod-edkxkxbaeq-uc.a.run.app` | `https://my-project-1508887546225-mt-oil-dashboard.storage.googleapis.com/index.html`     |

## FracFocus Job (Manual Until Scheduler Fixed)

Because Cloud Scheduler is disabled, trigger FracFocus updates by hand in each environment:

```bash
gcloud run jobs execute mt-oil-fracfocus-dev --region=us-central1 --project=my-project-1508887546225
gcloud run jobs execute mt-oil-fracfocus-prod --region=us-central1 --project=my-project-1508887546225
```

## Go/No-Go Decisions

- [x] Bootstrap verification passes.
- [x] Full data seeding approved and completed.
- [x] $10/month budget and `joseph.romani@gmail.com` alert email approved.
- [x] `master`-based workflow approved with `main` migration deferred.

## Next Actions

1. Address Phase 5 backlog items at the chosen priorities.
2. Continue Phase 7 project-agnostic IaC refactor, starting with `.github/workflows/deploy.yml` GitHub variables.
3. Monitor GCP billing dashboard monthly to stay under the $10 ceiling.
