variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "secret_id" {
  description = "Secret Manager secret ID"
  type        = string
}

variable "labels" {
  description = "Secret labels"
  type        = map(string)
  default     = {}
}
