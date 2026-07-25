import os
import sys

# Skip heavy data loading during test session startup.
os.environ.setdefault("SKIP_DATA_LOAD", "1")

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mt_oil.api.main import app, db  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seed_mock_data():
    """Populate the global datastore with minimal in-memory data for API tests."""
    wells = []
    for i in range(12):
        wells.append(
            {
                "API_WellNo": f"300000000{i:04d}",
                "Lat": 47.5 + i * 0.01,
                "Long": -105.2 - i * 0.01,
                "Type": "OIL" if i % 2 == 0 else "GAS",
                "Slant": "Horizontal" if i % 3 == 0 else "Vertical",
                "DTD": 12000.0 - i * 100,
                "ST_FMTN_CD": "Bakken" if i % 2 == 0 else "Three Forks",
            }
        )
    well_df = pd.DataFrame(wells).set_index("API_WellNo")
    db.well_df = well_df
    db.well_df.index.name = "API_WellNo"

    dates = pd.date_range("2020-01-01", periods=24, freq="MS")
    prod_rows = []
    for api in db.well_df.index:
        for i, d in enumerate(dates):
            prod_rows.append(
                {
                    "API_WellNo": api,
                    "Rpt_Date": d,
                    "ST_FMTN_CD": db.well_df.loc[api, "ST_FMTN_CD"],
                    "BBLS_OIL_COND": 1000 - i * 20,
                    "MCF_GAS": 500 - i * 10,
                    "BBLS_WTR": 50,
                    "DAYS_PROD": 30,
                }
            )
    prod_df = pd.DataFrame(prod_rows)
    db.prod_df = prod_df.set_index("API_WellNo").sort_index()

    sums = db.prod_df.groupby(level=0)[["BBLS_OIL_COND", "MCF_GAS"]].sum()
    producing = sums[(sums["BBLS_OIL_COND"] > 0) | (sums["MCF_GAS"] > 0)]
    db.producing_wells_set = set(producing.index)

    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
