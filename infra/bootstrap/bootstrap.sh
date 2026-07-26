#!/usr/bin/env bash
# Bootstrap script for MT Oil Analytics GCP project.
# Run once locally as a project owner to create the Terraform state backend,
# enable APIs, and configure Workload Identity Federation for GitHub Actions.

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-}"
REPO_OWNER="${REPO_OWNER:-jromani-ds}"
REPO_NAME="${REPO_NAME:-MT_Oil}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: PROJECT_ID environment variable is required."
  echo "Usage: PROJECT_ID=<gcp-project-id> REGION=<gcp-region> ./infra/bootstrap/bootstrap.sh"
  exit 1
fi

if [[ -z "${REGION}" ]]; then
  echo "ERROR: REGION environment variable is required."
  echo "Usage: PROJECT_ID=<gcp-project-id> REGION=<gcp-region> ./infra/bootstrap/bootstrap.sh"
  exit 1
fi
STATE_BUCKET="gs://${PROJECT_ID}-tfstate"
POOL_NAME="github-actions-pool"
PROVIDER_NAME="github-provider"
SA_NAME="github-actions"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== Bootstrapping project ${PROJECT_ID} ==="
echo "Using region: ${REGION}"
echo "GitHub repo: ${REPO_OWNER}/${REPO_NAME}"

# Set active project
gcloud config set project "${PROJECT_ID}"

# Enable required APIs
echo "=== Enabling Google Cloud APIs ==="
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  compute.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  bigquery.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  billingbudgets.googleapis.com \
  appengine.googleapis.com \
  firebase.googleapis.com \
  firestore.googleapis.com \
  --project="${PROJECT_ID}"

# Create Terraform state bucket (idempotent)
echo "=== Creating Terraform state bucket ==="
if ! gsutil ls -b "${STATE_BUCKET}" >/dev/null 2>&1; then
  gsutil mb -l "${REGION}" -p "${PROJECT_ID}" "${STATE_BUCKET}"
  gsutil versioning set on "${STATE_BUCKET}"
  gsutil ubla set on "${STATE_BUCKET}"
  echo "Created ${STATE_BUCKET}"
else
  echo "Bucket ${STATE_BUCKET} already exists"
fi

# Create Artifact Registry repository (not managed by Terraform to avoid chicken-and-egg)
echo "=== Creating Artifact Registry repository ==="
if ! gcloud artifacts repositories describe mt-oil-api --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud artifacts repositories create mt-oil-api \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Docker images for MT Oil API" \
    --project="${PROJECT_ID}"
fi

# Create GitHub Actions service account (idempotent)
echo "=== Creating CI/CD service account ==="
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" \
    --display-name="GitHub Actions CI/CD" \
    --description="Service account used by GitHub Actions for CI/CD deployments" \
    --project="${PROJECT_ID}"
fi

# Grant roles to the CI/CD service account (idempotent via gcloud add-iam-policy-binding semantics)
echo "=== Granting IAM roles to CI/CD service account ==="
ROLES=(
  roles/run.admin
  roles/artifactregistry.writer
  roles/storage.admin
  roles/bigquery.admin
  roles/secretmanager.secretAccessor
  roles/iam.serviceAccountAdmin
  roles/iam.serviceAccountUser
  roles/iam.workloadIdentityUser
  roles/logging.logWriter
  roles/monitoring.editor
  roles/cloudscheduler.admin
  roles/appengine.appAdmin
  roles/appengine.appCreator
  roles/serviceusage.serviceUsageAdmin
)

for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${ROLE}" \
    --condition=None \
    --quiet >/dev/null
done

# Create Workload Identity Pool
echo "=== Creating Workload Identity Pool ==="
if ! gcloud iam workload-identity-pools describe "${POOL_NAME}" --location=global --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "${POOL_NAME}" \
    --display-name="GitHub Actions" \
    --description="Pool for GitHub Actions OIDC tokens" \
    --location=global \
    --project="${PROJECT_ID}"
fi

# Create Workload Identity Provider
echo "=== Creating Workload Identity Provider ==="
if ! gcloud iam workload-identity-pools providers describe "${PROVIDER_NAME}" \
    --location=global \
    --workload-identity-pool="${POOL_NAME}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_NAME}" \
    --location=global \
    --workload-identity-pool="${POOL_NAME}" \
    --display-name="GitHub Actions Provider" \
    --description="OIDC provider for ${REPO_OWNER}/${REPO_NAME}" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --allowed-audiences="https://github.com/${REPO_OWNER}/${REPO_NAME}" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository=='${REPO_OWNER}/${REPO_NAME}'" \
    --project="${PROJECT_ID}"
fi

# Allow the workload identity pool to impersonate the CI/CD SA
echo "=== Binding Workload Identity to service account ==="
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
POOL_IDENTIFIER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}"
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL_IDENTIFIER}/attribute.repository/${REPO_OWNER}/${REPO_NAME}" \
  --project="${PROJECT_ID}" \
  --quiet >/dev/null

echo ""
echo "=== Bootstrap complete ==="
echo "Terraform state bucket: ${STATE_BUCKET}"
echo "Workload Identity Provider:"
gcloud iam workload-identity-pools providers describe "${PROVIDER_NAME}" \
  --location=global \
  --workload-identity-pool="${POOL_NAME}" \
  --project="${PROJECT_ID}" \
  --format="value(name)"
echo ""
echo "Add the following GitHub variables for CI/CD:"
echo "  GCP_PROJECT_ID              = ${PROJECT_ID}"
echo "  GCP_REGION                  = ${REGION}"
echo "  GCP_SERVICE_ACCOUNT_EMAIL   = ${SA_EMAIL}"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER = projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/providers/${PROVIDER_NAME}"
