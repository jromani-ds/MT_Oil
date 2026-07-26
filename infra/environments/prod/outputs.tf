output "api_url" {
  description = "Cloud Run API service URL"
  value       = module.cloud_run.service_url
}

output "frontend_website_url" {
  description = "GCS static website URL for the frontend"
  value       = module.frontend_gcs.website_url
}

output "data_bucket" {
  description = "GCS bucket for data and model artifacts"
  value       = module.gcs.bucket_name
}

output "frontend_bucket" {
  description = "GCS bucket serving the static frontend"
  value       = module.frontend_gcs.bucket_name
}

output "bigquery_dataset" {
  description = "BigQuery dataset ID"
  value       = module.bigquery.dataset_id
}

output "cloud_run_service_name" {
  description = "Cloud Run API service name"
  value       = module.cloud_run.service_name
}

output "fracfocus_job_name" {
  description = "Cloud Run Job name for FracFocus updates"
  value       = module.fracfocus_job.job_name
}
