"""Tests for fluid PVT module."""

from mt_oil.domain import pvt


class TestGasSpecificGravity:
    def test_methane(self):
        sg = pvt.gas_specific_gravity({"c1": 1.0})
        assert sg is not None
        assert round(sg, 4) == round(16.043 / 28.97, 4)

    def test_none(self):
        assert pvt.gas_specific_gravity({}) is None


class TestWichertAziz:
    def test_sweet_gas_no_correction(self):
        _sg, applied = pvt.corrected_gas_gravity({"c1": 0.95, "c2": 0.05})
        assert applied is False

    def test_sour_gas_applies_correction(self):
        comp = {"c1": 0.80, "h2s": 0.10, "co2": 0.05, "n2": 0.05}
        sg_corr, applied = pvt.corrected_gas_gravity(comp)
        assert applied is True
        # Corrected gravity should differ from raw
        raw = pvt.gas_specific_gravity(comp)
        assert sg_corr != raw

    def test_below_threshold_no_correction(self):
        # 2% H2S is below 3% threshold
        _sg, applied = pvt.corrected_gas_gravity({"c1": 0.98, "h2s": 0.02})
        assert applied is False

    def test_epsilon_positive_for_sour(self):
        assert pvt.wichert_aziz_epsilon(0.10, 0.05) > 0
        assert pvt.wichert_aziz_epsilon(0.0, 0.0) == 0


class TestBubblePoint:
    def test_basic(self):
        pb = pvt.bubble_point_standing(500, 0.65, 40, 150)
        assert pb is not None
        assert pb > 0


class TestOilViscosity:
    def test_returns_positive(self):
        mu = pvt.oil_viscosity_beggs_robinson(40, 150)
        assert mu is not None
        assert mu > 0


class TestOilFVF:
    def test_bo_above_one(self):
        bo = pvt.oil_fvf_standing(500, 0.65, 40, 150)
        assert bo is not None
        assert bo >= 1.0


class TestBelowBubblePoint:
    def test_below(self):
        result = pvt.below_bubble_point_check(500, 3000, 2000)
        assert result is not None
        assert result["below_bubble_point"] is True

    def test_above(self):
        result = pvt.below_bubble_point_check(500, 3000, 4000)
        assert result is not None
        assert result["below_bubble_point"] is False
