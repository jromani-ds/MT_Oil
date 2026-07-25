variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Cloud Run region"
  type        = string
}

variable "job_name" {
  description = "Cloud Run job name"
  type        = string
}

variable "image" {
  description = "Container image URL"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for the job"
  type        = string
}

variable "memory" {
  description = "Container memory"
  type        = string
  default     = "2Gi"
}

variable "cpu" {
  description = "Container CPU"
  type        = string
  default     = "1"
}

variable "timeout_seconds" {
  description = "Job timeout"
  type        = number
  default     = 3600
}

variable "max_retries" {
  description = "Maximum retries"
  type        = number
  default     = 2
}

variable "env_vars" {
  description = "Environment variables"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets as environment variables"
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Job labels"
  type        = map(string)
  default     = {}
}
