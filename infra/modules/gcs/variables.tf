variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "bucket_name" {
  description = "Name of the GCS bucket"
  type        = string
}

variable "location" {
  description = "Bucket location"
  type        = string
  default     = "US-CENTRAL1"
}

variable "storage_class" {
  description = "Default storage class"
  type        = string
  default     = "STANDARD"
}

variable "lifecycle_age_days" {
  description = "Move objects to nearline after N days"
  type        = number
  default     = 90
}

variable "model_artifact_delete_age_days" {
  description = "Delete objects under the models/ prefix after N days to control artifact storage costs"
  type        = number
  default     = 180
}

variable "uniform_bucket_level_access" {
  description = "Enable uniform bucket-level access"
  type        = bool
  default     = true
}

variable "versioning" {
  description = "Enable object versioning"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Bucket labels"
  type        = map(string)
  default     = {}
}

variable "website" {
  description = "Optional static website configuration"
  type = object({
    main_page_suffix = string
    not_found_page   = string
  })
  default = null
}
