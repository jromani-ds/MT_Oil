from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
import pandas as pd
import numpy as np
import os
from contextlib import asynccontextmanager

from mt_oil.data.loader import pull_well_data, pull_prod_data
from mt_oil.processing.features import preprocess_well_data, preprocess_prod_data, merge_data, preprocess_ff_data
from mt_oil.domain.decline_curve import fit_best_decline, arps_decline, duong_decline
from mt_oil.domain.economics import calculate_npv

# Global Data Cache
class DataStore:
    well_df: Optional[pd.DataFrame] = None
    prod_df: Optional[pd.DataFrame] = None
    totals_df: Optional[pd.DataFrame] = None

db = DataStore()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load data on startup
    print("Loading data...")
    # Using existing loader functions. 
    # Note: These download if not present.
    try:
        raw_well = pull_well_data()
        db.well_df = preprocess_well_data(raw_well)
        # Ensure Index is string for API lookups
        db.well_df.index = db.well_df.index.astype(str)
        
        lease_prod, well_prod = pull_prod_data()
        
        # 1. Preprocess totals FIRST (needs API_WellNo as column)
        # Ensure API is string here too just in case, or let preprocess handle it?
        # preprocess_prod_data expects API_WellNo column.
        # Let's operate on a copy or just do it before mutation.
        well_prod["API_WellNo"] = well_prod["API_WellNo"].astype(str)
        db.totals_df = preprocess_prod_data(well_prod) 
        db.totals_df.index = db.totals_df.index.astype(str)

        # 2. Setup raw prod_df for API access
        db.prod_df = well_prod 
        # Index for speed
        db.prod_df.set_index("API_WellNo", inplace=True)
        # Sort index to ensure performance
        db.prod_df.sort_index(inplace=True)
        
        print(f"Data Loaded: {len(db.well_df)} wells.")
    except Exception as e:
        print(f"Error loading data: {e}")
    
    yield
    # Cleanup if needed
    db.well_df = None

app = FastAPI(title="MT Oil API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "wells_loaded": len(db.well_df) if db.well_df is not None else 0}

@app.get("/wells")
def get_wells(limit: int = 100, skip: int = 0):
    if db.well_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    # Return list of wells with basic info (Lat, Long, API)
    # Reset index to make API_WellNo a column
    filtered = db.well_df.reset_index().iloc[skip : skip + limit]
    return filtered.to_dict(orient="records")

@app.get("/wells/{api_number}")
def get_well_details(api_number: str = Path(..., title="API Well Number")):
    if db.well_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    if api_number not in db.well_df.index:
        raise HTTPException(status_code=404, detail="Well not found")
        
    well = db.well_df.loc[api_number].to_dict()
    well["API_WellNo"] = api_number
    return well

@app.get("/wells/{api_number}/production")
def get_well_production(api_number: str):
    if db.prod_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    # Filter raw prod data
    # Ensure type match (API in prod data might be int or str, loader usually parses consistent)
    # Check type in dataframe first if needed, assuming str for now based on previous code
    
    # In pull_data.py it was read_csv without specific dtype for API, so likely inferred as int or obj.
    # We should handle this more robustly in a real app (casting).
    pass 
    # Logic to fetch and return timeseries
    
    # Using the raw dataframe
    # Types are now enforced as strings on load, and index is set
    if api_number in db.prod_df.index:
        well_data = db.prod_df.loc[[api_number]]
    else:
        well_data = pd.DataFrame()
    
    if well_data.empty:
        return []
        
    # Standardize columns
    result = well_data[["Rpt_Date", "BBLS_OIL_COND", "MCF_GAS", "BBLS_WTR", "DAYS_PROD"]].fillna(0)
    # Sort by date
    result["Rpt_Date"] = pd.to_datetime(result["Rpt_Date"])
    result = result.sort_values("Rpt_Date")
    
    return result.to_dict(orient="records")

@app.post("/wells/{api_number}/decline")
def fit_decline_curve(api_number: str, method: str = Query("auto", enum=["auto", "arps", "duong"])):
    """
    Fits a decline curve to the well's oil production history.
    """
    prod_hist = get_well_production(api_number)
    if not prod_hist:
        raise HTTPException(status_code=404, detail="No production history found")
        
    df = pd.DataFrame(prod_hist)
    # Filter for oil > 0
    df = df[df["BBLS_OIL_COND"] > 0].reset_index(drop=True)
    
    if len(df) < 6: # Need minimum data points
         raise HTTPException(status_code=400, detail="Insufficient data for decline curve analysis")
    
    # Time in months (approx)
    # Calculate months from start
    df["Month_Index"] = (df["Rpt_Date"] - df["Rpt_Date"].min()).dt.days // 30 + 1
    
    t_months = df["Month_Index"].values
    q_oil = df["BBLS_OIL_COND"].values
    
    best_fit = fit_best_decline(t_months, q_oil, method=method)
    
    # Generate forecast (next 24 months)
    last_t = t_months[-1]
    forecast_t = np.arange(last_t + 1, last_t + 25)
    
    if best_fit["method"] == "arps":
        forecast_q = arps_decline(forecast_t, **best_fit["params"])
    elif best_fit["method"] == "duong":
        forecast_q = duong_decline(forecast_t, **best_fit["params"])
    else:
        forecast_q = []
        
    # Helper to convert numpy types to native python types for JSON serialization
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

    return {
        "historical_data_points": int(len(df)),
        "fit": to_native(best_fit), # Sanitize best_fit dict (params, score)
        "forecast": {
            "months": forecast_t.tolist(),
            "production": forecast_q.tolist()
        }
    }

@app.post("/wells/{api_number}/economics")
def run_economics(api_number: str, 
                  oil_price: float = 70.0,
                  discount_rate: float = 0.10,
                  capex: float = 6000000.0,
                  opex: float = 10.0):
    
    # 1. Get Forecast (Auto-fit)
    fit_res = fit_decline_curve(api_number, method="auto")
    if not fit_res["forecast"]["production"]:
        raise HTTPException(status_code=400, detail="Could not forecast production")
        
    forecast_prod = fit_res["forecast"]["production"]
    
    # 2. Run Economics on Forecast
    # Note: Running econ on the *future* forecast only? 
    # Usually you run it on the whole lifecycle (Past + Future) for Lookback, 
    # or just Future for PDP (Proved Developed Producing) valuation.
    # Let's do PDP Valuation (Future Cashflow).
    # So CAPEX might be 0 for a PDP well (sunk cost), but let's allow user input 
    # in case they want to evaluate a "new" well with this type curve.
    
    econ_metrics = calculate_npv(
        production_forecast=forecast_prod,
        oil_price=oil_price,
        discount_rate=discount_rate,
        capex=capex,
        opex_per_bbl=opex
    )
    
    return econ_metrics
