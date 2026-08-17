"""Fluid PVT — gas composition, bubble point, viscosity, shrinkage."""

# Molecular weights (lb/lbmol) for gas components
MW = {
    "c1": 16.043,
    "c2": 30.07,
    "c3": 44.097,
    "ic4": 58.124,
    "nc4": 58.124,
    "ic5": 72.151,
    "nc5": 72.151,
    "c6": 86.178,
    "c7plus": 96.0,
    "n2": 28.013,
    "co2": 44.01,
    "h2s": 34.08,
}


def gas_specific_gravity(mole_fractions: dict) -> float | None:
    """Compute gas specific gravity from mole fractions.

    SG = weighted MW / MW_air (28.97 lb/lbmol)
    """
    if not mole_fractions:
        return None
    total_mw = 0.0
    total_frac = 0.0
    for comp, frac in mole_fractions.items():
        if frac is None:
            continue
        comp_key = comp.lower()
        mw = 28.97 if comp_key == "air" else MW.get(comp_key)
        if mw is None:
            continue
        total_mw += mw * frac
        total_frac += frac
    if total_frac <= 0:
        return None
    return round(total_mw / total_frac / 28.97, 4)


# ── Non-hydrocarbon corrections (Wichert-Aziz) for Standing correlations ────


def wichert_aziz_epsilon(h2s_mol: float, co2_mol: float) -> float:
    """Wichert-Aziz correction parameter ε (Rankine) for non-hydrocarbon gases.

    Applies when H2S and/or CO2 are present in significant amounts (>3–5 mol%).
    """
    a = max(0.0, (h2s_mol or 0.0) + (co2_mol or 0.0))
    if a <= 0:
        return 0.0
    b = (h2s_mol or 0.0) / a if a > 0 else 0.0
    epsilon = 120.0 * (a**0.9 - a**1.6) + 15.0 * (b**0.5 - b**4.0)
    return epsilon


def corrected_gas_gravity(mole_fractions: dict) -> float:
    """Compute a non-HC-corrected gas gravity for use in Standing correlations.

    Applies Wichert-Aziz correction only when H2S ≥ 3% or CO₂ ≥ 5% (total
    non-hydrocarbon content gating), else returns the raw gravity.

    Returns a tuple (corrected_gravity, applied: bool).
    """
    raw_sg = gas_specific_gravity(mole_fractions)
    if raw_sg is None:
        return 0.65, False

    h2s = mole_fractions.get("h2s", 0.0) or 0.0
    co2 = mole_fractions.get("co2", 0.0) or 0.0
    non_hc = h2s + co2
    total_frac = sum(v for v in (mole_fractions or {}).values() if v is not None)

    # Gate: apply correction only if significant non-hydrocarbons present
    if total_frac <= 0 or non_hc <= 0:
        return raw_sg, False

    h2s_mol_pct = h2s / total_frac * 100.0
    co2_mol_pct = co2 / total_frac * 100.0

    if h2s_mol_pct < 3.0 and co2_mol_pct < 5.0:
        # Below correction threshold — use raw gravity
        return raw_sg, False

    # Wichert-Aziz pseudo-critical correction
    epsilon = wichert_aziz_epsilon(h2s, co2)

    # Sutton pseudo-critical from raw gravity
    t_pc_raw = 170.491 + 307.344 * raw_sg
    p_pc_raw = 683.399 - 38.881 * raw_sg + 52.078 * raw_sg**2

    s = h2s / non_hc if non_hc > 0 else 0.0
    t_pc_corr = t_pc_raw - epsilon
    p_pc_raw * t_pc_corr / (t_pc_raw + s * (1 - s) * epsilon)

    # Corrected pseudo-reduced properties → corrected gas gravity
    # Recompute gas gravity from pseudo-critical ratio (approximation)
    # γg_corr ≈ (T_pc_corr/169.0)⁻¹ heuristic — use pseudo-critical based estimate
    gamma_o_corr = (t_pc_corr - 170.491) / 307.344
    gamma_o_corr = max(gamma_o_corr, 0.1)
    return float(round(gamma_o_corr, 4)), True


