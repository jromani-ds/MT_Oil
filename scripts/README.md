# MT Oil — Operational Scripts

One-off and periodic scripts for data seeding and GIS processing.

## `seed_bigquery.py`

Loads Montana DNRC `.tab` files into BigQuery. Supports local files and GCS
source modes, and can seed both dev and prod datasets from the same data.

```bash
# Seed a single dataset from local files
python scripts/seed_bigquery.py --project <GCP_PROJECT_ID> --dataset mt_oil_dev

# Upload local files to GCS once, then seed both datasets from GCS
python scripts/seed_bigquery.py \
  --project <GCP_PROJECT_ID> \
  --gcs-bucket <GCS_BUCKET_NAME> \
  --all-datasets \
  --upload-source

# Re-seed both datasets from existing GCS files
python scripts/seed_bigquery.py \
  --project <GCP_PROJECT_ID> \
  --gcs-bucket <GCS_BUCKET_NAME> \
  --all-datasets
```

Seeds three BigQuery tables:

- `wells` — well header data (API number, location, operator, status)
- `production_monthly` — monthly production volumes
- `frac_focus` — FracFocus completion data (optional, downloaded live)

## `process_gis_data.py`

Downloads Montana MBOGC GIS shapefiles, reprojects to EPSG:4326 (WGS 84),
simplifies geometries, and uploads the resulting GeoJSON to GCS.

Target layers:

- **WellPaths** — directional / horizontal wellbore path lines
- **WellSurface** — well surface point locations
- **FieldBoundaries** — delineated field boundary polygons
- **Units** — enhanced recovery unit + gas storage unit polygons

```bash
python scripts/process_gis_data.py \
  --project <GCP_PROJECT_ID> \
  --bucket <GCS_BUCKET_NAME> \
  [--gis-prefix gis/] \
  [--simplify-tolerance 0.0001]
```

Also invoked by the `gis_update` Cloud Run Job on a monthly schedule.
