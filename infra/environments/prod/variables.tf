variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Primary GCP region"
  type        = string
  default     = "us-central1"
}

variable "gcs_location" {
  description = "GCS bucket location"
  type        = string
  default     = "US-CENTRAL1"
}

variable "bigquery_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}

variable "scheduler_region" {
  description = "Cloud Scheduler region"
  type        = string
  default     = "us-central1"
}

variable "api_image" {
  description = "Container image for the API and jobs"
  type        = string
}

variable "alert_email" {
  description = "Email address for monitoring alerts (empty = console-only)"
  type        = string
  default     = ""
}

variable "billing_account" {
  description = "GCP billing account ID for budget alerts (empty = no budget)"
  type        = string
  default     = ""
}
