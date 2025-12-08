from typing import List, Dict


def calculate_npv(
    production_forecast: List[float],
    historical_production: List[float] = [],
    oil_price: float = 70.0,
    gas_price: float = 3.5,
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
    Calculates the Net Present Value (NPV) of a well used Full Cycle Economics.
    Includes both Historical (Sunk) and Future (Forecast) production.

    Args:
        production_forecast: List of monthly oil production volumes (bbl).
        historical_production: List of monthly oil production volumes (bbl) - Historical.
        oil_price: WTI Price ($/bbl).
        gas_price: Henry Hub Price ($/mcf) - unused in this simple oil version.
        discount_rate: Annual discount rate (e.g. 0.10 for 10%).
        capex: Initial Capital Expenditure ($).
        opex_per_bbl: Variable operating cost per barrel.
        oil_diff: Price differential to WTI ($/bbl).
        gas_diff: Price differential to HH ($/mcf).
        nri: Net Revenue Interest (owner's share).
        ad_valorem_tax: Tax rate.
        severance_tax: Tax rate.
        abandonment_rate: Economic Limit (bbl/month).
    """

    monthly_discount_rate = (1 + discount_rate) ** (1 / 12) - 1

    # Combine streams
    # If historical is provided, we assume T=0 was at the start of history.
    # CAPEX is spent at T=0.
    full_stream = historical_production + production_forecast

    cash_flows = []
    cumulative_cash_flow = -capex
    payout_month = None

    # Time 0: CAPEX
    cash_flows.append(-capex)

    realized_oil_price = oil_price + oil_diff

    # Track total truncated reserves
    total_eur = 0

    for month, vol in enumerate(full_stream, 1):
        # Abandonment Check (Economic Limit)
        if vol < abandonment_rate:
            break

        total_eur += vol

        # Revenue
        gross_revenue = vol * realized_oil_price
        net_revenue = gross_revenue * nri

        # Taxes
        taxes = gross_revenue * (ad_valorem_tax + severance_tax)

        # OPEX
        opex = vol * opex_per_bbl  # + fixed montly opex? Keeping simple.

        # Net Cash Flow
        ncf = net_revenue - taxes - opex

        cash_flows.append(ncf)
        cumulative_cash_flow += ncf

        if payout_month is None and cumulative_cash_flow >= 0:
            payout_month = month

    # Calculate NPV
    # NPV = Sum( CF_t / (1+r)^t )
    npv = -capex
    for t, cf in enumerate(cash_flows[1:], 1):
        npv += cf / ((1 + monthly_discount_rate) ** t)

    roi = (sum(cash_flows) + capex) / capex

    return {
        "NPV": npv,
        "ROI": roi,
        "Payout_Months": payout_month if payout_month else -1,
        "EUR": total_eur,  # Estimated Ultimate Recovery (Truncated)
    }
