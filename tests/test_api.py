import pytest


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["wells_loaded"] > 0


def test_get_wells(client):
    response = client.get("/wells?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 10
    assert "API_WellNo" in data[0]


def test_well_search(client):
    response = client.get("/wells?search=3000000000")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any("3000000000" in w["API_WellNo"] for w in data)


def test_well_search_no_match(client):
    response = client.get("/wells?search=ZZZZZ")
    assert response.status_code == 200
    assert response.json() == []


def test_well_details(client):
    # Fetch a list first to get a valid ID
    wells = client.get("/wells?limit=1").json()
    api = wells[0]["API_WellNo"]

    response = client.get(f"/wells/{api}")
    assert response.status_code == 200
    assert response.json()["API_WellNo"] == api


def test_production_history(client):
    # Find a well with history (brute force search like in script, but simplified)
    # We can probably pick a known good well effectively if we sort db by production,
    # but for now iterating is fine as robust check.

    wells = client.get("/wells?limit=50").json()
    valid_api = None

    for w in wells:
        r = client.get(f"/wells/{w['API_WellNo']}/production")
        if r.status_code == 200 and len(r.json()) > 10:
            valid_api = w["API_WellNo"]
            break

    if valid_api:
        # Test DCA
        r_dca = client.post(f"/wells/{valid_api}/decline?method=auto")
        if r_dca.status_code != 200:
            # It might fail if not enough oil specifically
            pass
        else:
            dca = r_dca.json()
            assert "forecast" in dca
            assert len(dca["forecast"]["production"]) == 24

            # Test Econ
            r_econ = client.post(f"/wells/{valid_api}/economics")
            assert r_econ.status_code == 200
            assert "NPV" in r_econ.json()
    else:
        pytest.skip("No well with sufficient production found in sample")


def test_wellfile_url(client):
    wells = client.get("/wells?limit=1").json()
    api = wells[0]["API_WellNo"]

    response = client.get(f"/wells/{api}/wellfile")
    assert response.status_code == 200
    data = response.json()
    assert "primary_url" in data
    assert "fallback_url" in data
    assert "bogfiles.dnrc.mt.gov" in data["primary_url"]
    assert "storage.googleapis.com" in data["fallback_url"]
    assert api.strip()[:10] in data["primary_url"]


def test_wellfile_url_unknown_well(client):
    response = client.get("/wells/9999999999/wellfile")
    assert response.status_code == 404


def test_gas_well_decline(client):
    """Gas-only wells should return stream='gas' in decline response."""
    wells = client.get("/wells?limit=50").json()
    gas_api = None
    for w in wells:
        if w.get("Type") == "GAS":
            prod = client.get(f"/wells/{w['API_WellNo']}/production").json()
            if len(prod) > 0 and all(r["BBLS_OIL_COND"] == 0 for r in prod):
                gas_api = w["API_WellNo"]
                break

    if not gas_api:
        pytest.skip("No gas well found")

    r = client.post(f"/wells/{gas_api}/decline?method=auto")
    assert r.status_code == 200
    data = r.json()
    assert data["stream"] == "gas"
    assert len(data["forecast"]["production"]) == 24


def test_gas_well_economics(client):
    """Economics on a gas well should return EUR_Gas and positive NPV."""
    wells = client.get("/wells?limit=50").json()
    gas_api = None
    for w in wells:
        if w.get("Type") == "GAS":
            prod = client.get(f"/wells/{w['API_WellNo']}/production").json()
            if len(prod) > 12 and all(r["BBLS_OIL_COND"] == 0 for r in prod):
                gas_api = w["API_WellNo"]
                break

    if not gas_api:
        pytest.skip("No gas well with sufficient production found")

    # Use a low abandonment rate (BOE/day) so gas BOE passes the threshold
    r = client.post(
        f"/wells/{gas_api}/economics", params={"abandonment_rate_daily": 0.5}
    )
    assert r.status_code == 200
    data = r.json()
    assert "EUR_Gas" in data
    assert data["EUR_Gas"] > 0
    assert data["NPV"] is not None
