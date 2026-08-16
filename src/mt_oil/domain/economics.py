from typing import List, Dict


def calculate_npv(
    production_forecast_oil: List[float],
    production_forecast_gas: List[float],
    historical_production_oil: List[float] = [],
    historical_production_gas: List[float] = [],
    oil_price: float = 70.0,
    gas_price: float = 2.5,
    discount_rate: float = 0.10,
    capex: float = 6_000_000,
    opex_per_bbl: float = 10.0,
    oil_diff: float = -5.0,
    gas_diff: float = -0.5,
    nri: float = 0.80,  # Net Revenue Interest
    ad_valorem_tax: float = 0.05,
    severance_tax: float = 0.05,
    abandonment_rate: float = 0.0,  # bbls per month (converted from day in caller or passed as month)
) -> Dict:
    """
    Calculates the Net Present Value (NPV) of a well using Full Cycle Economics.
    Includes both Historical (Sunk) and Future (Forecast) production for oil and gas.

    Args:
        production_forecast_oil: List of monthly oil production volumes (bbl).
        production_forecast_gas: List of monthly gas production volumes (mcf).
        historical_production_oil: List of monthly oil production volumes (bbl) - Historical.
        historical_production_gas: List of monthly gas production volumes (mcf) - Historical.
        oil_price: WTI Price ($/bbl).
        gas_price: Henry Hub Price ($/mcf).
        discount_rate: Annual discount rate (e.g. 0.10 for 10%).
        capex: Initial Capital Expenditure ($).
        opex_per_bbl: Variable operating cost per barrel of oil equivalent.
        oil_diff: Price differential to WTI ($/bbl).
        gas_diff: Price differential to HH ($/mcf).
        nri: Net Revenue Interest (owner's share).
        ad_valorem_tax: Tax rate.
        severance_tax: Tax rate.
        abandonment_rate: Economic Limit (bbl oil/month).
    """

    monthly_discount_rate = (1 + discount_rate) ** (1 / 12) - 1

    # Combine streams
    full_oil_stream = historical_production_oil + production_forecast_oil
    full_gas_stream = historical_production_gas + production_forecast_gas

    cash_flows = []
    cumulative_cash_flow = -capex
    payout_month = None

    # Time 0: CAPEX
    cash_flows.append(-capex)

    realized_oil_price = oil_price + oil_diff
    realized_gas_price = gas_price + gas_diff

    # Track total reserves
    total_oil_eur = 0
    total_gas_eur = 0

    for month, (oil_vol, gas_vol) in enumerate(
        zip(full_oil_stream, full_gas_stream), 1
    ):
        # Abandonment Check (Economic Limit based on BOE)
        boe = oil_vol + (gas_vol / 5.8)
        if boe < abandonment_rate:
            break

        total_oil_eur += oil_vol
        total_gas_eur += gas_vol

        # Revenue from oil and gas
        oil_revenue = oil_vol * realized_oil_price
        gas_revenue = gas_vol * realized_gas_price
        gross_revenue = oil_revenue + gas_revenue
        net_revenue = gross_revenue * nri

        # Taxes
        taxes = gross_revenue * (ad_valorem_tax + severance_tax)

        # OPEX (based on BOE)
        boe = oil_vol + (gas_vol / 5.8)  # Convert gas to BOE
        opex = boe * opex_per_bbl

        # Net Cash Flow
        ncf = net_revenue - taxes - opex

        cash_flows.append(ncf)
        cumulative_cash_flow += ncf

        if payout_month is None and cumulative_cash_flow >= 0:
            payout_month = month

    # Calculate NPV
    npv = -capex
    for t, cf in enumerate(cash_flows[1:], 1):
        npv += cf / ((1 + monthly_discount_rate) ** t)

    roi = (sum(cash_flows) + capex) / capex

    return {
        "NPV": npv,
        "ROI": roi,
        "Payout_Months": payout_month if payout_month else -1,
        "EUR_Oil": total_oil_eur,
        "EUR_Gas": total_gas_eur,
        "EUR": total_oil_eur + (total_gas_eur / 5.8),  # BOE
    }
