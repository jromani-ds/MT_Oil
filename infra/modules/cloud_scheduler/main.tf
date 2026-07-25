resource "google_cloud_scheduler_job" "this" {
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
