"""Unit conversion constants and helpers for FracFocus data."""

BBL_PER_GAL = 42.0
GAL_PER_BBL = 42.0
SCF_PER_MSCF = 1000.0
LB_PER_TON = 2000.0

# Nitrogen: 1 ton ≈ 27,200 SCF at standard conditions
N2_SCF_PER_TON = 27200.0
N2_TON_PER_SCF = 1.0 / N2_SCF_PER_TON

# Carbon Dioxide: 1 ton ≈ 17.47 bbl liquid at standard cryogenic conditions
CO2_BBL_PER_TON = 17.47
CO2_TON_PER_BBL = 1.0 / CO2_BBL_PER_TON

# CO2 density: ~1.97 kg/m³ at STP (0°C, 1 atm)
# ~0.123 lb/scf at 60°F, 1 atm (typical US standard)
CO2_LB_PER_SCF = 0.123
CO2_SCF_PER_LB = 1.0 / CO2_LB_PER_SCF

# N2 density: ~0.073 lb/scf at 60°F, 1 atm
N2_LB_PER_SCF = 0.073
N2_SCF_PER_LB = 1.0 / N2_LB_PER_SCF

# Sand volumetric displacement (gal/lb) for quartz sand at SG=2.65
SAND_DISPLACEMENT_GAL_PER_LB = 0.0456


def gal_to_bbl(gal: float) -> float:
    return gal / GAL_PER_BBL


def bbl_to_gal(bbl: float) -> float:
    return bbl * GAL_PER_BBL


def scf_to_mscf(scf: float) -> float:
    return scf / SCF_PER_MSCF


def mscf_to_scf(mscf: float) -> float:
    return mscf * SCF_PER_MSCF


def ton_to_lb(tons: float) -> float:
    return tons * LB_PER_TON


def lb_to_ton(lbs: float) -> float:
    return lbs / LB_PER_TON


def n2_ton_to_scf(tons: float) -> float:
    return tons * N2_SCF_PER_TON


def n2_scf_to_ton(scf: float) -> float:
    return scf * N2_TON_PER_SCF


def n2_lb_to_scf(lbs: float) -> float:
    return lbs * N2_SCF_PER_LB


def n2_scf_to_lb(scf: float) -> float:
    return scf * N2_LB_PER_SCF


def co2_ton_to_bbl(tons: float) -> float:
    return tons * CO2_BBL_PER_TON


def co2_bbl_to_ton(bbl: float) -> float:
    return bbl * CO2_TON_PER_BBL


def co2_lb_to_scf(lbs: float) -> float:
    return lbs * CO2_SCF_PER_LB


def co2_scf_to_lb(scf: float) -> float:
    return scf * CO2_LB_PER_SCF


def to_clean_water_equivalent(
    volume_bbl: float,
    proppant_lbs: float | None,
) -> float:
    """Normalize a slurry (or unknown) fluid volume to Clean Water Equivalent (CWE).

    Clean volume = slurry volume − (proppant lbs × sand displacement gal/lb).

    At 2.0–2.5 PPA, sand displacement inflates liquid volume by 9–12%, so this
    prevents false-positive >10% discrepancy flags against clean-water filings.
    If no proppant is present, returns the volume unchanged.
    """
    if volume_bbl is None:
        return 0.0
    if proppant_lbs is None or proppant_lbs <= 0:
        return float(volume_bbl)
    displacement_gal = proppant_lbs * SAND_DISPLACEMENT_GAL_PER_LB
    displacement_bbl = gal_to_bbl(displacement_gal)
    cwe = volume_bbl - displacement_bbl
    return max(cwe, 0.0)
