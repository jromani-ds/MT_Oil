variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Cloud Run region"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
}

variable "image" {
  description = "Container image URL"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for the Cloud Run service"
  type        = string
}

variable "min_scale" {
  description = "Minimum instances"
  type        = number
  default     = 0
}

variable "max_scale" {
  description = "Maximum instances"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Container memory"
  type        = string
  default     = "1Gi"
}

variable "cpu" {
  description = "Container CPU"
  type        = string
  default     = "1"
}

variable "concurrency" {
  description = "Max requests per container instance"
  type        = number
  default     = 80
}

variable "timeout_seconds" {
  description = "Request timeout"
  type        = number
  default     = 300
}

variable "cpu_always_allocated" {
  description = "Whether CPU is always allocated"
  type        = bool
  default     = false
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

variable "ingress" {
  description = "Ingress traffic source"
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "allow_unauthenticated" {
  description = "Allow unauthenticated invocations"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Whether Terraform should protect the service from deletion"
  type        = bool
  default     = true
}

variable "labels" {
  description = "Service labels"
  type        = map(string)
  default     = {}
}
