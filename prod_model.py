# stub for ml model pipeline

import pandas as pd
import numpy as np


def preprocess_ff_data(df):
    # stub for FF data

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


def preprocess_well_data(well_data_df):
    # gets us the stuff we need to know about the well
    # to predict the production

    # want |API | lat length | formation |

    well_df = well_data_df[["API_WellNo", "Lat", "Long", "Slant"]].set_index(
        "API_WellNo"
    )

    return well_df


def preprocess_prod(well_prod_df):
    # allows us to preprocess the production data
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
    df["TOTAL_DAYS"] = df.groupby("API_WellNo")["DAYS_PROD"].cumsum()

    # Initialize a dictionary to store the totals
    totals = {}

    # Define the intervals
    intervals = [180, 360, 720]

    # Loop through each factory and interval to calculate total output
    for well in df["API_WellNo"].unique():
        well_df = df[df["API_WellNo"] == well]

        for zone in well_df["ST_FMTN_CD"].unique():
            zone_df = well_df[well_df["ST_FMTN_CD"] == zone]
            zone_output = 0
            for interval in intervals:
                interval_oil = zone_df[zone_df["TOTAL_DAYS"] <= interval][
                    "BBLS_OIL_COND"
                ].sum()
                interval_water = zone_df[zone_df["TOTAL_DAYS"] <= interval][
                    "BBLS_WTR"
                ].sum()
                interval_gas = zone_df[zone_df["TOTAL_DAYS"] <= interval][
                    "MCF_GAS"
                ].sum()
                totals[(well, zone, interval)] = [
                    interval_oil,
                    interval_gas,
                    interval_water,
                ]

    # Convert totals dictionary to a DataFrame for better visualization
    totals_df = pd.DataFrame(
        list(totals.items()), columns=["API-Interval", "Total Output"]
    )
    totals_df[["API_WellNo", "Zone", "Interval"]] = pd.DataFrame(
        totals_df["API-Interval"].tolist(), index=totals_df.index
    )
    totals_df[["BBLS_OIL_COND", "BBLS_WTR", "MCF_GAS"]] = pd.DataFrame(
        totals_df["Total Output"].tolist(), index=totals_df.index
    )
    totals_df = totals_df[
        ["API_WellNo", "Zone", "Interval", "BBLS_OIL_COND", "BBLS_WTR", "MCF_GAS"]
    ]

    # restrict to oil wells
    totals_df = totals_df[(totals_df["BBLS_OIL_COND"]) > 0]

    totals_df = totals_df.set_index("API_WellNo")

    return totals_df


def data_merge(totals_df, well_df, ff_data, interval=720):
    # stub to merge well, prod, and ff data

    # merge well data, production data, and ff data
    prod_data = totals_df[totals_df.Interval == interval]
    prod_data = prod_data[["Zone", "BBLS_OIL_COND", "BBLS_WTR", "MCF_GAS"]]

    data = pd.merge(well_df, prod_data, left_index=True, right_index=True)
    data = pd.merge(data, ff_data, left_index=True, right_index=True)

    data["BOE"] = data["BBLS_OIL_COND"] + data["MCF_GAS"] / 5.8

    data = data[
        [
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
    ]
    return data


def model_pipeline(data):

    from sklearn.model_selection import train_test_split
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler, OneHotEncoder
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score

    X = data.drop("BOE", axis=1)
    y = data["BOE"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 3. Pipeline Setup
    # Preprocessing for numerical data
    numerical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="mean")),
            ("scaler", StandardScaler()),
        ]
    )

    # Preprocessing for categorical data
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    # Bundle preprocessing for numerical and categorical data
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                numerical_transformer,
                [
                    "Lat",
                    "Long",
                    "PercentHFJob",
                    "MassIngredient",
                    "TVD",
                    "TotalBaseWaterVolume",
                    "TotalBaseNonWaterVolume",
                ],
            ),
            ("cat", categorical_transformer, ["Slant"]),
        ]
    )

    # Define the model
    model = RandomForestRegressor(n_estimators=100, random_state=42)

    # Create and evaluate the pipeline
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])

    # 4. Training and Prediction
    # Train the model
    pipeline.fit(X_train, y_train)

    # Make predictions
    y_pred = pipeline.predict(X_test)

    # Evaluate the model
    mse = mean_absolute_error(y_test, y_pred)
    print(f"Mean Absolute Error: {mse}")

    r2 = r2_score(y_test, y_pred)
    print(f"R^2: {r2}")


if __name__ == "__main__":
    from pull_data import pull_ff_data, pull_prod_data, pull_well_data

    # Pull Data
    lease_prod_df, well_prod_df = pull_prod_data()
    well_data_df = pull_well_data()
    FracFocusRegistry_df_MT, registryupload_df_MT = pull_ff_data(state_name="Montana")

    # data preprocessing
    ff_data = preprocess_ff_data(FracFocusRegistry_df_MT)
    well_df = preprocess_well_data(well_data_df)
    totals_df = preprocess_prod(well_prod_df)
    data = data_merge(totals_df, well_df, ff_data, interval=720)

    # ML pipeline
    model_pipeline(data)
