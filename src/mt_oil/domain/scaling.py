"""Produced water chemistry — scaling indices and formation resistivity."""

import math


def normalize_Rw(rw_ohm_m: float, temp_f: float, target_temp_f: float = 77.0) -> float:
    """Normalize formation water resistivity to a reference temperature (Arps).

    Rw2 = Rw1 * (T1 + 6.77) / (T2 + 6.77)
    """
    if target_temp_f == temp_f:
        return rw_ohm_m
    return rw_ohm_m * (temp_f + 6.77) / (target_temp_f + 6.77)


# ── Ionic strength and Stiff-Davis K-value (valid for I > 0.1 M) ──────────────


def ionic_strength_from_tds(tds_mg_l: float) -> float:
    """Estimate ionic strength I (mol/L) from TDS (mg/L).

    Approximate conversion for chloride-dominated brines:
    I ≈ TDS(mg/L) / 58,443 (NaCl equivalent).
    """
    if tds_mg_l <= 0:
        return 0.0
    return tds_mg_l / 58_443.0


def stiff_davis_k_value(ionic_strength: float, temp_c: float) -> float:
    """Stiff-Davis K-value for CaCO3 (valid for ionic strength I > 0.1 M).

    Polynomial regression fit to Stiff & Davis (1952) chart data, valid up to
    ~6 M ionic strength (high-salinity Williston Basin brines). K increases
    with ionic strength and decreases slightly with temperature.
    """
    i = max(ionic_strength, 0.0)
    t = temp_c

    # Fit: K = a0 + a1·log10(I) + a2·log10(I)² + b1·(T) + b2·log10(I)·T
    # Base coefficients fit to Stiff-Davis chart (K ~ 1.8–3.2 range)
    log_i = math.log10(i) if i > 0 else -2.0
    k = 2.84 + 0.38 * log_i + 0.045 * log_i**2 - 0.004 * t - 0.0012 * log_i * t
    return k


def stiff_davis_si(
    ca_mg_l: float,
    hco3_mg_l: float,
    pH: float,
    tds_mg_l: float,
    temp_f: float,
) -> float:
    """Stiff-Davis Stability Index for CaCO3 (valid for I > 0.1 M).

    SI = pH − (K + pCa + pAlk). Positive SI indicates scale-prone conditions.

    Uses temperature-dependent K-values valid for high-salinity brines
    (ionic strength up to ~6 M). Logs a boundary warning above 350,000 mg/L TDS.
    """
    tds_mg_l = tds_mg_l or 0.0
    if tds_mg_l > 350_000:
        import warnings

        warnings.warn(
            f"Stiff-Davis K-value extrapolated beyond 350,000 mg/L TDS ({tds_mg_l:.0f} mg/L)",
            RuntimeWarning,
            stacklevel=2,
        )

    ionic_strength = ionic_strength_from_tds(tds_mg_l)
    temp_c = (temp_f - 32.0) * 5.0 / 9.0

    # pCa and pAlk from concentrations
    ca_mol = ca_mg_l / 40_080.0
    alk_eq = hco3_mg_l / 61_017.0
    pca = -math.log10(ca_mol) if ca_mol > 0 else 0
    palk = -math.log10(alk_eq) if alk_eq > 0 else 0

    k = stiff_davis_k_value(ionic_strength, temp_c)
    phs = k + pca + palk
    si = pH - phs
    return round(si, 3)


# ── Temperature-dependent solubility products (Oddo-Tomson) ──────────────────


def _oddo_tomson_ksp_baso4(temp_c: float, ionic_strength: float) -> float:
    """Oddo-Tomson BaSO4 solubility product (mol²/L²) at temperature.

    Empirical temperature + ionic-strength dependence. Reference Ksp ~1.1e-10
    at 25°C; decreases with temperature (more scale-prone downhole).
    """
    # Base log Ksp at 25°C ≈ -9.96 (Oddo-Tomson)
    log_ksp = (
        -9.96
        - 0.0018 * (temp_c - 25.0)
        + 0.1 * math.log10(max(ionic_strength, 0.1) / 0.1)
    )
    return 10.0**log_ksp


def _oddo_tomson_ksp_srso4(temp_c: float, ionic_strength: float) -> float:
    """Oddo-Tomson SrSO4 solubility product (mol²/L²) at temperature."""
    # Reference log Ksp ~ -6.5 at 25°C (SrSO4 more soluble than BaSO4)
    log_ksp = (
        -6.5
        - 0.0012 * (temp_c - 25.0)
        + 0.06 * math.log10(max(ionic_strength, 0.1) / 0.1)
    )
    return 10.0**log_ksp


