variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "env" {
  description = "Environment name"
  type        = string
}

variable "api_url" {
  description = "Full HTTPS URL of the API (e.g. https://...run.app)"
  type        = string
}

variable "frontend_url" {
  description = "Full HTTPS URL of the frontend static site"
  type        = string
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "alert_email" {
  description = "Email address for alert notifications (empty = console only)"
  type        = string
  default     = ""
}

variable "billing_account" {
  description = "GCP billing account ID for budget alerts (empty = no budget)"
  type        = string
  default     = ""
}

variable "budget_amount" {
  description = "Monthly budget amount in USD"
  type        = number
  default     = 10
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}
