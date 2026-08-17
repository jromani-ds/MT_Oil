import zipfile
from urllib.request import urlopen
import shutil
import os
import fnmatch
import pandas as pd
from typing import Tuple


def pull_prod_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retrieves well and lease production data from the Montana Board of Oil and Gas Conservation.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - lease_prod_df: DataFrame containing lease production data.
            - well_prod_df: DataFrame containing well production data.
    """
    url = "https://bogfiles.dnrc.mt.gov//Reporting/Production/Historical/MT_Historical_Production.zip"
    file_name = "MT_Historical_Production.zip"

    try:
        # Check if extracted files already exist
        if os.path.exists("MT_HistoricalPRUProduction.tab") and os.path.exists(
            "MT_HistoricalWellProduction.tab"
        ):
            print("Production data files found locally. Skipping download.")
        else:
            print("Downloading production data...")
            # extracting zipfile from URL
            with urlopen(url) as response, open(file_name, "wb") as out_file:
                shutil.copyfileobj(response, out_file)

            # extracting required file from zipfile
            with zipfile.ZipFile(file_name) as zf:
                zf.extract("MT_HistoricalPRUProduction.tab")
                zf.extract("MT_HistoricalWellProduction.tab")

        # loading data from the file
        print("Loading production data into DataFrames...")
        lease_prod_df = pd.read_csv(
            "MT_HistoricalPRUProduction.tab", sep="\t", low_memory=False
        )
        well_prod_df = pd.read_csv(
            "MT_HistoricalWellProduction.tab", sep="\t", low_memory=False
        )

        return lease_prod_df, well_prod_df

    finally:
        # Cleanup zip only if it exists
        if os.path.exists(file_name):
            os.remove(file_name)


def pull_well_data() -> pd.DataFrame:
    """
    Retrieves well header data from the Montana Board of Oil and Gas Conservation.

    Returns:
        pd.DataFrame: DataFrame containing well header information (Lat, Long, etc).
    """
    url = "https://bogfiles.dnrc.mt.gov//Reporting/Wells/MT_CompleteWellList.zip"
    file_name = "MT_CompleteWellList.zip"

    try:
        # extracting zipfile from URL
        with urlopen(url) as response, open(file_name, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

        # extracting required file from zipfile
        with zipfile.ZipFile(file_name) as zf:
            zf.extract("MT_HistoricalWellList.tab")

        # loading data from the file
        well_data_df = pd.read_csv(
            "MT_HistoricalWellList.tab", sep="\t", low_memory=False
        )

        return well_data_df

    finally:
        if os.path.exists(file_name):
            os.remove(file_name)


def pull_ff_data(
    state_name: str = "Montana", keep_zip: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retrieves FracFocus registry data for a single state.

    Args:
        state_name (str): Name of the state to filter data for. Defaults to "Montana".
        keep_zip (bool): If True, leave the downloaded FracFocusCSV.zip on disk so
            callers (e.g. the Cloud Run Job) can archive it to GCS. Defaults to False.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - FracFocusRegistry_df: Registry data.
            - registryupload_df: Empty placeholder kept for backwards compatibility.
    """
    url = "https://www.fracfocusdata.org/digitaldownload/FracFocusCSV.zip"
    file_name = "FracFocusCSV.zip"
    # Only the columns needed by preprocess_ff_data are loaded, which keeps the
    # memory footprint small enough to run in a 4 GiB Cloud Run Job container.
    registry_cols = {
        "APINumber",
        "StateName",
        "Purpose",
        "PercentHFJob",
        "MassIngredient",
        "TVD",
        "TotalBaseWaterVolume",
        "TotalBaseNonWaterVolume",
        # Expanded for ingredient-level classification
        "CASNumber",
        "IngredientName",
        "Supplier",
        "TradeName",
        "IngredientMass",
        "IngredientPercentHFJob",
        "CalculationType",
        "JobStartDate",
        "JobEndDate",
        "OperatorName",
        "WellName",
        "IngredientComment",
    }
    required_cols = {"APINumber", "Purpose", "MassIngredient"}
    chunksize = 200_000

    try:
        print("Downloading FracFocus data...")
        with urlopen(url) as response, open(file_name, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

        registry_chunks: list[pd.DataFrame] = []
        with zipfile.ZipFile(file_name) as zip_file:
            registry_files = [
                info
                for info in zip_file.infolist()
                if fnmatch.fnmatch(info.filename, "FracFocusRegistry*.csv")
            ]

            if not registry_files:
                raise ValueError("No FracFocus registry CSVs found in archive")

            for info in registry_files:
                print(f"Reading {info.filename}...")
                with zip_file.open(info.filename) as f:
                    for chunk in pd.read_csv(
                        f,
                        low_memory=False,
                        chunksize=chunksize,
                        usecols=lambda col: col in registry_cols,
                    ):
                        if state_name and "StateName" in chunk.columns:
                            chunk = chunk[chunk["StateName"] == state_name]
                        registry_chunks.append(chunk)

        if not registry_chunks:
            raise ValueError("No FracFocus data chunks found")

        registry_df = pd.concat(registry_chunks, ignore_index=True)
        missing = required_cols - set(registry_df.columns)
        if missing:
            raise ValueError(f"Required columns missing from FracFocus data: {missing}")

        return registry_df, pd.DataFrame()

    finally:
        if not keep_zip and os.path.exists(file_name):
            os.remove(file_name)
