import pandas as pd
import numpy as np


def preprocess_ff_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses FracFocus data to aggregate proppant and fluid volumes by API Number.

    Args:
        df (pd.DataFrame): Raw FracFocus data.

    Returns:
        pd.DataFrame: Aggregated data indexed by API_WellNo.
    """
    # Drop duplicate reports
    df.drop_duplicates(keep="last", inplace=True)

    # group by API, and get total `Purpose` == 'Proppant' PercentHFJob
    df = df[df.Purpose == "Proppant"]

    df = (
        df.groupby("APINumber")
        .agg(
            {
                "PercentHFJob": "sum",
                "MassIngredient": "sum",
                "TVD": "first",
                "TotalBaseWaterVolume": "first",
                "TotalBaseNonWaterVolume": "first",
            }
        )
        .reset_index()
    )

    # Assume zero values for volume/proppant, etc. are missing
    df.replace(0, np.nan, inplace=True)

    df = df.rename(columns={"APINumber": "API_WellNo"}).set_index("API_WellNo")

    return df


def preprocess_well_data(well_data_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts relevant well header information (Lat, Long, Slant).

    Args:
        well_data_df (pd.DataFrame): Raw well header data.

    Returns:
        pd.DataFrame: Processed well data indexed by API_WellNo.
    """
    # want |API | lat length | formation |
    well_df = well_data_df[["API_WellNo", "Lat", "Long", "Slant"]].set_index(
        "API_WellNo"
    )
    return well_df


def preprocess_prod_data(well_prod_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates cumulative production totals for specified intervals (180, 360, 720 days).
    RESTRICTED TO OIL WELLS Only.

    Args:
        well_prod_df (pd.DataFrame): Raw production data.

    Returns:
        pd.DataFrame: DataFrame containing cumulative production totals, indexed by API_WellNo.
    """
    df = well_prod_df[
        [
            "API_WellNo",
            "Rpt_Date",
            "ST_FMTN_CD",
            "BBLS_OIL_COND",
            "MCF_GAS",
            "BBLS_WTR",
            "DAYS_PROD",
        ]
    ]

    # Calculate cumulative days
    # Need to ensure sorted within groups
    df = df.sort_values(["API_WellNo", "Rpt_Date"])
    df["TOTAL_DAYS"] = df.groupby("API_WellNo")["DAYS_PROD"].cumsum()

    # Vectorized approach
    intervals = [180, 360, 720]
    results = []

    for interval in intervals:
        # Filter for days <= interval
        mask = df["TOTAL_DAYS"] <= interval
        interval_data = df[mask]

        # Group by API and Zone
        grouped = (
            interval_data.groupby(["API_WellNo", "ST_FMTN_CD"])
            .agg({"BBLS_OIL_COND": "sum", "BBLS_WTR": "sum", "MCF_GAS": "sum"})
            .reset_index()
        )

        grouped["Interval"] = interval
        results.append(grouped)

    # Concatenate all intervals
    totals_df = pd.concat(results, axis=0)

    # Rename columns to match expected output format
    totals_df = totals_df.rename(columns={"ST_FMTN_CD": "Zone"})

    totals_df = totals_df[
        ["API_WellNo", "Zone", "Interval", "BBLS_OIL_COND", "BBLS_WTR", "MCF_GAS"]
    ]

    # restrict to oil wells (where oil > 0)
    totals_df = totals_df[(totals_df["BBLS_OIL_COND"]) > 0]

    totals_df = totals_df.set_index("API_WellNo")

    return totals_df


def merge_data(
    totals_df: pd.DataFrame,
    well_df: pd.DataFrame,
    ff_data: pd.DataFrame,
    interval: int = 720,
) -> pd.DataFrame:
    """
    Merges processed production, well, and FracFocus data into a single dataset for modeling.

    Args:
        totals_df (pd.DataFrame): Processed production totals.
        well_df (pd.DataFrame): Processed well header data.
        ff_data (pd.DataFrame): Processed FracFocus data.
        interval (int, optional): The production interval to target (e.g., 720 days). Defaults to 720.

    Returns:
        pd.DataFrame: Merged DataFrame ready for ML pipeline.
    """
    # Filter production data for the specific interval
    prod_data = totals_df[totals_df.Interval == interval]
    prod_data = prod_data[["Zone", "BBLS_OIL_COND", "BBLS_WTR", "MCF_GAS"]]

    # Merge
    # detailed inner join implies we only want wells present in ALL datasets
    data = pd.merge(well_df, prod_data, left_index=True, right_index=True)
    data = pd.merge(data, ff_data, left_index=True, right_index=True)

    # Calculate BOE (Barrel of Oil Equivalent)
    # 5.8 or 6 is standard. Using 5.8 as per original code.
    data["BOE"] = data["BBLS_OIL_COND"] + data["MCF_GAS"] / 5.8

    columns_to_keep = [
        "Zone",
        "Lat",
        "Long",
        "Slant",
        "PercentHFJob",
        "MassIngredient",
        "TVD",
        "TotalBaseWaterVolume",
        "TotalBaseNonWaterVolume",
        "BOE",
    ]

    # Return only keeping columns if they exist (handling potential missing ones gracefully?)
    # For now, strict as per requirement to reproduce functionality.
    data = data[columns_to_keep]

    return data
