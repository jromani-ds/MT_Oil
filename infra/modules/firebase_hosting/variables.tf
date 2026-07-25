variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "site_id" {
  description = "Firebase Hosting site ID"
  type        = string
}

variable "app_name" {
  description = "Firebase app display name"
  type        = string
  default     = "MT Oil Dashboard"
}
