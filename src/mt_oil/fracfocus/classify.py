"""CAS number and ingredient name lookup tables for classifying FracFocus ingredients."""

from mt_oil.fracfocus.units import (
    co2_lb_to_scf,
    n2_lb_to_scf,
)

# ── Acid CAS numbers ──────────────────────────────────────────────────────────
ACID_CAS_SET = {
    "7647-01-0",  # Hydrochloric acid (HCl)
    "7664-39-3",  # Hydrofluoric acid (HF)
    "64-19-7",  # Acetic acid
    "64-18-6",  # Formic acid
    "77-92-9",  # Citric acid
    "7697-37-2",  # Nitric acid
    "7664-38-2",  # Phosphoric acid
    "75-05-8",  # Acetonitrile (acid precursor)
}

ACID_FORMULATION_KEYWORDS = {
    "15%": "15% HCl",
    "28%": "28% HCl",
    "20%": "20% HCl",
    "10%": "10% HCl",
    "acetic": "Acetic acid",
    "formic": "Formic acid",
    "hydrofluoric": "Hydrofluoric acid",
    "muriatic": "Muriatic acid (HCl)",
    "hydrochloric": "Hydrochloric acid",
}

# ── Proppant CAS numbers ──────────────────────────────────────────────────────
SILICA_CAS_SET = {
    "14808-60-7",  # Crystalline silica / quartz
    "15468-32-3",  # Cristobalite
    "14464-46-1",  # Tridymite
    "1317-95-9",  # Silica (generic)
    "60676-86-0",  # Silica glass / fused silica
}

RESIN_CAS_SET = {
    "9003-35-4",  # Phenol-formaldehyde resin
    "25085-75-0",  # Epoxy resin
    "9003-36-5",  # Furan resin
    "64754-95-0",  # Phenolic resin (modified)
}

CERAMIC_CAS_SET = {
    "1344-28-1",  # Aluminum oxide (corundum)
    "1302-76-7",  # Mullite / aluminum silicate
    "1318-16-7",  # Bauxite
    "1335-30-4",  # Sintered bauxite
    "1344-00-9",  # Ceramic proppant (generic)
}

DIVERTER_CAS_SET = {
    "26100-51-6",  # Polylactic acid (PLA)
    "9051-89-2",  # Polylactide/glycolide copolymer
    "7647-14-5",  # Sodium chloride (rock salt)
    "65-85-0",  # Benzoic acid
    "100-51-6",  # Benzyl alcohol (benzoate precursor)
    "9003-17-2",  # Polybutadiene (micro-proppant additive)
}

# ── Additive CAS numbers ──────────────────────────────────────────────────────
FRICTION_REDUCER_CAS = {
    "9003-05-8",  # Polyacrylamide
    "25085-02-3",  # Polyacrylamide copolymer
    "68439-46-3",  # Petroleum distillate / hydrotreated light
    "64742-47-8",  # Hydrotreated light petroleum distillate
    "8052-41-3",  # Stoddard solvent
    "68334-30-5",  # Diesel / fuel oil (carrier for FR)
}

SCALE_INHIBITOR_CAS = {
    "2809-21-4",  # Etidronic acid (HEDP)
    "2664-58-6",  # ATMP (aminotris(methylenephosphonic acid))
    "6419-19-8",  # DTPMP (diethylenetriaminepenta(methylenephosphonic acid))
    "15827-60-8",  # PPCA (phosphinopolycarboxylic acid)
    "52227-60-8",  # Phosphonate (generic polymer)
    "9003-01-4",  # Polyacrylic acid (PAA)
}

BIOCIDE_CAS = {
    "111-30-8",  # Glutaraldehyde
    "52-51-7",  # 2-bromo-2-nitropropane-1,3-diol (Bronopol)
    "10043-35-3",  # Boric acid
    "4719-04-4",  # THPS (tetrakis(hydroxymethyl)phosphonium sulfate)
    "106-89-8",  # Epichlorohydrin
    "87-90-1",  # Trichloroisocyanuric acid
    "130-95-0",  # Quinine (generic)
}

