# MT Oil — GCP Deployment Completion Plan

_Living plan incorporating current decisions: dev-first, sample data seed, public API, GCS static website endpoint, $10/month hard cap, alert email `joseph.romani@gmail.com`. Keep `master` as the production trigger for now, with a backlog item to migrate to `main` in the future._

## Decisions

| Item              | Decision                                                                                      |
| ----------------- | --------------------------------------------------------------------------------------------- |
| GCP project       | `my-project-1508887546225` (billing-enabled)                                                  |
| Bootstrap status  | Uncertain; verify before first deploy                                                         |
| First environment | **Dev only**                                                                                  |
| Data seeding      | **Sample first** (e.g., 100,000 production rows) to prove the end-to-end flow, then full seed |
| API access        | Fully public (`allUsers`) with future auth in backlog                                         |
| Frontend serving  | GCS static website endpoint                                                                   |
| Budget cap        | $10/month hard cap; alert email `joseph.romani@gmail.com`                                     |
| Primary branch    | `master` remains the prod trigger for now; add backlog item to migrate to `main`              |

## Current Status

- [x] FastAPI backend with local + BigQuery data loaders
- [x] React + Vite + Tailwind frontend
- [x] Terraform-managed dev and prod environments
- [x] GitHub Actions CI/CD with Workload Identity Federation
- [x] Cloud Run service, Cloud Run Job, Cloud Scheduler, BigQuery, GCS scaffolding
- [ ] Bootstrap resources verified
- [ ] Data uploaded to BigQuery
- [ ] Model artifact uploaded to GCS
- [ ] Several Terraform / backend bugs block a clean first deploy
- [ ] Prod monitoring not yet applied

## Phase 0 — Bootstrap Verification

Before any CI deployment, confirm the following exist. If any are missing, run `infra/bootstrap/bootstrap.sh` once locally as a project owner.

| Resource                   | Verification command                                                                                                                   |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Terraform state bucket     | `gsutil ls -b gs://my-project-1508887546225-tfstate`                                                                                   |
| Artifact Registry repo     | `gcloud artifacts repositories describe mt-oil-api --location=us-central1`                                                             |
| CI/CD service account      | `gcloud iam service-accounts describe github-actions@my-project-1508887546225.iam.gserviceaccount.com`                                 |
| Workload Identity Pool     | `gcloud iam workload-identity-pools describe github-actions-pool --location=global`                                                    |
| Workload Identity Provider | `gcloud iam workload-identity-pools providers describe github-provider --location=global --workload-identity-pool=github-actions-pool` |
| Billing & budget alerts    | Cloud Console → Billing                                                                                                                |

## Phase 1 — Mandatory Fixes Before First Dev Deploy

### Backend

1. **Fix GCS model save bug** in `src/mt_oil/models/pipeline.py`: write to a temporary file and upload it; do not attempt to download the destination blob first.
2. **Wire `CORS_ORIGINS`** to `FRONTEND_URL` or pass `CORS_ORIGINS` explicitly from Terraform.
3. **Replace `print()` with structured logging** driven by `LOG_LEVEL` in `src/mt_oil/config.py`.
4. **Improve `/health`** so it returns BigQuery/GCS connectivity status in deployed mode.

### Infrastructure

1. **Add App Engine application** resource (or bootstrap step) so Cloud Scheduler can create jobs.
2. **Add Cloud Scheduler invocation IAM**:
   - Cloud Scheduler service agent → `roles/iam.serviceAccountTokenCreator` on the runtime service account.
   - Runtime service account → `roles/run.invoker` on the FracFocus Cloud Run Job.
3. **Wire Cloud Run module variables**: pass `concurrency` and `timeout_seconds` into `google_cloud_run_v2_service`.
4. **Wire Cloud Run Job module variable**: pass `timeout_seconds` into `google_cloud_run_v2_job`.
5. **Add root-level `outputs.tf`** for dev and prod exporting the API URL and frontend website URL.
6. **Update `deploy.yml`** to display the correct GCS static website endpoint rather than the raw `storage.googleapis.com/<bucket>` XML URL.
7. **Review CI/CD service account permissions** in `infra/bootstrap/bootstrap.sh` so Terraform can create datasets, scheduler jobs, monitoring resources, and service accounts.

### Repository / Branch Hygiene

1. Keep `master` as the production trigger for now; add a code comment and backlog task documenting the future migration to `main`.
2. Ensure pre-commit `no-commit-to-branch` is consistent with the active protected branches.

## Phase 2 — Dev Data Seeding (Sample First)

Use the existing `scripts/seed_bigquery.py` to load a sample into the dev dataset:

