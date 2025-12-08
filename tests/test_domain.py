import pytest
import numpy as np
from mt_oil.domain.decline_curve import fit_best_decline, arps_decline
from mt_oil.domain.economics import calculate_npv


@pytest.mark.parametrize("method", ["arps", "duong", "auto"])
def test_decline_curve_fitting(method):
    # Generate synthetic Arps data
    t = np.arange(1, 48)
    qi, di, b = 1000, 0.5, 1.2
    q_true = arps_decline(t, qi, di, b)
    # Add noise
    q_noisy = q_true + np.random.normal(0, 5, size=len(t))

    result = fit_best_decline(t, q_noisy, method=method)

    assert result["method"] is not None
    assert result["score"] < 1000  # Reasonable MSE
    assert len(result["params"]) > 0


def test_economics_npv():
    # Simple case: 1 month production
    prod = [1000]
    # Price $100, Net $80 (after tax/diff), Cost $10/bbl -> Margin $70
    # Cashflow = 1000 * 70 = 70,000
    # Capex 60,000
    # NPV ~ 10,000 (undiscounted)

    res = calculate_npv(
        production_forecast=prod,
        oil_price=100.0,
        oil_diff=0,
        capex=60_000,
        opex_per_bbl=10.0,
        ad_valorem_tax=0,
        severance_tax=0,
        nri=1.0,
        discount_rate=0.0,
    )

    assert res["NPV"] == pytest.approx(30000.0)
    assert res["ROI"] == pytest.approx(90000 / 60000)
    assert res["Payout_Months"] == 1


def test_economics_negative_case():
    prod = [100]
    res = calculate_npv(production_forecast=prod, oil_price=50.0, capex=1_000_000)
    assert res["NPV"] < 0
    assert res["Payout_Months"] == -1
