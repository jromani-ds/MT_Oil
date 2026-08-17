"""FracFocus orchestration service: classifies raw FF data and returns aggregates + detail."""

import logging

import pandas as pd

from mt_oil.fracfocus.classify import (
    classify_acids,
    classify_additive,
    classify_base_fluid,
    classify_gas,
    classify_proppant_category,
    detect_acid_formulation,
    is_resin_coated,
    normalize_gas_volume,
)
from mt_oil.fracfocus.schemas import (
    AdditiveProfile,
    FracFocusDetailRow,
    FracFocusWellAggregate,
    GasComponent,
    ProppantBreakdown,
)

logger = logging.getLogger(__name__)

REQUIRED_FF_COLS = {
    "APINumber",
    "Purpose",
    "MassIngredient",
    "IngredientName",
    "CASNumber",
    "Supplier",
    "TradeName",
    "IngredientMass",
    "IngredientPercentHFJob",
    "CalculationType",
    "TotalBaseWaterVolume",
    "TotalBaseNonWaterVolume",
    "TVD",
    "JobStartDate",
    "JobEndDate",
    "OperatorName",
    "WellName",
}


def classify_ff_well(
    raw_ff_df: pd.DataFrame,
    api_wellno: str,
) -> tuple[FracFocusWellAggregate | None, list[FracFocusDetailRow]]:
    """Classify all FracFocus records for a single well.

    Returns (aggregate, detail_rows).
    """
    # Filter to well
    well_df = raw_ff_df[raw_ff_df["APINumber"].astype(str) == api_wellno]
    if well_df.empty:
        return None, []

    return _classify_ff_df(well_df)


def classify_all_ff(
    raw_ff_df: pd.DataFrame,
) -> tuple[dict[str, FracFocusWellAggregate], list[FracFocusDetailRow]]:
    """Classify all FracFocus records. Returns (aggregates_by_api, all_detail_rows)."""
    all_detail: list[FracFocusDetailRow] = []
    aggregates: dict[str, FracFocusWellAggregate] = {}

    for api, group in raw_ff_df.groupby("APINumber"):
        api_str = str(api).strip()
        agg, detail = _classify_ff_df(group)
        if agg:
            aggregates[api_str] = agg
        all_detail.extend(detail)

    return aggregates, all_detail


