"""Download, reproject, simplify, and upload Montana MBOGC GIS shapefiles as GeoJSON.

Downloads shapefile ZIPs from the Montana Board of Oil and Gas Conservation GIS
repository, reprojects them to EPSG:4326 (WGS 84), simplifies polygon geometries
to reduce payload size, and uploads the resulting GeoJSON FeatureCollections to
a GCS bucket.

Target files (from https://bogwebfiles.dnrc.mt.gov/GISData/):
    - WellPaths.zip   (directional / horizontal wellbore path lines)
    - Wells.zip       (surface point locations)
    - delineatedfields.zip (field boundary polygons)
    - units.zip       (enhanced recovery unit polygons)
    - gstUnits.zip    (gas storage unit polygons — merged into units)

Usage:
    python scripts/process_gis_data.py \\
        --project <GCP_PROJECT_ID> \\
        --bucket <GCS_BUCKET_NAME> \\
        [--gis-prefix gis/] \\
        [--simplify-tolerance 0.0001]
"""

import argparse
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
from google.cloud import storage

GIS_BASE_URL = "https://bogwebfiles.dnrc.mt.gov/GISData/"

TARGET_ZIPS: dict[str, str] = {
    "WellPaths.zip": "well_paths",
    "Wells.zip": "wells_surfaces",
    "delineatedfields.zip": "fields",
    "units.zip": "units",
    "gstUnits.zip": "units_gst",
}

OUTPUT_NAMES: dict[str, str] = {
    "well_paths": "gis/well_paths.json",
    "wells_surfaces": "gis/wells_surfaces.json",
    "fields": "gis/fields.json",
    "units": "gis/units.json",
}


def _download_zip(url: str, dest_dir: Path) -> Path:
    """Download a ZIP from *url* into *dest_dir* and return the local path."""
    filename = url.rsplit("/", 1)[-1]
    local_path = dest_dir / filename
    if local_path.exists():
        print(f"  {filename} already cached, skipping download.")
        return local_path
    print(f"  Downloading {filename}...")
    import urllib.request
    import shutil

    with urllib.request.urlopen(url) as response, open(local_path, "wb") as f:
        shutil.copyfileobj(response, f)
    return local_path


def _read_shapefile_from_zip(
    zip_path: Path, layer_name: str | None = None
) -> gpd.GeoDataFrame:
    """Read the first shapefile found inside *zip_path*."""
    with zipfile.ZipFile(zip_path) as zf:
        shp_files = [n for n in zf.namelist() if n.endswith(".shp")]
        if not shp_files:
            raise ValueError(f"No .shp file found in {zip_path}")
        with tempfile.TemporaryDirectory() as tmp:
            zf.extractall(tmp)
            gdf = gpd.read_file(Path(tmp) / shp_files[0], layer=layer_name)
    return gdf


