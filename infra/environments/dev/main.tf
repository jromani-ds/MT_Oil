terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
  }

  backend "gcs" {
    bucket = "my-project-1508887546225-tfstate"
    prefix = "dev/terraform.tfstate"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

locals {
  env = "dev"
  labels = {
    environment = local.env
    project     = "mt-oil"
    managed_by  = "terraform"
  }
}

# Service account used by Cloud Run API and Cloud Run Jobs at runtime.
resource "google_service_account" "runtime" {
  account_id   = "mt-oil-runtime-${local.env}"
  display_name = "MT Oil runtime service account (${local.env})"
  description  = "Used by Cloud Run API and Cloud Run Jobs to access BigQuery and GCS"
}

resource "google_project_iam_member" "runtime_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_bigquery_read" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

module "apis" {
  source     = "../../modules/enable_apis"
  project_id = var.project_id
}

module "gcs" {
  source      = "../../modules/gcs"
  project_id  = var.project_id
  bucket_name = "${var.project_id}-mt-oil-${local.env}"
  location    = var.gcs_location
  versioning  = true
  labels      = local.labels

  depends_on = [module.apis]
}

module "bigquery" {
  source      = "../../modules/bigquery"
  project_id  = var.project_id
  dataset_id  = "mt_oil_${local.env}"
  location    = var.bigquery_location
  description = "MT Oil analytics dataset (${local.env})"
  labels      = local.labels

  depends_on = [module.apis]
}

module "secrets" {
  source   = "../../modules/secret_manager"
  for_each = toset([])

  project_id = var.project_id
  secret_id  = each.value
  labels     = local.labels

  depends_on = [module.apis]
}

module "frontend_gcs" {
  source      = "../../modules/gcs"
  project_id  = var.project_id
  bucket_name = "${var.project_id}-mt-oil-dashboard-${local.env}"
  location    = var.gcs_location
  versioning  = false
  labels      = local.labels
  website = {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  depends_on = [module.apis]
}

resource "google_storage_bucket_iam_member" "frontend_public" {
  bucket = module.frontend_gcs.bucket_name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

module "cloud_run" {
  source     = "../../modules/cloud_run"
  project_id = var.project_id
  region     = var.region

  service_name          = "mt-oil-api-${local.env}"
  image                 = var.api_image
  service_account_email = google_service_account.runtime.email
  deletion_protection   = false

  min_scale             = 0
  max_scale             = 1
  memory                = "1Gi"
  cpu                   = "1"
  cpu_always_allocated  = false
  allow_unauthenticated = true

  env_vars = {
    ENVIRONMENT       = local.env
    GCP_PROJECT_ID    = var.project_id
    GCS_DATA_BUCKET   = module.gcs.bucket_name
    BIGQUERY_DATASET  = module.bigquery.dataset_id
    FRONTEND_URL      = module.frontend_gcs.website_url
    CORS_ORIGINS      = module.frontend_gcs.website_url
    MODEL_PATH        = "gs://${module.gcs.bucket_name}/models/rf_model.joblib"
    ENABLE_LOCAL_DATA = "false"
    LOG_LEVEL         = "info"
  }

  labels = local.labels

  depends_on = [module.gcs, module.bigquery, module.frontend_gcs]
}

module "fracfocus_job" {
  source     = "../../modules/cloud_run_job"
  project_id = var.project_id
  region     = var.region

  job_name              = "mt-oil-fracfocus-${local.env}"
  image                 = var.api_image
  service_account_email = google_service_account.runtime.email
  memory                = "4Gi"
  cpu                   = "2"
  timeout_seconds       = 7200
  max_retries           = 2

  env_vars = {
    ENVIRONMENT      = local.env
    GCP_PROJECT_ID   = var.project_id
    GCS_DATA_BUCKET  = module.gcs.bucket_name
    BIGQUERY_DATASET = module.bigquery.dataset_id
    JOB_NAME         = "fracfocus-update"
  }

  labels = local.labels

  depends_on = [module.gcs, module.bigquery]
}

module "fracfocus_scheduler" {
  source     = "../../modules/cloud_scheduler"
  project_id = var.project_id
  region     = var.scheduler_region

  job_name              = "mt-oil-fracfocus-${local.env}-monthly"
  schedule              = "0 2 1 * *"
  time_zone             = "America/Denver"
  cloud_run_job_name    = module.fracfocus_job.job_name
  service_account_email = google_service_account.runtime.email

  depends_on = [module.fracfocus_job]
}