def _classify_ff_df(
    df: pd.DataFrame,
) -> tuple[FracFocusWellAggregate | None, list[FracFocusDetailRow]]:
    """Classify a DataFrame of ingredient rows for a single well."""
    if df.empty:
        return None, []

    # ── Build detail rows ──
    detail_rows: list[FracFocusDetailRow] = []
    for _, row in df.iterrows():
        detail_rows.append(
            FracFocusDetailRow(
                api_wellno=str(row.get("APINumber", "")).strip(),
                cas_number=(
                    str(row.get("CASNumber"))
                    if pd.notna(row.get("CASNumber"))
                    else None
                ),
                ingredient_name=(
                    str(row.get("IngredientName"))
                    if pd.notna(row.get("IngredientName"))
                    else None
                ),
                supplier=(
                    str(row.get("Supplier")) if pd.notna(row.get("Supplier")) else None
                ),
                purpose=(
                    str(row.get("Purpose")) if pd.notna(row.get("Purpose")) else None
                ),
                trade_name=(
                    str(row.get("TradeName"))
                    if pd.notna(row.get("TradeName"))
                    else None
                ),
                mass_lbs=(
                    float(row["MassIngredient"])
                    if pd.notna(row.get("MassIngredient"))
                    else None
                ),
                percent_hfj=(
                    float(row["IngredientPercentHFJob"])
                    if pd.notna(row.get("IngredientPercentHFJob"))
                    else None
                ),
                calculation_type=(
                    str(row.get("CalculationType"))
                    if pd.notna(row.get("CalculationType"))
                    else None
                ),
                job_start_date=(
                    str(row.get("JobStartDate"))
                    if pd.notna(row.get("JobStartDate"))
                    else None
                ),
                job_end_date=(
                    str(row.get("JobEndDate"))
                    if pd.notna(row.get("JobEndDate"))
                    else None
                ),
                operator=(
                    str(row.get("OperatorName"))
                    if pd.notna(row.get("OperatorName"))
                    else None
                ),
                well_name=(
                    str(row.get("WellName")) if pd.notna(row.get("WellName")) else None
                ),
            )
        )

    # ── Compute aggregates ──
    # Total water volume (from first row per job)
    total_water_gal = None
    total_nonwater_gal = None
    if "TotalBaseWaterVolume" in df.columns:
        valid_wv = df["TotalBaseWaterVolume"].dropna()
        if not valid_wv.empty:
            total_water_gal = float(valid_wv.iloc[0])

    if "TotalBaseNonWaterVolume" in df.columns:
        valid_nwv = df["TotalBaseNonWaterVolume"].dropna()
        if not valid_nwv.empty:
            total_nonwater_gal = float(valid_nwv.iloc[0])

    # Total proppant (sum of proppant-purpose rows)
    proppant_rows = df[df["Purpose"] == "Proppant"] if "Purpose" in df.columns else df
    total_proppant = (
        float(proppant_rows["MassIngredient"].sum())
        if "MassIngredient" in proppant_rows.columns
        else 0.0
    )

    # Proppant breakdown by category
    proppant_categories: dict[str, float] = {
        "silica": 0.0,
        "resin_coated": 0.0,
        "ceramic": 0.0,
        "diverter": 0.0,
        "other": 0.0,
    }
    for _, row in df.iterrows():
        p = row.get("Purpose")
        ing = (
            str(row.get("IngredientName", ""))
            if pd.notna(row.get("IngredientName"))
            else None
        )
        cas = str(row.get("CASNumber", "")) if pd.notna(row.get("CASNumber")) else None
        mass = (
            float(row["MassIngredient"]) if pd.notna(row.get("MassIngredient")) else 0.0
        )
        cat = classify_proppant_category(p, ing, cas)
        if cat:
            cat_key = cat if cat in proppant_categories else "other"
            proppant_categories[cat_key] += mass

    # Detect resin coating
    for _, row in df.iterrows():
        ing = (
            str(row.get("IngredientName", ""))
            if pd.notna(row.get("IngredientName"))
            else None
        )
        cas = str(row.get("CASNumber", "")) if pd.notna(row.get("CASNumber")) else None
        if is_resin_coated(ing, cas) and proppant_categories.get("silica", 0) > 0:
            proppant_categories["resin_coated"] += (
                proppant_categories.pop("silica", 0) * 0.5
            )
            break

    proppant_breakdown = ProppantBreakdown(**proppant_categories)

    # Acid volume
    total_acid_gal = 0.0
    for _, row in df.iterrows():
        p = row.get("Purpose")
        ing = (
            str(row.get("IngredientName", ""))
            if pd.notna(row.get("IngredientName"))
            else None
        )
        cas = str(row.get("CASNumber", "")) if pd.notna(row.get("CASNumber")) else None
        mass = (
            float(row["MassIngredient"]) if pd.notna(row.get("MassIngredient")) else 0.0
        )
        if classify_acids(p, ing, cas):
            total_acid_gal += mass

    # Check if TotalBaseNonWaterVolume captures acid
    # Some disclosures report acid in non-water volume
    for _, row in df.iterrows():
        ing = (
            str(row.get("IngredientName", ""))
            if pd.notna(row.get("IngredientName"))
            else None
        )
        comment = (
            str(row.get("IngredientComment"))
            if "IngredientComment" in df.columns
            and pd.notna(row.get("IngredientComment"))
            else None
        )
        trade = str(row.get("TradeName")) if pd.notna(row.get("TradeName")) else None
        formulation = detect_acid_formulation(ing, comment, trade)
        if formulation:
            break

    # Additives
    additive_pcts: dict[str, float] = {}
    for _, row in df.iterrows():
        p = row.get("Purpose")
        ing = (
            str(row.get("IngredientName", ""))
            if pd.notna(row.get("IngredientName"))
            else None
        )
        cas = str(row.get("CASNumber", "")) if pd.notna(row.get("CASNumber")) else None
        pct = (
            float(row["IngredientPercentHFJob"])
            if pd.notna(row.get("IngredientPercentHFJob"))
            else None
        )
        cat = classify_additive(p, ing, cas)
        if cat and pct is not None:
            attr = f"{cat}_max_pct"
            existing = additive_pcts.get(attr, 0.0)
            if pct > existing:
                additive_pcts[attr] = pct

    additives = AdditiveProfile(
        friction_reducer_max_pct=additive_pcts.get("friction_reducer_max_pct"),
        scale_inhibitor_max_pct=additive_pcts.get("scale_inhibitor_max_pct"),
        biocide_max_pct=additive_pcts.get("biocide_max_pct"),
        crosslinker_max_pct=additive_pcts.get("crosslinker_max_pct"),
        surfactant_max_pct=additive_pcts.get("surfactant_max_pct"),
    )

    # Gas components
    gas_components: list[GasComponent] = []
    gas_mass: dict[str, float] = {}
    for _, row in df.iterrows():
        ing = (
            str(row.get("IngredientName", ""))
            if pd.notna(row.get("IngredientName"))
            else None
        )
        cas = str(row.get("CASNumber", "")) if pd.notna(row.get("CASNumber")) else None
        mass = (
            float(row["MassIngredient"]) if pd.notna(row.get("MassIngredient")) else 0.0
        )
        gas_type = classify_gas(ing, cas)
        if gas_type:
            gas_mass[gas_type] = gas_mass.get(gas_type, 0.0) + mass

    for gas_type, mass_lbs in gas_mass.items():
        scf, lbs, bbl = normalize_gas_volume(gas_type, mass_lbs=mass_lbs)
        gas_components.append(
            GasComponent(type=gas_type, volume_scf=scf, mass_lbs=lbs, liquid_bbl=bbl)
        )

    # Base fluid type
    ingredient_names = [
        str(row.get("IngredientName", ""))
        for _, row in df.iterrows()
        if pd.notna(row.get("IngredientName"))
    ]
    base_fluid_type = classify_base_fluid(total_water_gal or 0.0, ingredient_names)

    # Job metadata (from first row)
    first_row = df.iloc[0]

    aggregate = FracFocusWellAggregate(
        api_wellno=str(first_row.get("APINumber", "")).strip(),
        total_water_volume_gal=total_water_gal,
        total_nonwater_volume_gal=total_nonwater_gal,
        total_proppant_lbs=total_proppant,
        total_acid_gal=total_acid_gal if total_acid_gal > 0 else None,
        proppant_breakdown=proppant_breakdown,
        additives=additives,
        base_fluid_type=base_fluid_type,
        gas_components=gas_components,
        tvd_ft=float(first_row["TVD"]) if pd.notna(first_row.get("TVD")) else None,
        job_start_date=(
            str(first_row.get("JobStartDate"))
            if pd.notna(first_row.get("JobStartDate"))
            else None
        ),
        job_end_date=(
            str(first_row.get("JobEndDate"))
            if pd.notna(first_row.get("JobEndDate"))
            else None
        ),
        operator=(
            str(first_row.get("OperatorName"))
            if pd.notna(first_row.get("OperatorName"))
            else None
        ),
        well_name=(
            str(first_row.get("WellName"))
            if pd.notna(first_row.get("WellName"))
            else None
        ),
    )

    return aggregate, detail_rows
