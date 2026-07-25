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
    Extracts relevant well header information (Lat, Long, Slant, DTD).

    Args:
        well_data_df (pd.DataFrame): Raw well header data.

    Returns:
        pd.DataFrame: Processed well data indexed by API_WellNo.
    """
    # want |API | lat length | formation | type | DTD |
    # Adding 'Type' to support filtering
    # Adding 'DTD' (Driller's Total Depth) for lateral length calculation
    well_df = well_data_df[
        ["API_WellNo", "Lat", "Long", "Slant", "Type", "DTD"]
    ].set_index("API_WellNo")
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
    df["Rpt_Date"] = pd.to_datetime(df["Rpt_Date"])  # Ensure datetime
    df = df.sort_values(["API_WellNo", "Rpt_Date"])
    df["TOTAL_DAYS"] = df.groupby("API_WellNo")["DAYS_PROD"].cumsum()

    # Get First Prod Date per well
    first_dates = df.groupby("API_WellNo")["Rpt_Date"].min().reset_index()
    first_dates.rename(columns={"Rpt_Date": "First_Prod_Date"}, inplace=True)

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

    # Merge First Prod Date back to totals
    totals_df = pd.merge(totals_df, first_dates, on="API_WellNo", how="left")

    # Rename columns to match expected output format
    totals_df = totals_df.rename(columns={"ST_FMTN_CD": "Zone"})

    totals_df = totals_df[
        [
            "API_WellNo",
            "Zone",
            "Interval",
            "BBLS_OIL_COND",
            "BBLS_WTR",
            "MCF_GAS",
            "First_Prod_Date",
        ]
    ]

    # restrict to oil wells (where oil > 0)
    totals_df = totals_df[(totals_df["BBLS_OIL_COND"]) > 0]

    totals_df = totals_df.set_index("API_WellNo")

    return totals_df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates new features for the ML model with robust cleansing.
    """
    # 1. Lateral Length Proxy (DTD - TVD)
    # Fill missing TVD or DTD with 0 for safety before calc
    df["TVD"] = df["TVD"].fillna(0)
    df["DTD"] = df["DTD"].fillna(0)

    # Calculate Lat Len ONLY for Horizontal wells
    # If Slant is not horizontal, Lateral Length should logically be 0 or small for completion intensity calc?
    # Or we treat vertical wells differently.
    # For vertical, intensity is per foot of perforation interval, which we don't strictly have.
    # We'll set Lateral_Length to 0 for non-horizontal to distinguish, or minimal value to avoid div/0.

    # Normalize Slant text
    if "Slant" in df.columns:
        is_horizontal = df["Slant"].str.contains("Horizontal", case=False, na=False)
    else:
        is_horizontal = pd.Series([False] * len(df), index=df.index)

    df["Lateral_Length"] = df["DTD"] - df["TVD"]

    # Apply Horizontal mask: If not horizontal, Lateral Length = 0 (or we could set to NaN)
    df.loc[~is_horizontal, "Lateral_Length"] = 0

    # Outlier / Physics Check for Lateral Length
    # Typical extended reach is < 15,000 ft. Minimum economic lateral ~1,000 ft.
    # We clip or mask. Masking (setting to NaN/0) removes them from intensity calculation validity.
    # User said: "cleanse items that are physical impossibilities"
    valid_lateral = (df["Lateral_Length"] >= 1000) & (df["Lateral_Length"] <= 15000)
    df.loc[~valid_lateral, "Lateral_Length"] = 0  # Invalid calculation

    # 2. Completion Intensity
    # Avoid division by zero
    # Use a small epsilon or mask
    has_lat_len = df["Lateral_Length"] > 0

    df["Proppant_Per_Foot"] = 0.0
    df["Fluid_Per_Foot"] = 0.0

    df.loc[has_lat_len, "Proppant_Per_Foot"] = (
        df.loc[has_lat_len, "MassIngredient"] / df.loc[has_lat_len, "Lateral_Length"]
    )
    df.loc[has_lat_len, "Fluid_Per_Foot"] = (
        df.loc[has_lat_len, "TotalBaseWaterVolume"]
        / df.loc[has_lat_len, "Lateral_Length"]
    )

    # 3. Physical Check: Sand Fraction
    # Volume of Sand (gal) = Mass (lbs) / 22.1 (lbs/gal, approx density of quartz sand)
    # Total Volume (gal) approx = Water Volume + Sand Volume
    # Fraction = Sand Vol / Total Vol. Should be < 20% (0.2).
    # MassIngredient is in Lbs. Water is in Gallons.

    sand_density_ppg = 22.1
    sand_vol_gal = df["MassIngredient"] / sand_density_ppg
    total_vol_estimate = df["TotalBaseWaterVolume"] + sand_vol_gal

    sand_fraction = sand_vol_gal / total_vol_estimate

    # Mark rows with physically impossible sand fraction as invalid (set intensity features to 0 or NaN)
    # User said: "cleanse items".
    bad_sand = (sand_fraction > 0.25) | (
        sand_fraction < 0
    )  # Allow slightly over 20% for safety margin, say 25%

    # Nullify intensities for bad sand data
    df.loc[bad_sand, "Proppant_Per_Foot"] = 0
    df.loc[bad_sand, "Fluid_Per_Foot"] = 0

    # Also clean extreme intensity values directly just in case headers were wrong
    # > 5000 lbs/ft is very rare/high. > 100 bbl/ft (4200 gal/ft) is high.
    df.loc[df["Proppant_Per_Foot"] > 5000, "Proppant_Per_Foot"] = 0
    df.loc[df["Fluid_Per_Foot"] > 5000, "Fluid_Per_Foot"] = 0

    # 3. Vintage Bins
    if "First_Prod_Date" in df.columns:
        df["First_Prod_Date"] = pd.to_datetime(df["First_Prod_Date"])
        df["Vintage_Year"] = df["First_Prod_Date"].dt.year
    else:
        df["Vintage_Year"] = 2020  # Default to modern era if unknown for new wells

    # 4. Handle outliers/infinite final cleanup
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df["Proppant_Per_Foot"] = df["Proppant_Per_Foot"].fillna(0)
    df["Fluid_Per_Foot"] = df["Fluid_Per_Foot"].fillna(0)
    df["Vintage_Year"] = df["Vintage_Year"].fillna(2020)

    return df


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
    prod_data = prod_data[
        ["Zone", "BBLS_OIL_COND", "BBLS_WTR", "MCF_GAS", "First_Prod_Date"]
    ]

    # Merge
    # detailed inner join implies we only want wells present in ALL datasets
    data = pd.merge(well_df, prod_data, left_index=True, right_index=True)
    data = pd.merge(data, ff_data, left_index=True, right_index=True)

    # Calculate BOE (Barrel of Oil Equivalent)
    # 5.8 or 6 is standard. Using 5.8 as per original code.
    data["BOE"] = data["BBLS_OIL_COND"] + data["MCF_GAS"] / 5.8

    # Feature Engineering
    data = engineer_features(data)

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
        "DTD",
        "Lateral_Length",
        "Proppant_Per_Foot",
        "Fluid_Per_Foot",
        "Vintage_Year",
        "BOE",
    ]

    # Return only keeping columns if they exist (handling potential missing ones gracefully?)
    # For now, strict as per requirement to reproduce functionality.
    # Ensure all columns exist
    for col in columns_to_keep:
        if col not in data.columns:
            data[col] = 0

    data = data[columns_to_keep]

    return data
