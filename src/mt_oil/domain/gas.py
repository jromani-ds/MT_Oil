"""Gas properties — real-gas Z-factor (Hall-Yarborough), downhole volumes, density."""

import math

# Gas constants
R = 10.7316  # psia·ft³/(lbmol·°R)

# Universal gas constant density factor
# ρ_gas (ppg) = (p · MW_gas) / (Z · R · T) / 7.4805  — 7.4805 gal/ft³
# Simplified: ρ_gas (ppg) = (p · γg · 28.97) / (Z · 10.7316 · T · 7.4805)
# Approx constant: ρ_gas = p · γg / (Z · T · constant_factor)
_RHO_FACTOR = 28.97 / (R * 7.4805)  # ≈ 0.361


def hall_yarborough_z(
    p_psia: float,
    t_rankine: float,
    gas_gravity: float = 0.65,
    n2_mol_frac: float = 0.0,
    co2_mol_frac: float = 0.0,
    h2s_mol_frac: float = 0.0,
    max_iter: int = 50,
    tolerance: float = 1e-6,
) -> float:
    """Compute Z-factor using Hall-Yarborough correlation with Wichert-Aziz
    pseudo-critical corrections.

    Implements the Hall-Yarborough (1973) equation of state for natural gases.
    Valid for: 1.0 ≤ T_pr ≤ 3.0, 0.2 ≤ P_pr ≤ 30.0
    """
    # ── Pseudo-critical properties (Sutton / Wichert-Aziz) ──
    # Sutton (1985) for gas gravity
    if gas_gravity <= 0:
        gas_gravity = 0.65

    # Johnston (Charts) or Sutton: T_pc_raw, P_pc_raw
    t_pc_raw = 170.491 + 307.344 * gas_gravity
    p_pc_raw = 683.399 - 38.881 * gas_gravity + 52.078 * gas_gravity**2

    # Wichert-Aziz correction for H2S and CO2
    h2s = max(0.0, h2s_mol_frac)
    co2 = max(0.0, co2_mol_frac)
    a = h2s + co2
    if a > 0:
        # Wichert-Aziz parameter epsilon
        b = h2s / a if a > 0 else 0.0
        epsilon = 120.0 * (a**0.9 - a**1.6) + 15.0 * (b**0.5 - b**4.0)
        t_pc = t_pc_raw - epsilon
        p_pc = p_pc_raw * t_pc / (t_pc_raw + b * (1 - b) * epsilon)
    else:
        t_pc = t_pc_raw
        p_pc = p_pc_raw

    # Reduced properties
    t_pr = t_rankine / t_pc
    p_pr = p_psia / p_pc

    if t_pr <= 0 or p_pr <= 0:
        return 1.0

    # Hall-Yarborough equations
    # y = 0.06125 · P_pr · t⁻¹ · exp(-1.2 · (1 - t⁻¹)²)
    t_inv = 1.0 / t_pr
    y_guess = 0.06125 * p_pr * t_inv * math.exp(-1.2 * (1.0 - t_inv) ** 2)

    if y_guess <= 0:
        return 1.0

    y = y_guess
    for _ in range(max_iter):
        # F(y) = 0 from Hall-Yarborough
        # Using the form: F(y) = -0.06125·P·t·exp(-1.2·(1-t)²) + (y + y² + y³ + y⁴) / (1-y)³
        #   - (14.76·t - 9.76·t² + 4.58·t³)·y² + (90.7·t - 242.2·t² + 42.4·t³)·y^(2.18+2.82·t)
        y2 = y * y
        y3 = y2 * y
        y4 = y3 * y

        a1 = 14.76 * t_inv - 9.76 * t_inv**2 + 4.58 * t_inv**3
        a2 = 90.7 * t_inv - 242.2 * t_inv**2 + 42.4 * t_inv**3
        a3 = 2.18 + 2.82 * t_inv

        f = (
            -0.06125 * p_pr * t_inv * math.exp(-1.2 * (1.0 - t_inv) ** 2)
            + (y + y2 + y3 + y4) / (1 - y) ** 3
            - a1 * y2
            + a2 * y**a3
        )

        # Derivative F'(y)
        df = (
            (1.0 + 2.0 * y + 3.0 * y2 + 4.0 * y3) / (1.0 - y) ** 3
            + 3.0 * (y + y2 + y3 + y4) / (1.0 - y) ** 4
            - 2.0 * a1 * y
            + a2 * a3 * y ** (a3 - 1.0)
        )

        if abs(df) < 1e-12:
            break

        y_new = y - f / df
        if y_new < 0:
            y_new = y * 0.5

        if abs(y_new - y) < tolerance:
            y = y_new
            break
        y = y_new

    # Z = 0.06125 · P_pr · t⁻¹ · exp(-1.2 · (1 - t⁻¹)²) / y
    z = 0.06125 * p_pr * t_inv * math.exp(-1.2 * (1.0 - t_inv) ** 2) / y
    return max(z, 0.1)  # floor at 0.1


def downhole_gas_volume(
    surface_scf: float,
    p_bhp_psia: float,
    t_rankine: float,
    gas_gravity: float = 0.65,
    n2_mol_frac: float = 0.0,
    co2_mol_frac: float = 0.0,
    h2s_mol_frac: float = 0.0,
) -> float | None:
    """Convert surface SCF to downhole gas volume in gallons.

    Uses: V_dh = (V_scf · T_R · Z · P_sc) / (P_bhp · T_sc)
    where P_sc = 14.7 psia, T_sc = 520 °R (60°F).
    """
    if surface_scf is None or surface_scf <= 0 or p_bhp_psia is None or p_bhp_psia <= 0:
        return None
    if t_rankine is None or t_rankine <= 0:
        return None

    z = hall_yarborough_z(
        p_psia=p_bhp_psia,
        t_rankine=t_rankine,
        gas_gravity=gas_gravity,
        n2_mol_frac=n2_mol_frac,
        co2_mol_frac=co2_mol_frac,
        h2s_mol_frac=h2s_mol_frac,
    )

    # Standard conditions: 14.7 psia, 520 °R
    volume_ft3 = surface_scf * t_rankine * z * 14.7 / (p_bhp_psia * 520.0)
    # Convert ft³ to gallons
    volume_gal = volume_ft3 * 7.48051948
    return volume_gal


def downhole_gas_density_ppg(
    p_bhp_psia: float,
    z: float,
    t_rankine: float,
    gas_gravity: float = 0.65,
) -> float | None:
    """Compute downhole gas density in ppg (pounds per gallon).

    ρ = (p · MW) / (Z · R · T)  in lb/ft³, then convert to ppg.
    """
    if p_bhp_psia is None or p_bhp_psia <= 0 or z is None or z <= 0:
        return None
    if t_rankine is None or t_rankine <= 0:
        return None
    if gas_gravity is None or gas_gravity <= 0:
        return None

    mw = gas_gravity * 28.97
    # lb/ft³
    rho_lb_per_ft3 = p_bhp_psia * mw / (z * R * t_rankine)
    # Convert to ppg (1 ft³ = 7.4805 gal)
    rho_ppg = rho_lb_per_ft3 / 7.48051948
    return max(rho_ppg, 0.001)


def bhp_estimate(
    surface_pressure_psi: float, tvd_ft: float, fluid_sg: float = 1.0
) -> float:
    """Estimate bottomhole treating pressure from surface pressure and hydrostatic."""
    hydrostatic = 0.433 * fluid_sg * tvd_ft
    return surface_pressure_psi + hydrostatic
