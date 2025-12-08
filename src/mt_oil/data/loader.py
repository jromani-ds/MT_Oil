import zipfile
from urllib.request import urlopen
import shutil
import os
import pandas as pd
from typing import Tuple, Dict


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


def pull_ff_data(state_name: str = "Montana") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Retrieves FracFocus data.

    Args:
        state_name (str): Name of the state to filter data for. Defaults to "Montana".

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]:
            - FracFocusRegistry_df: Registry data.
            - registryupload_df: Registry upload data.
    """
    url = "https://www.fracfocusdata.org/digitaldownload/FracFocusCSV.zip"
    file_name = "FracFocusCSV.zip"

    try:
        # extracting zipfile from URL
        with urlopen(url) as response, open(file_name, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

        # extracting required files from zipfile and put in dictionary
        with zipfile.ZipFile(file_name) as zip_file:
            dfs: Dict[str, pd.DataFrame] = {
                csv_file.filename: pd.read_csv(
                    zip_file.open(csv_file.filename), low_memory=False
                )
                for csv_file in zip_file.infolist()
                if csv_file.filename.endswith(".csv")
            }

        registryupload_keys = [item for item in list(dfs.keys()) if "Frac" not in item]
        registryupload_dict = {x: dfs[x] for x in registryupload_keys}
        registryupload_df = pd.concat(registryupload_dict, axis=0)

        FracFocusRegistry_keys = [
            item for item in list(dfs.keys()) if "registryupload" not in item
        ]
        FracFocusRegistry_dict = {x: dfs[x] for x in FracFocusRegistry_keys}
        FracFocusRegistry_df = pd.concat(FracFocusRegistry_dict, axis=0)

        if state_name:
            FracFocusRegistry_df = FracFocusRegistry_df[
                FracFocusRegistry_df["StateName"] == state_name
            ]
            registryupload_df = registryupload_df[
                registryupload_df["StateName"] == state_name
            ]

        return FracFocusRegistry_df, registryupload_df

    finally:
        if os.path.exists(file_name):
            os.remove(file_name)