def barium_sulfate_si(
    ba_mg_l: float,
    so4_mg_l: float,
    tds_mg_l: float = 0.0,
    temp_f: float = 150.0,
) -> float | None:
    """Oddo-Tomson BaSO4 saturation index (log10 supersaturation ratio).

    SI > 0 indicates scale-prone barium sulfate. Uses temperature- and
    ionic-strength-dependent Ksp (valid for high-salinity brines).
    """
    if ba_mg_l <= 0 or so4_mg_l <= 0:
        return None

    ba_mol = ba_mg_l / 137_330.0
    so4_mol = so4_mg_l / 96_062.0
    ion_product = ba_mol * so4_mol
    if ion_product <= 0:
        return None

    ionic_strength = ionic_strength_from_tds(tds_mg_l)
    temp_c = (temp_f - 32.0) * 5.0 / 9.0
    ksp = _oddo_tomson_ksp_baso4(temp_c, ionic_strength)

    si = math.log10(ion_product / ksp)
    return round(si, 3)


def strontium_sulfate_si(
    sr_mg_l: float,
    so4_mg_l: float,
    tds_mg_l: float = 0.0,
    temp_f: float = 150.0,
) -> float | None:
    """Oddo-Tomson SrSO4 saturation index (log10 supersaturation ratio).

    SI > 0 indicates scale-prone strontium sulfate.
    """
    if sr_mg_l <= 0 or so4_mg_l <= 0:
        return None

    sr_mol = sr_mg_l / 87_620.0
    so4_mol = so4_mg_l / 96_062.0
    ion_product = sr_mol * so4_mol
    if ion_product <= 0:
        return None

    ionic_strength = ionic_strength_from_tds(tds_mg_l)
    temp_c = (temp_f - 32.0) * 5.0 / 9.0
    ksp = _oddo_tomson_ksp_srso4(temp_c, ionic_strength)

    si = math.log10(ion_product / ksp)
    return round(si, 3)


def skillman_mcdonald(
    ca_mg_l: float, so4_mg_l: float, tds_mg_l: float, temp_f: float
) -> float | None:
    """Skillman-McDonald calcium sulfate (CaSO4) index.

    Returns the isothermal solubility threshold comparison (1.0 = saturated).
    Simplified: uses Ca and SO4 concentrations.
    """
    if ca_mg_l <= 0 or so4_mg_l <= 0:
        return None

    # Empirical CaSO4 solubility (mg/L) as function of TDS and temperature
    solubility = 1200.0 - 0.25 * tds_mg_l + 8.0 * (temp_f - 60) / 10.0
    if solubility <= 0:
        return None

    product = math.sqrt(ca_mg_l * so4_mg_l)
    return round(product / math.sqrt(solubility), 3)


def scaling_summary(water: dict) -> dict:
    """Produce a scaling tendency summary from a water chemistry dict.

    water keys: tds_mg_l, na, ca, mg, ba, sr, so4, cl, hco3, ph, rw_ohm_m, sample_temp_f
    """
    tds = water.get("tds_mg_l", 0.0) or 0.0
    temp = water.get("sample_temp_f", 100.0) or 100.0
    ph = water.get("ph", 7.0) or 7.0
    ca = water.get("ca", 0.0) or 0.0
    so4 = water.get("so4", 0.0) or 0.0
    hco3 = water.get("hco3", 0.0) or 0.0
    ba = water.get("ba", 0.0) or 0.0
    sr = water.get("sr", 0.0) or 0.0

    sd = stiff_davis_si(ca, hco3, ph, tds, temp)
    sm = skillman_mcdonald(ca, so4, tds, temp)
    bso4 = barium_sulfate_si(ba, so4, tds, temp)
    sso4 = strontium_sulfate_si(sr, so4, tds, temp)

    rw = water.get("rw_ohm_m")
    rw77 = normalize_Rw(rw, temp) if rw else None

    method_flag = None
    if tds > 350_000:
        method_flag = "METHOD_BOUNDARY_EXCEEDED"

    scale_risk = (
        "HIGH"
        if (sd and sd > 0.5) or (bso4 and bso4 > 0) or (sso4 and sso4 > 0)
        else "MODERATE" if (sd and sd > 0) or (sm and sm > 1.0) else "LOW"
    )

    return {
        "stiff_davis_caco3_si": sd,
        "skillman_mcdonald_caso4": sm,
        "barium_sulfate_si": bso4,
        "strontium_sulfate_si": sso4,
        "rw_ohm_m@77F": rw77,
        "scale_risk": scale_risk,
        "method_flag": method_flag,
    }
