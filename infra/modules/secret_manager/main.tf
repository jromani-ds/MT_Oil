resource "google_secret_manager_secret" "this" {
  project   = var.project_id
  secret_id = var.secret_id

  replication {
    auto {}
  }

  labels = var.labels
}

output "secret_id" {
  value = google_secret_manager_secret.this.secret_id
}

output "secret_name" {
  value = google_secret_manager_secret.this.id
}
