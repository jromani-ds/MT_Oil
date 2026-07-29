"""Monthly GIS data refresh job.

Invokes the GIS shapefile-to-GeoJSON pipeline to refresh the 4 GIS layers
(well surfaces, well paths, fields, units) stored in GCS. Designed to run
as a Cloud Run Job on a monthly schedule.

Usage (local):
    python -m mt_oil.jobs.gis_update

Environment variables required:
    GCP_PROJECT_ID   — GCP project ID
    GCS_DATA_BUCKET  — GCS bucket for GIS GeoJSON output
"""

import sys
from pathlib import Path

from mt_oil.config import settings

# Ensure the scripts directory is importable.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def run() -> None:
    print("Starting GIS update job...")
    print(f"  Project: {settings.gcp_project_id}")
    print(f"  Bucket:  {settings.gcs_data_bucket}")

    if not settings.gcp_project_id or not settings.gcs_data_bucket:
        raise EnvironmentError(
            "GCP_PROJECT_ID and GCS_DATA_BUCKET environment variables are required"
        )

    from process_gis_data import process_all

    results = process_all(
        project=settings.gcp_project_id,
        bucket=settings.gcs_data_bucket,
        gis_prefix="gis/",
        simplify_tolerance=0.0001,
    )

    print("\nGIS update complete. Uploaded layers:")
    for layer, url in results.items():
        print(f"  {layer}: {url}")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
