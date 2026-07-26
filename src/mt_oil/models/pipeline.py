import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from mt_oil.config import settings

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


def _storage_client():
    """Return a GCS client scoped to the configured GCP project when available."""
    from google.cloud import storage

    return (
        storage.Client(project=settings.gcp_project_id)
        if settings.gcp_project_id
        else storage.Client()
    )


def _maybe_download_gcs(path: str) -> str:
    """If *path* is a gs:// URI, download it to a temp file and return the local path."""
    if not path.startswith("gs://"):
        return path

    client = _storage_client()
    bucket_name, blob_name = path[5:].split("/", 1)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    suffix = Path(blob_name).suffix or ".joblib"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    blob.download_to_file(tmp)
    tmp.close()
    return tmp.name


def train_and_evaluate(data: pd.DataFrame) -> Pipeline:
    """
    Trains a Random Forest Regressor to predict BOE with Hyperparameter Tuning.

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
    # Added new features: DTD, Lateral_Length, Proppant_Per_Foot, Fluid_Per_Foot, Vintage_Year
    numerical_features = [
        "Lat",
        "Long",
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
    ]

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
            ("num", numerical_transformer, numerical_features),
            ("cat", categorical_transformer, ["Slant"]),
        ]
    )

    # Define the model
    rf = RandomForestRegressor(random_state=42)

    # Create the pipeline
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", rf)])

    # Define Hyperparameters for GridSearch
    # Keeping it relatively small for demo performance
    param_grid = {
        "model__n_estimators": [100, 200],
        "model__max_depth": [None, 10, 20],
        "model__min_samples_split": [2, 5],
    }

    logger.info("Starting GridSearch CV...")
    grid_search = GridSearchCV(
        pipeline, param_grid, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1
    )

    grid_search.fit(X_train, y_train)

    logger.info("Best Parameters: %s", grid_search.best_params_)

    best_model = grid_search.best_estimator_

    # Make predictions
    y_pred = best_model.predict(X_test)

    # Evaluate the model
    mae = mean_absolute_error(y_test, y_pred)
    logger.info("Mean Absolute Error: %f", mae)

    r2 = r2_score(y_test, y_pred)
    logger.info("R^2: %f", r2)

    # Retrain on full dataset with best params
    logger.info("Retraining on full dataset...")
    best_model.fit(X, y)

    return best_model


def save_model(model: Pipeline, path: str = "rf_model.joblib"):
    if path.startswith("gs://"):
        suffix = Path(path).suffix or ".joblib"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            joblib.dump(model, tmp.name)
            local_path = tmp.name

        try:
            client = _storage_client()
            bucket_name, blob_name = path[5:].split("/", 1)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            logger.info("Model uploaded to %s", path)
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
    else:
        joblib.dump(model, path)
        logger.info("Model saved to %s", path)


def load_model(path: str = "rf_model.joblib") -> Pipeline:
    try:
        local_path = _maybe_download_gcs(path)
        if not os.path.exists(local_path):
            logger.warning("Model file not found: %s", path)
            return None
        try:
            return joblib.load(local_path)
        finally:
            # Clean up temp file if we downloaded from GCS.
            if local_path != path and os.path.exists(local_path):
                os.remove(local_path)
    except Exception as e:
        logger.warning("Could not load model from %s: %s", path, e)
        return None