```bash
cd /Users/josephromani/MT_Oil
source venv/bin/activate
python scripts/seed_bigquery.py \
  --project my-project-1508887546225 \
  --dataset mt_oil_dev \
  --sample 100000
```

Then upload the model artifact:

```bash
gsutil cp rf_model.joblib \
  gs://my-project-1508887546225-mt-oil-dev/models/rf_model.joblib
```

**Validation:**

- `wells`, `production_monthly`, and (optionally) `frac_focus` tables exist in `mt_oil_dev`.
- Spot-check a known API well number against the local `.tab` data.

## Phase 3 — Dev Deployment

1. Merge Phase 1 fixes into `dev`.
2. Trigger `.github/workflows/deploy-dev.yml`:
   - Build and push the API image to Artifact Registry.
   - Run `terraform apply` for the dev environment.
   - Build the frontend with `VITE_API_BASE_URL` set to the dev Cloud Run URL.
   - Sync `frontend/dist` to `my-project-1508887546225-mt-oil-dashboard-dev`.
3. Validate:
   - `GET https://<dev-api>/health` returns 200.
   - `/filters` and `/wells` return BigQuery-backed data.
   - Map, DCA, and economics views work end to end.
   - The frontend loads from the GCS website URL and CORS succeeds.

## Phase 4 — Full Data Seed + Prod Deployment

1. Seed the prod dataset with the full local data (no `--sample`):

   ```bash
   python scripts/seed_bigquery.py \
     --project my-project-1508887546225 \
     --dataset mt_oil_prod
   ```

2. Upload the model artifact to the prod GCS bucket:

   ```bash
   gsutil cp rf_model.joblib \
     gs://my-project-1508887546225-mt-oil-prod/models/rf_model.joblib
   ```

3. Merge `dev` → `master` and let `.github/workflows/deploy-prod.yml` run.
4. Verify the prod monitoring module applies and uptime check / alert emails reach `joseph.romani@gmail.com`.

## Phase 5 — Post-Deploy Backlog

| Item                                                         | Priority |
| ------------------------------------------------------------ | -------- |
| Migrate primary branch from `master` to `main`               | Medium   |
| Add rate limiting to public API (e.g., SlowAPI)              | Medium   |
| Add authentication (IAP or API key) for a non-public variant | Low      |
| Add frontend tests and error boundary                        | Medium   |
| Add `/train` status/result endpoint                          | Low      |
| Add lifecycle rule for old model artifacts in GCS            | Low      |
| Remove dead `firebase_hosting` Terraform module              | Low      |
| Update `AGENTS.md` with the validated deployment runbook     | Medium   |
| Add `README.md` status badges                                | Low      |

## Phase 6 — Branch Migration to `main` (Future)

When ready to move from `master` to `main`:

1. Create `main`, set it as the default branch in GitHub.
2. Update `.github/workflows/deploy-prod.yml` trigger to `main`.
3. Update `.github/workflows/ci.yml` PR target branches to include `main`.
4. Update `.pre-commit-config.yaml` to block `main` (and/or replace `master`).
5. Retire `master` after a transition period.

## Cost Model

| Service                         | Configuration                          | Approx. Monthly Cost               |
| ------------------------------- | -------------------------------------- | ---------------------------------- |
| Cloud Run (dev + prod)          | `max_scale = 1`, CPU throttled, 1 GiB  | Mostly $0 when idle                |
| Cloud Run Jobs (FracFocus)      | Monthly run, 4 GiB / 2 CPU for minutes | <$0.10                             |
| Cloud Storage (frontend + data) | ~1 GB standard class                   | <$0.05                             |
| BigQuery storage                | ~500 MB–1 GB                           | <$0.05                             |
| BigQuery queries                | UI-scoped reads                        | Usually within free tier           |
| Cloud Monitoring                | Uptime checks + alert policies         | Usually within free tier           |
| Cloud Scheduler                 | 1 job                                  | Within free tier                   |
| Artifact Registry               | Small container images                 | <$0.10                             |
| **Total**                       |                                        | **<$5 typical, <$10 hard ceiling** |

## Go/No-Go Before Starting

- [ ] Bootstrap verification passes, or `bootstrap.sh` has been re-run and confirmed.
- [ ] You approve sample-first seeding (`--sample 100000`) for dev.
- [ ] You approve the $10/month budget and `joseph.romani@gmail.com` for billing/alert emails.
- [ ] You approve updating the current `master`-based workflow for dev/prod, with `main` migration deferred to a backlog item.

## Next Action

1. Verify the bootstrap resources listed in Phase 0.
2. Begin Phase 1 backend/infrastructure fixes.
3. Seed dev BigQuery with a sample and upload the model artifact.
4. Trigger the first dev deployment and validate end to end.
