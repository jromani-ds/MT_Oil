locals {
  enabled = var.env == "prod" ? 1 : 0

  billing_account_id = startswith(var.billing_account, "billingAccounts/") ? var.billing_account : "billingAccounts/${var.billing_account}"

  api_url_parts = regex("^https://([^/]+)(.*)$", var.api_url)
  api_host      = local.api_url_parts[0]
  api_path      = "${trimsuffix(local.api_url_parts[1], "/")}/health"

  frontend_url_parts = regex("^https://([^/]+)(.*)$", var.frontend_url)
  frontend_host      = local.frontend_url_parts[0]
  frontend_path      = "${trimsuffix(local.frontend_url_parts[1], "/")}/index.html"
}

resource "google_monitoring_uptime_check_config" "api_health" {
  count = local.enabled

  project      = var.project_id
  display_name = "mt-oil-${var.env}-api-health"

  timeout          = "10s"
  period           = "300s"
  selected_regions = ["USA"]

  http_check {
    path         = local.api_path
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = local.api_host
    }
  }

  user_labels = var.labels
}

resource "google_monitoring_uptime_check_config" "frontend_health" {
  count = local.enabled

  project      = var.project_id
  display_name = "mt-oil-${var.env}-frontend-health"

  timeout          = "10s"
  period           = "300s"
  selected_regions = ["USA"]

  http_check {
    path         = local.frontend_path
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = local.frontend_host
    }
  }

  user_labels = var.labels
}

resource "google_monitoring_notification_channel" "email" {
  count   = local.enabled > 0 && var.alert_email != "" ? 1 : 0
  project = var.project_id

  display_name = "MT Oil ${var.env} alerts"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }

  force_delete = true
}

resource "google_monitoring_alert_policy" "api_uptime" {
  count = local.enabled

  project      = var.project_id
  display_name = "mt-oil-${var.env}-api-uptime"
  combiner     = "OR"

  conditions {
    display_name = "API health check failure"
    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
        "resource.type=\"uptime_url\"",
        "metric.labels.check_id=\"${google_monitoring_uptime_check_config.api_health[0].uptime_check_id}\"",
      ])
      duration        = "0s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_FRACTION_TRUE"
      }
    }
  }

  notification_channels = length(google_monitoring_notification_channel.email) > 0 ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "86400s"
  }

  severity    = "CRITICAL"
  user_labels = var.labels
}

resource "google_monitoring_alert_policy" "frontend_uptime" {
  count = local.enabled

  project      = var.project_id
  display_name = "mt-oil-${var.env}-frontend-uptime"
  combiner     = "OR"

  conditions {
    display_name = "Frontend health check failure"
    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\"",
        "resource.type=\"uptime_url\"",
        "metric.labels.check_id=\"${google_monitoring_uptime_check_config.frontend_health[0].uptime_check_id}\"",
      ])
      duration        = "0s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_FRACTION_TRUE"
      }
    }
  }

  notification_channels = length(google_monitoring_notification_channel.email) > 0 ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "86400s"
  }

  severity    = "CRITICAL"
  user_labels = var.labels
}

resource "google_monitoring_alert_policy" "cloud_run_5xx" {
  count = local.enabled

  project      = var.project_id
  display_name = "mt-oil-${var.env}-cloud-run-5xx"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run 5xx error rate > 0"
    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"run.googleapis.com/request_count\"",
        "resource.type=\"cloud_run_revision\"",
        "resource.label.service_name=\"${var.cloud_run_service_name}\"",
        "metric.label.response_code_class=\"5xx\"",
      ])
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = length(google_monitoring_notification_channel.email) > 0 ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "86400s"
  }

  severity    = "ERROR"
  user_labels = var.labels
}

resource "google_monitoring_alert_policy" "cloud_run_latency" {
  count = local.enabled

  project      = var.project_id
  display_name = "mt-oil-${var.env}-cloud-run-latency"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run p95 latency > 2000 ms"
    condition_threshold {
      filter = join(" AND ", [
        "metric.type=\"run.googleapis.com/request_latencies\"",
        "resource.type=\"cloud_run_revision\"",
        "resource.label.service_name=\"${var.cloud_run_service_name}\"",
      ])
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 2000
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_PERCENTILE_95"
      }
    }
  }

  notification_channels = length(google_monitoring_notification_channel.email) > 0 ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "86400s"
  }

  severity    = "WARNING"
  user_labels = var.labels
}

resource "google_billing_budget" "monthly" {
  count = local.enabled > 0 && var.billing_account != "" ? 1 : 0

  billing_account = local.billing_account_id
  display_name    = "mt-oil-${var.env}-monthly-budget"

  amount {
    specified_amount {
      currency_code = "USD"
      units         = var.budget_amount
    }
  }

  threshold_rules {
    threshold_percent = 50
  }

  threshold_rules {
    threshold_percent = 90
  }

  threshold_rules {
    threshold_percent = 100
  }

  all_updates_rule {
    monitoring_notification_channels = length(google_monitoring_notification_channel.email) > 0 ? [google_monitoring_notification_channel.email[0].id] : []
    disable_default_iam_recipients   = false
  }
}
