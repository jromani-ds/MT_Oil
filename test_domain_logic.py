import sys
import os
import numpy as np
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from mt_oil.domain.decline_curve import fit_best_decline, arps_decline, duong_decline
from mt_oil.domain.economics import calculate_npv

def test_dca():
    print("Testing Decline Curve Analysis...")
    # Generate synthetic data (Arps)
    t = np.arange(1, 25) # 24 months
    qi = 500
    di = 0.5
    b = 1.2
    
    # Create noisy data
    q_true = arps_decline(t, qi, di, b)
    q_noisy = q_true + np.random.normal(0, 10, size=len(t))
    
    # Fit
    result = fit_best_decline(t, q_noisy, method="auto")
    print(f"Best fit method: {result['method']}")
    print(f"Score (MSE): {result['score']:.2f}")
    print(f"Params: {result['params']}")
    
    # Validate Duong
    q_duong = duong_decline(t, 500, 1.0, 1.2)
    assert len(q_duong) == len(t)
    print("DCA Tests Passed.")

def test_economics():
    print("Testing Economics...")
    # 24 months of production, 1000 bbl/month declining
    prod = [1000 * (0.95 ** i) for i in range(24)] 
    
    econ_result = calculate_npv(
        production_forecast=prod,
        oil_price=75.0,
        oil_diff=-8.0, # Bakken diff
        capex=500_000,
        discount_rate=0.1
    )
    
    print(f"NPV: ${econ_result['NPV']:,.2f}")
    print(f"ROI: {econ_result['ROI']:.2f}x")
    print(f"Payout: {econ_result['Payout_Months']} months")
    
    assert econ_result['NPV'] is not None
    print("Economics Tests Passed.")

if __name__ == "__main__":
    test_dca()
    print("-" * 20)
    test_economics()
