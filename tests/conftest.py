import pytest
from fastapi.testclient import TestClient
import os
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mt_oil.api.main import app, db  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def mock_data():
    """
    Load data only once for the session to speed up tests.
    Uses the real data since optimization makes it fast enough,
    but could be mocked if needed.
    """
    # Trigger the lifespan startup event manually or rely on TestClient context
    # TestClient(app) context manager runs lifespan.
    # We can check if db is populated.
    if db.well_df is None:
        # If client fixture didn't trigger (it should), or if we need direct access
        pass
    return db