def _reproject_to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Reproject to EPSG:4326 (WGS 84) if not already in that CRS."""
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        print(f"    Reprojecting from {gdf.crs or 'unknown'} to EPSG:4326...")
        gdf = gdf.to_crs(epsg=4326)
    return gdf


def _simplify_geometries(
    gdf: gpd.GeoDataFrame, tolerance: float = 0.0001
) -> gpd.GeoDataFrame:
    """Simplify polygon/line geometries to reduce GeoJSON payload size.

    *tolerance* of 0.0001 degrees is roughly 10 metres — a good balance for
    state-wide field/unit boundaries on a zoomable web map.
    """
    geom_types = gdf.geometry.type.unique()
    if any(
        t in ("Polygon", "MultiPolygon", "LineString", "MultiLineString")
        for t in geom_types
    ):
        print(f"    Simplifying geometry (tolerance={tolerance})...")
        gdf = gdf.copy()
        gdf["geometry"] = gdf.geometry.simplify(tolerance, preserve_topology=True)
    return gdf


def _filter_active_records(gdf: gpd.GeoDataFrame, dataset: str) -> gpd.GeoDataFrame:
    """Drop inactive or historical-only records based on known column conventions."""
    status_cols = [
        c for c in gdf.columns if c.lower() in ("status", "active", "inactive")
    ]
    if status_cols:
        col = status_cols[0]
        before = len(gdf)
        gdf = gdf[
            gdf[col].astype(str).str.lower().isin(("active", "true", "1", "y", "yes"))
        ].copy()
        after = len(gdf)
        if after < before:
            print(f"    Filtered inactive records: {before} -> {after}")
    return gdf


def _merge_gst_units(units_dir: Path, gst_zip: Path) -> gpd.GeoDataFrame | None:
    """Merge gstUnits into the main units dataset if both exist."""
    print("  Merging gstUnits into units...")
    if not gst_zip.exists():
        print("    gstUnits.zip not found, skipping merge.")
        return None
    try:
        gst_gdf = _read_shapefile_from_zip(gst_zip)
        gst_gdf = _reproject_to_wgs84(gst_gdf)
        gst_gdf = _simplify_geometries(gst_gdf)
        return gst_gdf
    except Exception as e:
        print(f"    Failed to merge gstUnits: {e}")
        return None


def _upload_to_gcs(
    local_path: Path,
    bucket_name: str,
    blob_name: str,
    project: str,
    cache_control: str = "public, max-age=3600",
) -> str:
    """Upload a file to GCS and return its public URL."""
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.cache_control = cache_control
    blob.content_type = "application/geo+json"
    blob.upload_from_filename(str(local_path))
    public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    print(f"    Uploaded -> {public_url}")
    return public_url


def process_all(
    project: str,
    bucket: str,
    gis_prefix: str = "gis/",
    simplify_tolerance: float = 0.0001,
    work_dir: str | None = None,
) -> dict[str, str]:
    """Run the full pipeline and return a dict of layer_name -> GCS URL."""
    if work_dir:
        base = Path(work_dir)
        base.mkdir(parents=True, exist_ok=True)
    else:
        base = Path(tempfile.mkdtemp(prefix="mt_oil_gis_"))

    download_dir = base / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, str] = {}

    for zip_name, dataset_key in TARGET_ZIPS.items():
        print(f"\n=== Processing {zip_name} ({dataset_key}) ===")

        url = f"{GIS_BASE_URL}{zip_name}"
        zip_path = _download_zip(url, download_dir)

        gdf = _read_shapefile_from_zip(zip_path)
        print(f"    Loaded {len(gdf):,} features, columns={list(gdf.columns)}")

        gdf = _reproject_to_wgs84(gdf)
        gdf = _simplify_geometries(gdf, tolerance=simplify_tolerance)
        gdf = _filter_active_records(gdf, dataset_key)

        # Merge gstUnits into units if applicable
        if dataset_key == "units":
            gst_zip = download_dir / "gstUnits.zip"
            gst_gdf = _merge_gst_units(download_dir, gst_zip)
            if gst_gdf is not None:
                print(f"    Merged {len(gst_gdf):,} gas storage unit features.")
                common_cols = list(set(gdf.columns) & set(gst_gdf.columns))
                if "geometry" not in common_cols:
                    common_cols.append("geometry")
                gdf = pd.concat(
                    [gdf[common_cols], gst_gdf[common_cols]],
                    ignore_index=True,
                )
                print(f"    Combined units: {len(gdf):,} features.")

        # Determine output filename
        output_key = dataset_key
        if dataset_key == "units_gst":
            continue  # already merged above
        blob_name = OUTPUT_NAMES.get(output_key, f"gis/{output_key}.json")
        local_output = output_dir / f"{output_key}.json"

        gdf.to_file(local_output, driver="GeoJSON")
        print(f"    Wrote {local_output} ({local_output.stat().st_size / 1024:.1f} KB)")

        url = _upload_to_gcs(local_output, bucket, blob_name, project)
        results[output_key] = url

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process MBOGC GIS shapefiles to optimized GeoJSON and upload to GCS."
    )
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument(
        "--bucket", required=True, help="GCS bucket name (e.g. my-project-mt-oil-dev)"
    )
    parser.add_argument(
        "--gis-prefix", default="gis/", help="GCS prefix for GeoJSON files"
    )
    parser.add_argument(
        "--simplify-tolerance",
        type=float,
        default=0.0001,
        help="Geometry simplification tolerance in degrees (~10m default)",
    )
    parser.add_argument(
        "--work-dir",
        default=None,
        help="Working directory for downloads/outputs (default: temp dir)",
    )
    args = parser.parse_args()

    print("Starting GIS data processing pipeline...")
    print(f"  Project: {args.project}")
    print(f"  Bucket:  {args.bucket}")
    print(f"  Prefix:  {args.gis_prefix}")

    results = process_all(
        project=args.project,
        bucket=args.bucket,
        gis_prefix=args.gis_prefix,
        simplify_tolerance=args.simplify_tolerance,
        work_dir=args.work_dir,
    )

    print("\n=== Pipeline Complete ===")
    for layer, url in results.items():
        print(f"  {layer}: {url}")


if __name__ == "__main__":
    main()
