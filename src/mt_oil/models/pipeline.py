from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import pandas as pd


def train_and_evaluate(data: pd.DataFrame) -> Pipeline:
    """
    Trains a Random Forest Regressor to predict BOE.

    Args:
        data (pd.DataFrame): The feature dataset including target 'BOE'.

    Returns:
        Pipeline: The trained Scikit-Learn pipeline.
    """
    X = data.drop("BOE", axis=1)
    y = data["BOE"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

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

    # Create the pipeline
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])

    # Train the model
    print("Training model...")
    pipeline.fit(X_train, y_train)

    # Make predictions
    y_pred = pipeline.predict(X_test)

    # Evaluate the model
    mae = mean_absolute_error(y_test, y_pred)
    print(f"Mean Absolute Error: {mae}")

    r2 = r2_score(y_test, y_pred)
    print(f"R^2: {r2}")

    # Retrain on full dataset
    print("Retraining on full dataset...")
    pipeline.fit(X, y)

    return pipeline
