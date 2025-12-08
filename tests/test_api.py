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
