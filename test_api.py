import sys
import os
from fastapi.testclient import TestClient

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mt_oil.api.main import app, db

# Mock database loading to avoid downloading 500MB during quick test if not needed
# OR just rely on files being present (they should be from previous steps)

def test_api():
    client = TestClient(app)
    
    print("Testing /health...")
    # Health check triggers lifespan
    with TestClient(app) as client:
        response = client.get("/health")
        print(f"Health Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        
        # Test GET /wells
        print("Testing /wells...")
        # Get more wells to increase chance of finding one with history
        response = client.get("/wells?limit=50")
        if response.status_code == 200:
            wells = response.json()
            print(f"Got {len(wells)} wells.")
            if len(wells) > 0:
                first_api = wells[0]["API_WellNo"]
                print(f"Testing detail for API {first_api}...")
                
                # Test Detail
                r_detail = client.get(f"/wells/{first_api}")
                assert r_detail.status_code == 200
                
                # Test Production logic
                print(f"Searching for well with production history...")
                valid_api = None
                for w in wells:
                    # Check if it has prod
                    p = client.get(f"/wells/{w['API_WellNo']}/production").json()
                    if not p:
                        continue
                        
                    # Check for oil > 0 and enough points
                    has_oil_hist = [rec['BBLS_OIL_COND'] for rec in p if rec['BBLS_OIL_COND'] > 0]
                    if len(has_oil_hist) > 12: # increased threshold for better fit
                        valid_api = w['API_WellNo']
                        print(f"Found valid well: {valid_api} with {len(has_oil_hist)} oil months.")
                        break
                
                if valid_api:
                    print(f"Testing Decline Curve for API {valid_api}...")
                    r_dca = client.post(f"/wells/{valid_api}/decline?method=auto")
                    if r_dca.status_code == 200:
                        dca = r_dca.json()
                        print(f"DCA Fit Method: {dca['fit']['method']}")
                        print(f"Forecast Points: {len(dca['forecast']['production'])}")
                        
                        # Test Economics
                        print(f"Testing Economics for API {valid_api}...")
                        r_econ = client.post(f"/wells/{valid_api}/economics", params={"oil_price": 75.0})
                        if r_econ.status_code == 200:
                            econ = r_econ.json()
                            print(f"NPV: {econ['NPV']}")
                        else:
                            print(f"Econ failed: {r_econ.text}")
                    else:
                        print(f"DCA failed: {r_dca.text}")
                else:
                    print("Could not find a well with enough oil history for DCA test in the first 5 wells.")

if __name__ == "__main__":
    test_api()
