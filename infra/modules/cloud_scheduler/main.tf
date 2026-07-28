data "google_project" "project" {
  project_id = var.project_id
}

resource "google_cloud_scheduler_job" "this" {
  count            = var.enabled ? 1 : 0
  name             = var.job_name
  project          = var.project_id
  region           = var.region
  schedule         = var.schedule
  time_zone        = var.time_zone
  attempt_deadline = "1800s"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${var.cloud_run_job_name}:run"

    oauth_token {
      service_account_email = var.service_account_email
    }
  }
}

# Allow the runtime service account to invoke the target Cloud Run Job.
resource "google_cloud_run_v2_job_iam_member" "invoker" {
  count    = var.enabled ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = var.cloud_run_job_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.service_account_email}"
}

# Allow the Cloud Scheduler service agent to impersonate the runtime SA.
resource "google_service_account_iam_member" "scheduler_token_creator" {
  count              = var.enabled ? 1 : 0
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.service_account_email}"
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
}
