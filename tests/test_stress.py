"""Tests for rock mechanics / stress module."""

from mt_oil.domain import stress


class TestSigmaHmin:
    def test_closure_equals_hmin(self):
        assert stress.sigma_hmin(5000) == 5000


class TestStressGradient:
    def test_basic(self):
        assert stress.stress_gradient(5000, 10000) == 0.5

    def test_zero_tvd(self):
        assert stress.stress_gradient(5000, 0) is None


class TestClassifyLeakoff:
    def test_pdl(self):
        assert stress.classify_leakoff("pressure dependent leakoff") == "pdl"

    def test_normal(self):
        assert stress.classify_leakoff("normal matrix leakoff") == "normal"

    def test_height(self):
        assert (
            stress.classify_leakoff("height recession observed") == "height_recession"
        )

    def test_empty(self):
        assert stress.classify_leakoff(None) is None
        assert stress.classify_leakoff("") is None

    def test_unknown(self):
        assert stress.classify_leakoff("low permeability formation") is None


class TestFrictionSplit:
    def test_three_points(self):
        # Construct synthetic step-down data with known behavior
        pairs = [
            {"rate_bpm": 10, "isip_psi": 5000},
            {"rate_bpm": 20, "isip_psi": 5300},
            {"rate_bpm": 30, "isip_psi": 5700},
        ]
        result = stress.friction_split(pairs)
        assert result is not None
        assert "closure_pressure_psi" in result
        assert "perf_friction_coef" in result
        assert "nwb_tortuosity_coef" in result

    def test_insufficient_data(self):
        single = stress.friction_split([{"rate_bpm": 10, "isip_psi": 5000}])
        assert single["status"] == "indeterminate"
        assert "multi-rate" in single["reason"].lower()

        empty = stress.friction_split([])
        assert empty["status"] == "indeterminate"

        two = stress.friction_split(
            [{"rate_bpm": 10, "isip_psi": 5000}, {"rate_bpm": 20, "isip_psi": 5300}]
        )
        assert two["status"] == "indeterminate"

    def test_computed_status(self):
        pairs = [
            {"rate_bpm": 10, "isip_psi": 5000},
            {"rate_bpm": 20, "isip_psi": 5300},
            {"rate_bpm": 30, "isip_psi": 5700},
        ]
        result = stress.friction_split(pairs)
        assert result["status"] == "computed"
        assert "closure_pressure_psi" in result


class TestFractureGradientPressure:
    def test_gradient(self):
        from mt_oil.domain.stress import fracture_gradient_pressure

        # 8000 psi surface + hydrostatic at 10000ft, fluid sg 1.0
        bhp = 8000 + 0.433 * 10000
        expected = round(bhp / 10000, 5)
        assert fracture_gradient_pressure(8000, 10000) == expected
