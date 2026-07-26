resource "google_cloud_run_v2_job" "this" {
  name     = var.job_name
  project  = var.project_id
  location = var.region
  labels   = var.labels

  template {
    template {
      service_account = var.service_account_email
      timeout         = "${var.timeout_seconds}s"

      containers {
        image = var.image

        command = length(var.command) > 0 ? var.command : null
        args    = length(var.args) > 0 ? var.args : null

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }

        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = var.secrets
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }

      max_retries = var.max_retries
    }
  }
}
