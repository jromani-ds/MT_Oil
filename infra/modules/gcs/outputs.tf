output "bucket_name" {
  description = "GCS bucket name"
  value       = google_storage_bucket.this.name
}

output "bucket_url" {
  description = "GCS bucket URL"
  value       = "gs://${google_storage_bucket.this.name}"
}

output "website_url" {
  description = "GCS static website endpoint URL"
  value       = "https://${google_storage_bucket.this.name}.storage.googleapis.com/"
}
