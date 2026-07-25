variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Scheduler region"
  type        = string
}

variable "job_name" {
  description = "Name of the scheduler job"
  type        = string
}

variable "schedule" {
  description = "Cron schedule"
  type        = string
  default     = "0 2 1 * *"
}

variable "time_zone" {
  description = "Time zone"
  type        = string
  default     = "America/Denver"
}

variable "cloud_run_job_name" {
  description = "Target Cloud Run job name"
  type        = string
}

variable "service_account_email" {
  description = "Service account email to run the scheduler job"
  type        = string
}

variable "app_engine_location" {
  description = "App Engine location for Cloud Scheduler (must match scheduler region, e.g. us-central for us-central1)"
  type        = string
  default     = "us-central"
}
