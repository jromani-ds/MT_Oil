"""Tests for FracFocus classification and unit conversion modules."""

from mt_oil.fracfocus.classify import (
    classify_acids,
    classify_additive,
    classify_gas,
    classify_proppant_category,
)
from mt_oil.fracfocus.units import (
    co2_ton_to_bbl,
    gal_to_bbl,
    lb_to_ton,
    mscf_to_scf,
    n2_ton_to_scf,
    to_clean_water_equivalent,
)


class TestUnits:
    def test_gal_to_bbl(self):
        assert gal_to_bbl(42.0) == 1.0
        assert gal_to_bbl(0.0) == 0.0
        assert gal_to_bbl(84.0) == 2.0

    def test_to_clean_water_equivalent(self):
        # 100 bbl slurry with 2,000,000 lbs proppant
        # displacement = 2M * 0.0456 gal = 91,200 gal = 2171 bbl
        cwe = to_clean_water_equivalent(100.0, 2_000_000.0)
        assert cwe < 100.0  # CWE is always <= slurry volume
        # Without proppant, unchanged
        assert to_clean_water_equivalent(100.0, None) == 100.0
        assert to_clean_water_equivalent(100.0, 0) == 100.0

    def test_n2_ton_to_scf(self):
        result = n2_ton_to_scf(1.0)
        assert result == 27200.0
        assert n2_ton_to_scf(0.5) == 13600.0

    def test_co2_ton_to_bbl(self):
        result = co2_ton_to_bbl(1.0)
        assert result == 17.47
        assert co2_ton_to_bbl(2.0) == 34.94

    def test_mscf_to_scf(self):
        assert mscf_to_scf(1.0) == 1000.0
        assert mscf_to_scf(0.5) == 500.0

    def test_lb_to_ton(self):
        assert lb_to_ton(2000.0) == 1.0
        assert lb_to_ton(5000.0) == 2.5


class TestClassifyAcids:
    def test_hcl_cas_returns_true(self):
        assert classify_acids(purpose=None, ingredient=None, cas="7647-01-0") is True

    def test_acetic_acid_cas_returns_true(self):
        assert classify_acids(purpose=None, ingredient=None, cas="64-19-7") is True

    def test_purpose_acid_returns_true(self):
        assert classify_acids(purpose="acid", ingredient=None, cas=None) is True

    def test_ingredient_acid_keyword_returns_true(self):
        assert classify_acids(purpose=None, ingredient="HCl 15%", cas=None) is True

    def test_non_acid_returns_false(self):
        assert (
            classify_acids(
                purpose="friction reducer", ingredient="polyacrylamide", cas="9003-05-8"
            )
            is False
        )

    def test_none_returns_false(self):
        assert classify_acids(purpose=None, ingredient=None, cas=None) is False


class TestClassifyProppantCategory:
    def test_silica_cas_returns_silica(self):
        result = classify_proppant_category(
            purpose="proppant", ingredient=None, cas="14808-60-7"
        )
        assert result == "silica"

    def test_ceramic_cas_returns_ceramic(self):
        result = classify_proppant_category(
            purpose="proppant", ingredient=None, cas="1344-28-1"
        )
        assert result == "ceramic"

    def test_diverter_cas_returns_diverter(self):
        result = classify_proppant_category(
            purpose="proppant", ingredient=None, cas="7647-14-5"
        )
        assert result == "diverter"

    def test_resin_coated_keyword_returns_resin_coated(self):
        result = classify_proppant_category(
            purpose="proppant", ingredient="Resin Coated Sand", cas=None
        )
        assert result == "resin_coated"

    def test_sand_keyword_returns_silica(self):
        result = classify_proppant_category(
            purpose="proppant", ingredient="Sand 20/40", cas=None
        )
        assert result == "silica"

    def test_not_proppant_returns_none(self):
        result = classify_proppant_category(
            purpose="gel", ingredient="guar gum", cas=None
        )
        assert result is None

    def test_unknown_returns_other(self):
        result = classify_proppant_category(
            purpose="proppant", ingredient="walnut shells", cas=None
        )
        assert result == "other"


class TestClassifyAdditive:
    def test_friction_reducer_cas(self):
        result = classify_additive(purpose=None, ingredient=None, cas="9003-05-8")
        assert result == "friction_reducer"

    def test_biocide_cas(self):
        result = classify_additive(purpose=None, ingredient=None, cas="111-30-8")
        assert result == "biocide"

    def test_scale_inhibitor_purpose(self):
        result = classify_additive(purpose="scale inhibitor", ingredient=None, cas=None)
        assert result == "scale_inhibitor"

    def test_crosslinker_keyword(self):
        result = classify_additive(
            purpose=None, ingredient="Borate crosslinker", cas=None
        )
        assert result == "crosslinker"

    def test_surfactant_ingredient(self):
        result = classify_additive(
            purpose=None, ingredient="Surfactant blend", cas=None
        )
        assert result == "surfactant"

    def test_friction_reducer_ingredient_keyword(self):
        result = classify_additive(purpose=None, ingredient="FR-1", cas=None)
        assert result == "friction_reducer"

    def test_unknown_returns_other(self):
        result = classify_additive(purpose=None, ingredient="water", cas=None)
        assert result == "other"


class TestClassifyGas:
    def test_n2_cas(self):
        result = classify_gas(ingredient=None, cas="7727-37-9")
        assert result == "N2"

    def test_co2_cas(self):
        result = classify_gas(ingredient=None, cas="124-38-9")
        assert result == "CO2"

    def test_nitrogen_ingredient(self):
        result = classify_gas(ingredient="Nitrogen", cas=None)
        assert result == "N2"

    def test_co2_ingredient(self):
        result = classify_gas(ingredient="Carbon Dioxide", cas=None)
        assert result == "CO2"

    def test_unknown_returns_none(self):
        result = classify_gas(ingredient="water", cas=None)
        assert result is None
