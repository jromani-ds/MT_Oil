variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
}

variable "location" {
  description = "Dataset location"
  type        = string
  default     = "US"
}

variable "description" {
  description = "Dataset description"
  type        = string
  default     = "MT Oil analytics dataset"
}

variable "labels" {
  description = "Dataset labels"
  type        = map(string)
  default     = {}
}
