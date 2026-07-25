output "dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.this.dataset_id
}

output "dataset_self_link" {
  description = "BigQuery dataset self link"
  value       = google_bigquery_dataset.this.self_link
}
