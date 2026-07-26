resource "google_cloud_run_v2_service" "this" {
  name                = var.service_name
  project             = var.project_id
  location            = var.region
  ingress             = var.ingress
  deletion_protection = var.deletion_protection

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.min_scale
      max_instance_count = var.max_scale
    }

    timeout                          = "${var.timeout_seconds}s"
    max_instance_request_concurrency = var.concurrency

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = !var.cpu_always_allocated
      }

      ports {
        container_port = 8000
      }

      startup_probe {
        initial_delay_seconds = 30
        period_seconds        = 30
        timeout_seconds       = 10
        failure_threshold     = 15
        tcp_socket {
          port = 8000
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
  }

  labels = var.labels

  lifecycle {
    ignore_changes = [template[0].scaling]
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.this.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
