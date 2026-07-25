terraform {
  required_providers {
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
  }
}

resource "google_firebase_hosting_site" "this" {
  provider = google-beta
  project  = var.project_id
  site_id  = var.site_id

  app_id = google_firebase_web_app.this.app_id
}

resource "google_firebase_web_app" "this" {
  provider     = google-beta
  project      = var.project_id
  display_name = var.app_name
}

output "site_id" {
  value = google_firebase_hosting_site.this.site_id
}

output "site_url" {
  value = "https://${google_firebase_hosting_site.this.default_url}"
}

output "app_id" {
  value = google_firebase_web_app.this.app_id
}
