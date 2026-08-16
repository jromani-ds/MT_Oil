resource "google_bigquery_dataset" "this" {
  project       = var.project_id
  dataset_id    = var.dataset_id
  friendly_name = var.dataset_id
  description   = var.description
  location      = var.location
  labels        = var.labels
}

resource "google_bigquery_table" "wells" {
  dataset_id          = google_bigquery_dataset.this.dataset_id
  table_id            = "wells"
  project             = var.project_id
  deletion_protection = true

  clustering = ["api_wellno"]

  schema = jsonencode([
    { name = "api_wellno", type = "STRING", mode = "REQUIRED" },
    { name = "well_name", type = "STRING", mode = "NULLABLE" },
    { name = "operator", type = "STRING", mode = "NULLABLE" },
    { name = "latitude", type = "FLOAT64", mode = "NULLABLE" },
    { name = "longitude", type = "FLOAT64", mode = "NULLABLE" },
    { name = "type", type = "STRING", mode = "NULLABLE" },
    { name = "slant", type = "STRING", mode = "NULLABLE" },
    { name = "dtd", type = "FLOAT64", mode = "NULLABLE" },
    { name = "total_depth", type = "FLOAT64", mode = "NULLABLE" },
    { name = "county", type = "STRING", mode = "NULLABLE" },
    { name = "field", type = "STRING", mode = "NULLABLE" },
    { name = "formation", type = "STRING", mode = "NULLABLE" },
    { name = "spud_date", type = "DATE", mode = "NULLABLE" },
    { name = "completion_date", type = "DATE", mode = "NULLABLE" },
    { name = "status", type = "STRING", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])

  lifecycle {
    ignore_changes = [schema]
  }
}

resource "google_bigquery_table" "production_monthly" {
  dataset_id          = google_bigquery_dataset.this.dataset_id
  table_id            = "production_monthly"
  project             = var.project_id
  deletion_protection = true

  time_partitioning {
    type  = "MONTH"
    field = "rpt_date"
  }

  clustering = ["api_wellno"]

  schema = jsonencode([
    { name = "api_wellno", type = "STRING", mode = "REQUIRED" },
    { name = "rpt_date", type = "DATE", mode = "REQUIRED" },
    { name = "st_fmtn_cd", type = "STRING", mode = "NULLABLE" },
    { name = "bbls_oil_cond", type = "FLOAT64", mode = "NULLABLE" },
    { name = "mcf_gas", type = "FLOAT64", mode = "NULLABLE" },
    { name = "bbls_wtr", type = "FLOAT64", mode = "NULLABLE" },
    { name = "days_prod", type = "INT64", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])

  lifecycle {
    ignore_changes = [schema]
  }
}

resource "google_bigquery_table" "frac_focus" {
  dataset_id          = google_bigquery_dataset.this.dataset_id
  table_id            = "frac_focus"
  project             = var.project_id
  deletion_protection = true

  clustering = ["api_wellno"]

  schema = jsonencode([
    { name = "api_wellno", type = "STRING", mode = "REQUIRED" },
    { name = "job_start_date", type = "DATE", mode = "NULLABLE" },
    { name = "state", type = "STRING", mode = "NULLABLE" },
    { name = "county", type = "STRING", mode = "NULLABLE" },
    { name = "total_water_volume", type = "FLOAT64", mode = "NULLABLE" },
    { name = "total_proppant", type = "FLOAT64", mode = "NULLABLE" },
    { name = "td", type = "FLOAT64", mode = "NULLABLE" },
    { name = "tvd", type = "FLOAT64", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])

  lifecycle {
    ignore_changes = [schema]
  }
}

resource "google_bigquery_table" "analysis_outputs" {
  dataset_id          = google_bigquery_dataset.this.dataset_id
  table_id            = "analysis_outputs"
  project             = var.project_id
  deletion_protection = true

  time_partitioning {
    type  = "MONTH"
    field = "created_at"
  }

  clustering = ["api_wellno", "analysis_type"]

  schema = jsonencode([
    { name = "api_wellno", type = "STRING", mode = "REQUIRED" },
    { name = "analysis_type", type = "STRING", mode = "REQUIRED" },
    { name = "version", type = "STRING", mode = "NULLABLE" },
    { name = "payload", type = "JSON", mode = "NULLABLE" },
    { name = "created_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])

  lifecycle {
    ignore_changes = [schema]
  }
}

resource "google_bigquery_table" "pdf_fetch_status" {
  dataset_id          = google_bigquery_dataset.this.dataset_id
  table_id            = "pdf_fetch_status"
  project             = var.project_id
  deletion_protection = false

  clustering = ["execution_id", "api_wellno"]

  schema = jsonencode([
    { name = "api_wellno", type = "STRING", mode = "REQUIRED" },
    { name = "execution_id", type = "STRING", mode = "REQUIRED" },
    { name = "status", type = "STRING", mode = "REQUIRED" },
    { name = "size_bytes", type = "INT64", mode = "NULLABLE" },
    { name = "updated_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "attempts", type = "INT64", mode = "NULLABLE" },
    { name = "error_message", type = "STRING", mode = "NULLABLE" },
  ])

  lifecycle {
    ignore_changes = [schema]
  }
}

resource "google_bigquery_table" "wellfile_parsed_metadata" {
  dataset_id          = google_bigquery_dataset.this.dataset_id
  table_id            = "wellfile_parsed_metadata"
  project             = var.project_id
  deletion_protection = true

  time_partitioning {
    type  = "MONTH"
    field = "extracted_at"
  }

  clustering = ["api_number"]

  schema = jsonencode([
    { name = "api_number", type = "STRING", mode = "REQUIRED" },
    { name = "well_name", type = "STRING", mode = "NULLABLE" },
    { name = "tvd_ft", type = "FLOAT64", mode = "NULLABLE" },
    { name = "md_ft", type = "FLOAT64", mode = "NULLABLE" },
    { name = "lateral_length_ft", type = "FLOAT64", mode = "NULLABLE" },
    { name = "total_clean_fluid_bbls", type = "FLOAT64", mode = "NULLABLE" },
    { name = "total_proppant_lbs", type = "FLOAT64", mode = "NULLABLE" },
    { name = "max_treating_pressure_psi", type = "FLOAT64", mode = "NULLABLE" },
    { name = "casing_intermediate_depth_ft", type = "FLOAT64", mode = "NULLABLE" },
    { name = "extraction_status", type = "STRING", mode = "REQUIRED" },
    { name = "extracted_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "gcs_uri", type = "STRING", mode = "NULLABLE" },
    { name = "input_tokens", type = "INT64", mode = "NULLABLE" },
    { name = "output_tokens", type = "INT64", mode = "NULLABLE" },
    { name = "latency_ms", type = "FLOAT64", mode = "NULLABLE" },
    { name = "payload", type = "JSON", mode = "NULLABLE" },
  ])

  depends_on = [google_bigquery_dataset.this]
}
