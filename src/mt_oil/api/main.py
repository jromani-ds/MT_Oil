from fastapi import FastAPI, HTTPException, Query, Path, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import pandas as pd
import numpy as np
from contextlib import asynccontextmanager

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from mt_oil.config import settings, logger
from mt_oil.data.loader import pull_well_data, pull_prod_data, pull_ff_data
from mt_oil.data.bigquery_loader import (
    load_all_from_bigquery,
    BigQueryDataLoader,
)
from mt_oil.processing.features import (
    preprocess_well_data,
    preprocess_prod_data,
    preprocess_ff_data,
    merge_data,
)
from mt_oil.domain.decline_curve import fit_best_decline, arps_decline, duong_decline
from mt_oil.domain.economics import calculate_npv
from mt_oil.models.pipeline import train_and_evaluate, load_model, save_model


def _rate_limit_key(request: Request) -> str:
    """Use the first X-Forwarded-For IP when behind Cloud Run, falling back to the direct client host."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_limit_key)


# Global Data Cache
class DataStore:
    well_df: Optional[pd.DataFrame] = None
    producing_wells_set: Optional[set] = None
    ml_model: Optional[object] = None
    is_training: bool = False
    totals_df: Optional[pd.DataFrame] = None
    # Backward compat: populated in local-dev mode, None in BigQuery mode
    prod_df: Optional[pd.DataFrame] = None
    ff_df: Optional[pd.DataFrame] = None
    merged_df: Optional[pd.DataFrame] = None

    def bq_available(self) -> bool:
        return (
            not settings.enable_local_data
            and bool(settings.gcp_project_id)
            and bool(settings.bigquery_dataset)
        )


db = DataStore()
_bq_loader: Optional[BigQueryDataLoader] = None


def _get_bq_loader() -> BigQueryDataLoader:
    global _bq_loader
    if _bq_loader is None and db.bq_available():
        _bq_loader = BigQueryDataLoader(
            settings.gcp_project_id, settings.bigquery_dataset
        )
    return _bq_loader


def _fetch_production_from_bq(api_number: str) -> list:
    loader = _get_bq_loader()
    if loader is None:
        raise HTTPException(status_code=503, detail="Data source not available")
    df = loader.load_production_for_well(api_number)
    if df.empty:
        return []
    result = df[
        ["Rpt_Date", "BBLS_OIL_COND", "MCF_GAS", "BBLS_WTR", "DAYS_PROD"]
    ].copy()
    result = result.fillna(0).replace([np.inf, -np.inf], 0)
    result["Rpt_Date"] = pd.to_datetime(result["Rpt_Date"])
    result = result.sort_values("Rpt_Date")
    return result.to_dict(orient="records")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.skip_data_load:
        logger.info("[SKIP_DATA_LOAD] Skipping data load for tests.")
        yield
        return

    use_bq = (
        not settings.enable_local_data
        and settings.gcp_project_id
        and settings.bigquery_dataset
    )

    logger.info(
        "[%s] Loading well headers... (BigQuery=%s)", settings.environment, use_bq
    )
    try:
        if use_bq:
            raw_well, db.producing_wells_set = load_all_from_bigquery(
                settings.gcp_project_id, settings.bigquery_dataset
            )
            logger.info(
                "Loaded %s wells. %s producing wells.",
                len(raw_well),
                len(db.producing_wells_set),
            )
        else:
            raw_well = pull_well_data()
            _, raw_prod = pull_prod_data()
            raw_ff, _ = pull_ff_data()

            if raw_ff is not None:
                raw_ff["APINumber"] = raw_ff["APINumber"].astype(str)
                db.ff_df = preprocess_ff_data(raw_ff)

            raw_prod["API_WellNo"] = raw_prod["API_WellNo"].astype(str)
            db.prod_df = raw_prod.set_index("API_WellNo").sort_index()

            sums = db.prod_df.groupby(level=0)[["BBLS_OIL_COND", "MCF_GAS"]].sum()
            producing = sums[(sums["BBLS_OIL_COND"] > 0) | (sums["MCF_GAS"] > 0)]
            db.producing_wells_set = set(producing.index)

        db.well_df = preprocess_well_data(raw_well)
        db.well_df.index = db.well_df.index.astype(str)

        if use_bq:
            fmtn_map = raw_well[["API_WellNo", "Formation"]].set_index("API_WellNo")
            db.well_df = db.well_df.join(fmtn_map)
            db.well_df["Formation"] = (
                db.well_df["Formation"].astype(object).fillna("Unknown")
            )
            db.well_df = db.well_df.rename(columns={"Formation": "ST_FMTN_CD"})
        else:
            prod_reset = db.prod_df.reset_index()
            unique_fmtn = (
                prod_reset[["API_WellNo", "ST_FMTN_CD"]]
                .drop_duplicates("API_WellNo")
                .set_index("API_WellNo")
            )
            db.well_df = db.well_df.join(unique_fmtn)
            db.well_df["ST_FMTN_CD"] = db.well_df["ST_FMTN_CD"].fillna("Unknown")

        if not use_bq:
            db.totals_df = preprocess_prod_data(raw_prod)
            db.totals_df.index = db.totals_df.index.astype(str)

            if db.ff_df is not None and not db.ff_df.empty:
                try:
                    logger.info("Merging datasets for ML features...")
                    db.ff_df.index = db.ff_df.index.astype(str)
                    db.merged_df = merge_data(
                        db.totals_df, db.well_df, db.ff_df, interval=720
                    )
                    logger.info("%s wells with full ML features.", len(db.merged_df))
                except Exception as e:
                    logger.warning("ML feature merge failed: %s", e)
                    db.merged_df = None

        logger.info("Loading ML Model from %s...", settings.model_path)
        db.ml_model = load_model(settings.model_path)
        if db.ml_model:
            logger.info("ML Model loaded successfully.")
        else:
            logger.warning("No trained ML model found. Use /train endpoint to train.")

        logger.info(
            "Data Loaded: %s wells. %s producing wells.",
            len(db.well_df),
            len(db.producing_wells_set),
        )
    except Exception as e:
        logger.error("Error loading data: %s", e)
        raise

    yield

    db.well_df = None
    db.prod_df = None
    db.totals_df = None
    db.ff_df = None
    db.merged_df = None
    db.ml_model = None
    db.producing_wells_set = None


app = FastAPI(title="MT Oil API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=("*" not in settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@limiter.limit(settings.rate_limit)
def health_check(request: Request):
    return {
        "status": "ok",
        "environment": settings.environment,
        "bigquery_enabled": db.bq_available(),
        "wells_loaded": len(db.well_df) if db.well_df is not None else 0,
        "producing_wells": len(db.producing_wells_set) if db.producing_wells_set else 0,
        "ml_model_loaded": db.ml_model is not None,
    }


@app.get("/filters")
@limiter.limit(settings.rate_limit)
def get_filter_options(request: Request):
    if db.well_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    return {
        "formations": sorted(db.well_df["ST_FMTN_CD"].unique().tolist()),
        "well_types": sorted(db.well_df["Type"].unique().tolist()),
        "slants": sorted(db.well_df["Slant"].unique().tolist()),
    }


@app.get("/wells")
@limiter.limit(settings.rate_limit)
def get_wells(
    request: Request,
    limit: int = 100,
    skip: int = 0,
    has_production: bool = False,
    formation: Optional[str] = None,
    well_type: Optional[str] = None,
    slant: Optional[str] = None,
):
    if db.well_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    df = db.well_df.reset_index()

    if has_production:
        if db.producing_wells_set is None:
            raise HTTPException(status_code=503, detail="Production data not loaded")
        df = df[df["API_WellNo"].isin(db.producing_wells_set)]

    if formation:
        df = df[df["ST_FMTN_CD"] == formation]
    if well_type:
        df = df[df["Type"] == well_type]
    if slant:
        df = df[df["Slant"] == slant]

    filtered = df.iloc[skip:] if limit <= 0 else df.iloc[skip : skip + limit]
    filtered = filtered.replace([np.inf, -np.inf, np.nan], None)
    return filtered.to_dict(orient="records")


@app.get("/wells/{api_number}")
@limiter.limit(settings.rate_limit)
def get_well_details(
    request: Request, api_number: str = Path(..., title="API Well Number")
):
    if db.well_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    if api_number not in db.well_df.index:
        raise HTTPException(status_code=404, detail="Well not found")

    well = (
        db.well_df.loc[[api_number]]
        .replace([np.inf, -np.inf, np.nan], None)
        .iloc[0]
        .to_dict()
    )
    well["API_WellNo"] = api_number
    return well


@app.get("/wells/{api_number}/wellfile")
@limiter.limit(settings.rate_limit)
def get_wellfile_url(
    request: Request, api_number: str = Path(..., title="API Well Number")
):
    if db.well_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    if api_number not in db.well_df.index:
        raise HTTPException(status_code=404, detail="Well not found")

    clean = api_number.strip()[:10]
    state_url = settings.wellfile_state_url_template.format(api_number=clean)
    gcs_url = (
        f"https://storage.googleapis.com/{settings.gcs_data_bucket}"
        f"/wells/pdfs/{api_number}/{clean}.pdf"
    )
    return {"primary_url": state_url, "fallback_url": gcs_url}


@app.get("/wells/{api_number}/production")
@limiter.limit(settings.rate_limit)
def get_well_production(request: Request, api_number: str):
    if db.prod_df is not None:
        if api_number in db.prod_df.index:
            well_data = db.prod_df.loc[[api_number]]
        else:
            well_data = pd.DataFrame()
    elif db.bq_available():
        return _fetch_production_from_bq(api_number)
    else:
        raise HTTPException(status_code=503, detail="Data not loaded")

    if well_data.empty:
        return []

    result = (
        well_data[["Rpt_Date", "BBLS_OIL_COND", "MCF_GAS", "BBLS_WTR", "DAYS_PROD"]]
        .fillna(0)
        .replace([np.inf, -np.inf], 0)
    )
    result["Rpt_Date"] = pd.to_datetime(result["Rpt_Date"])
    result = result.sort_values("Rpt_Date")

    return result.to_dict(orient="records")


@app.post("/train")
@limiter.limit("5/minute")
async def train_model(request: Request, background_tasks: BackgroundTasks):
    """
    Triggers model training in the background. Enforces single-concurrency.
    """
    if db.is_training:
        raise HTTPException(status_code=409, detail="Training already in progress")

    if db.merged_df is None or db.merged_df.empty:
        raise HTTPException(status_code=400, detail="No sufficient data for training")

    def run_training():
        logger.info("Starting background training...")
        try:
            model = train_and_evaluate(db.merged_df)
            save_model(model, settings.model_path)
            db.ml_model = model
            logger.info("Training complete and model loaded.")
        except Exception as e:
            logger.error("Training failed: %s", e)
        finally:
            db.is_training = False

    db.is_training = True
    background_tasks.add_task(run_training)
    return {"status": "Training started in background"}


@app.post("/wells/{api_number}/decline")
@limiter.limit("30/minute")
def fit_decline_curve(
    request: Request,
    api_number: str,
    method: str = Query("auto", enum=["auto", "arps", "duong"]),
):
    prod_hist = (
        _fetch_production_from_bq(api_number)
        if db.bq_available()
        else get_well_production(request, api_number)
    )
    if not prod_hist:
        raise HTTPException(status_code=404, detail="No production history found")

    df = pd.DataFrame(prod_hist)
    df = df[df["BBLS_OIL_COND"] > 0].reset_index(drop=True)

    if len(df) < 6:
        raise HTTPException(
            status_code=400, detail="Insufficient data for decline curve analysis"
        )

    df["Month_Index"] = (df["Rpt_Date"] - df["Rpt_Date"].min()).dt.days // 30 + 1
    t_months = df["Month_Index"].values
    q_oil = df["BBLS_OIL_COND"].values

    best_fit = fit_best_decline(t_months, q_oil, method=method)

    # ML Constrained Logic (Fine-Tuning)
    predicted_boe_eur = None
    if db.ml_model and db.merged_df is not None and api_number in db.merged_df.index:
        if len(df) <= 12:
            try:
                X_well = db.merged_df.loc[[api_number]].drop("BOE", axis=1)
                predicted_boe_eur = db.ml_model.predict(X_well)[0]
            except Exception as e:
                logger.warning("ML Prediction failed: %s", e)

    # Generate forecast
    FORECAST_MONTHS = 24
    last_t = t_months[-1]
    forecast_t = np.arange(last_t + 1, last_t + FORECAST_MONTHS + 1)

    if best_fit["method"] == "arps":
        forecast_q = arps_decline(forecast_t, **best_fit["params"])
    elif best_fit["method"] == "duong":
        forecast_q = duong_decline(forecast_t, **best_fit["params"])
    else:
        forecast_q = []

    def to_native(obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [to_native(i) for i in obj]
        return obj

    metrics = {
        "historical_data_points": int(len(df)),
        "fit": to_native(best_fit),
        "forecast": {"months": forecast_t.tolist(), "production": forecast_q.tolist()},
    }

    if predicted_boe_eur:
        metrics["ml_predicted_eur_24mo"] = float(predicted_boe_eur)

    return metrics


@app.post("/wells/{api_number}/economics")
@limiter.limit("30/minute")
def run_economics(
    request: Request,
    api_number: str,
    oil_price: float = 70.0,
    gas_price: float = 3.5,
    discount_rate: float = 0.10,
    capex: float = 6000000.0,
    opex: float = 10.0,
    abandonment_rate_daily: float = 5.0,
):
    fit_res = fit_decline_curve(request, api_number, method="auto")
    if not fit_res["forecast"]["production"]:
        raise HTTPException(status_code=400, detail="Could not forecast production")

    forecast_oil_prod = fit_res["forecast"]["production"]
    prod_hist = (
        _fetch_production_from_bq(api_number)
        if db.bq_available()
        else get_well_production(request, api_number)
    )

    historical_oil_prod = [
        r["BBLS_OIL_COND"] for r in prod_hist if r["BBLS_OIL_COND"] is not None
    ]
    historical_gas_prod = [r["MCF_GAS"] for r in prod_hist if r["MCF_GAS"] is not None]

    if historical_oil_prod and historical_gas_prod:
        total_hist_oil = sum(historical_oil_prod)
        total_hist_gas = sum(historical_gas_prod)
        gor = total_hist_gas / total_hist_oil if total_hist_oil > 0 else 0
    else:
        gor = 0

    forecast_gas_prod = [oil_vol * gor for oil_vol in forecast_oil_prod]

    abandonment_rate_monthly = abandonment_rate_daily * 30.4

    econ_metrics = calculate_npv(
        production_forecast_oil=forecast_oil_prod,
        production_forecast_gas=forecast_gas_prod,
        historical_production_oil=historical_oil_prod,
        historical_production_gas=historical_gas_prod,
        oil_price=oil_price,
        gas_price=gas_price,
        discount_rate=discount_rate,
        capex=capex,
        opex_per_bbl=opex,
        abandonment_rate=abandonment_rate_monthly,
    )

    if "ml_predicted_eur_24mo" in fit_res:
        econ_metrics["ml_predicted_eur_24mo"] = fit_res["ml_predicted_eur_24mo"]

    return econ_metrics