CROSSLINKER_CAS = {
    "1303-96-4",  # Borax / sodium tetraborate
    "1330-43-4",  # Sodium tetraborate (anhydrous)
    "10043-35-3",  # Boric acid
    "10034-93-2",  # Sodium borate (hydrate)
    "1344-28-1",  # Aluminum crosslinker (alumina)
    "10043-01-3",  # Aluminum sulfate
    "7439-89-6",  # Iron (Fe crosslinking)
}

SURFACTANT_CAS = {
    "68955-19-1",  # Alcohol ethoxylate
    "68439-49-6",  # Alcohol ethoxylate (C12-C16)
    "9016-45-9",  # Nonylphenol ethoxylate
    "67762-25-8",  # Alkyl dimethyl benzyl ammonium chloride
    "61789-40-0",  # Imidazoline derivative
    "107-41-5",  # Hexylene glycol
}

# ── Gas CAS numbers ───────────────────────────────────────────────────────────
GAS_CAS_MAP = {
    "7727-37-9": "N2",
    "124-38-9": "CO2",
}

# ── Base fluid keywords ───────────────────────────────────────────────────────
BASE_FLUID_KEYWORDS = {
    "freshwater": "freshwater",
    "fresh water": "freshwater",
    "produced water": "produced water",
    "brine": "brine",
    "salt water": "brine",
    "saltwater": "brine",
    "formation water": "produced water",
    "recycled water": "freshwater",
    "reuse water": "freshwater",
    "potable water": "freshwater",
    "river water": "freshwater",
}

# ── Diverter keywords (from ingredient name / comment) ────────────────────────
DIVERTER_KEYWORDS = [
    "ball sealer",
    "benzoic acid",
    "benzoic flake",
    "rock salt",
    "pla",
    "polylactic",
    "vda",
    "viscoelastic diverting",
    "polymer plug",
    "biodegradable diverter",
    "particulate diverter",
]


def classify_acids(
    purpose: str | None, ingredient: str | None, cas: str | None
) -> bool:
    if cas and cas in ACID_CAS_SET:
        return True
    if purpose and "acid" in purpose.lower():
        return True
    return bool(
        ingredient
        and any(kw in ingredient.lower() for kw in ["acid", "hcl", "hf", "h2so4"])
    )


def detect_acid_formulation(
    ingredient: str | None, comment: str | None, trade_name: str | None
) -> str | None:
    for text in [ingredient, comment, trade_name]:
        if not text:
            continue
        t = text.lower()
        for keyword, formulation in ACID_FORMULATION_KEYWORDS.items():
            if keyword in t:
                return formulation
    return None


def classify_proppant_category(
    purpose: str | None, ingredient: str | None, cas: str | None
) -> str | None:
    if purpose and purpose.lower() != "proppant":
        return None
    if cas:
        if cas in SILICA_CAS_SET:
            return "silica"
        if cas in CERAMIC_CAS_SET:
            return "ceramic"
        if cas in DIVERTER_CAS_SET:
            return "diverter"
    if ingredient:
        ing = ingredient.lower()
        if any(kw in ing for kw in ["resin coated", "resin-coated", "rcp"]):
            return "resin_coated"
        if "sand" in ing and "resin" not in ing:
            return "silica"
        if any(kw in ing for kw in ["ceramic", "bauxite", "sintered"]):
            return "ceramic"
        if any(kw in ing for kw in ["pla", "benzoic", "rock salt", "salt", "diverter"]):
            return "diverter"
    return "other"


def is_resin_coated(ingredient: str | None, cas: str | None) -> bool:
    if ingredient:
        ing = ingredient.lower()
        if any(
            kw in ing
            for kw in ["resin coated", "resin-coated", "rcp", "pre-cured", "precured"]
        ):
            return True
    return cas in RESIN_CAS_SET


