variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "apis" {
  description = "List of APIs to enable"
  type        = list(string)
  default = [
    "run.googleapis.com",
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudscheduler.googleapis.com",
    "bigquery.googleapis.com",
    "secretmanager.googleapis.com",
    "iamcredentials.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "billingbudgets.googleapis.com",
    "appengine.googleapis.com",
    "aiplatform.googleapis.com",
  ]
}