def btu_from_gas_composition(mole_fractions: dict) -> float | None:
    """Estimate higher heating value (HHV) in BTU/SCF from composition.

    Approximate per-component HHV contributions (BTU/SCF).
    """
    hhv = {
        "c1": 1010.0,
        "c2": 1770.0,
        "c3": 2520.0,
        "ic4": 3250.0,
        "nc4": 3260.0,
        "ic5": 4000.0,
        "nc5": 4000.0,
        "c6": 4750.0,
        "c7plus": 5500.0,
        "h2s": 640.0,
    }
    if not mole_fractions:
        return None
    total = 0.0
    for comp, frac in mole_fractions.items():
        if frac is None:
            continue
        hhv_val = hhv.get(comp.lower())
        if hhv_val:
            total += hhv_val * frac
    return round(total, 1)


def bubble_point_standing(
    gor_scf_stb: float,
    gas_gravity: float,
    oil_api: float,
    temp_f: float,
) -> float | None:
    """Standing correlation for bubble point pressure (psia).

    Pb = 18.2 * [ (Rs/γg)^0.83 * 10^(0.00091·T − 0.0125·API) − 1.4 ]

    Use a Wichert-Aziz corrected gas gravity for sour/CO2-rich gas via
    `corrected_gas_gravity()`; pass the corrected value here.
    """
    if gor_scf_stb <= 0 or gas_gravity <= 0 or oil_api is None:
        return None
    term = (gor_scf_stb / gas_gravity) ** 0.83
    term *= 10 ** (0.00091 * temp_f - 0.0125 * oil_api)
    pb = 18.2 * (term - 1.4)
    return round(float(pb), 1)


def oil_viscosity_beggs_robinson(api_gravity: float, temp_f: float) -> float | None:
    """Dead-oil viscosity via Beggs-Robinson (cp)."""
    if api_gravity is None:
        return None
    # Reference temperature (110°F standard)
    a = 10 ** (0.43 + 8.33 / api_gravity)
    mu_ref = a / 110.0  # at 110F
    b = 5.44 / (api_gravity + 150)
    mu = mu_ref * (temp_f / 110.0) ** (-b)
    return round(float(mu), 3)


def oil_fvf_standing(
    gor_scf_stb: float,
    gas_gravity: float,
    oil_api: float,
    temp_f: float,
) -> float | None:
    """Standing formation volume factor Bo (bbl/STB).

    Bo = 0.9759 + 0.00012·[ Rs·(γg/γo)^0.5 + 1.25·T ]^1.2

    Use a Wichert-Aziz corrected gas gravity for sour/CO2-rich gas.
    """
    if gor_scf_stb <= 0 or gas_gravity <= 0 or oil_api is None:
        return None
    # oil specific gravity
    gamma_o = 141.5 / (131.5 + oil_api)
    term = gor_scf_stb * (gas_gravity / gamma_o) ** 0.5 + 1.25 * temp_f
    bo = 0.9759 + 0.00012 * term**1.2
    return round(float(bo), 4)


def below_bubble_point_check(
    producing_gor_scf_stb: float,
    bubble_point_psi: float | None,
    reservoir_pressure_psi: float | None,
) -> dict | None:
    """Flag if the reservoir has dropped below bubble point (two-phase flow)."""
    if bubble_point_psi is None:
        return None
    below = (
        reservoir_pressure_psi is not None and reservoir_pressure_psi < bubble_point_psi
    )
    return {
        "bubble_point_psi": bubble_point_psi,
        "below_bubble_point": below,
        "note": (
            (
                "Reservoir below bubble point — two-phase flow crushing oil relative permeability"
                if below
                else "Above bubble point — single-phase oil"
            )
            if reservoir_pressure_psi is not None
            else "Pressure unknown"
        ),
    }