def classify_additive(
    purpose: str | None, ingredient: str | None, cas: str | None
) -> str | None:
    if cas:
        if cas in FRICTION_REDUCER_CAS:
            return "friction_reducer"
        if cas in SCALE_INHIBITOR_CAS:
            return "scale_inhibitor"
        if cas in BIOCIDE_CAS:
            return "biocide"
        if cas in CROSSLINKER_CAS:
            return "crosslinker"
        if cas in SURFACTANT_CAS:
            return "surfactant"
    if purpose:
        purpose_lower = purpose.lower()
        if "friction" in purpose_lower:
            return "friction_reducer"
        if "scale" in purpose_lower:
            return "scale_inhibitor"
        if "biocide" in purpose_lower or "antimicrobial" in purpose_lower:
            return "biocide"
        if "crosslink" in purpose_lower:
            return "crosslinker"
        if "surfactant" in purpose_lower or "surface tension" in purpose_lower:
            return "surfactant"
        if "corrosion" in purpose_lower:
            return "corrosion_inhibitor"
        if "iron" in purpose_lower or "nefe" in purpose_lower:
            return "nefe"
        if "clay" in purpose_lower:
            return "clay_stabilizer"
    if ingredient:
        ing = ingredient.lower()
        if any(kw in ing for kw in ["friction reduc", "fr-", "fr "]):
            return "friction_reducer"
        if any(kw in ing for kw in ["scale inhib", "scalecontrol", "scale control"]):
            return "scale_inhibitor"
        if any(kw in ing for kw in ["biocide", "glutaraldehyde", "thps", "bronopol"]):
            return "biocide"
        if any(kw in ing for kw in ["borate", "crosslink", "borax", "zirconium"]):
            return "crosslinker"
        if any(kw in ing for kw in ["surfactant", "non-emuls", "nonemuls", "wetting"]):
            return "surfactant"
    return "other"


def classify_base_fluid(total_water_vol_gal: float, ingredient_names: list[str]) -> str:
    for name in ingredient_names:
        if not name:
            continue
        n = name.lower()
        for keyword, classification in BASE_FLUID_KEYWORDS.items():
            if keyword in n:
                return classification
    if total_water_vol_gal and total_water_vol_gal > 0:
        return "freshwater"
    return "unknown"


def classify_gas(ingredient: str | None, cas: str | None) -> str | None:
    if cas and cas in GAS_CAS_MAP:
        return GAS_CAS_MAP[cas]
    if ingredient:
        ing = ingredient.lower()
        if "nitrogen" in ing or ing == "n2":
            return "N2"
        if "carbon dioxide" in ing or "co2" in ing:
            return "CO2"
    return None


def normalize_gas_volume(
    gas_type: str,
    mass_lbs: float | None = None,
    volume_scf: float | None = None,
    liquid_bbl: float | None = None,
) -> tuple[float, float, float]:
    """Normalize gas to (volume_scf, mass_lbs, liquid_bbl). Any input can seed."""
    result_scf = volume_scf or 0.0
    result_lbs = mass_lbs or 0.0
    result_bbl = liquid_bbl or 0.0

    if result_lbs > 0 and result_scf == 0:
        if gas_type == "N2":
            result_scf = n2_lb_to_scf(result_lbs)
        elif gas_type == "CO2":
            result_scf = co2_lb_to_scf(result_lbs)

    return result_scf, result_lbs, result_bbl


def compute_ppa(proppant_lbs: float, clean_water_gal: float) -> float:
    if clean_water_gal <= 0:
        return 0.0
    return proppant_lbs / clean_water_gal


def compute_stiff_davis_pH() -> float:
    pass  # implemented in domain/scaling.py


def is_diverter_ingredient(purpose: str | None, ingredient: str | None) -> bool:
    if ingredient:
        for kw in DIVERTER_KEYWORDS:
            if kw in ingredient.lower():
                return True
    return bool(purpose and "divert" in purpose.lower())
