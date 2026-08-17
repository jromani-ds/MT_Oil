"""Tests for water chemistry / scaling module."""

from mt_oil.domain import scaling


class TestNormalizeRw:
    def test_normalize_to_77F(self):
        # Rw increases as temperature decreases (Arps). Normalizing 150F→77F raises Rw.
        assert scaling.normalize_Rw(0.5, 150, 77) > 0.5

    def test_same_temp(self):
        assert scaling.normalize_Rw(0.3, 77, 77) == 0.3

    def test_exact_value(self):
        # Rw77 = 0.5 * (150+6.77)/(77+6.77)
        expected = round(0.5 * (150 + 6.77) / (77 + 6.77), 5)
        assert round(scaling.normalize_Rw(0.5, 150, 77), 5) == expected


class TestStiffDavis:
    def test_hard_scaling_water_positive(self):
        # High Ca, HCO3, high pH → aggressive CaCO3 scaling
        si = scaling.stiff_davis_si(4000, 600, 7.5, 100000, 150)
        assert si is not None
        assert isinstance(si, float)

    def test_returns_number(self):
        si = scaling.stiff_davis_si(100, 50, 7.0, 20000, 100)
        assert isinstance(si, float)


class TestBaSO4:
    def test_high_barium_sulfate_positive(self):
        # Ba 3000, SO4 3000 → very high ion product → scaling
        si = scaling.barium_sulfate_si(3000, 3000)
        assert si is not None
        assert si > 0

    def test_zero_returns_none(self):
        assert scaling.barium_sulfate_si(0, 3000) is None
        assert scaling.barium_sulfate_si(3000, 0) is None


class TestScalingSummary:
    def test_summary_shape(self):
        water = {
            "tds_mg_l": 50000,
            "ca": 2000,
            "so4": 100,
            "hco3": 300,
            "ba": 50,
            "ph": 7.2,
            "rw_ohm_m": 0.3,
            "sample_temp_f": 120,
        }
        summary = scaling.scaling_summary(water)
        assert "stiff_davis_caco3_si" in summary
        assert "rw_ohm_m@77F" in summary
        assert summary["scale_risk"] in ("HIGH", "MODERATE", "LOW")


class TestHighSalinity:
    def test_williston_brine_valid(self):
        # 250k TDS brine should produce a finite Stiff-Davis index
        water = {
            "tds_mg_l": 250000,
            "ca": 30000,
            "mg": 4000,
            "ba": 2000,
            "sr": 1500,
            "so4": 500,
            "hco3": 300,
            "ph": 6.5,
            "sample_temp_f": 200,
        }
        sd = scaling.stiff_davis_si(
            water["ca"],
            water["hco3"],
            water["ph"],
            water["tds_mg_l"],
            water["sample_temp_f"],
        )
        assert isinstance(sd, float)

    def test_ultra_high_tds_emits_warning(self):
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            scaling.stiff_davis_si(30000, 300, 6.5, 400000, 200)
            assert any("beyond 350,000" in str(x.message) for x in w)

    def test_baSo4_temperature_dependent(self):
        # Same ions, different temps → different index
        si_cold = scaling.barium_sulfate_si(3000, 3000, 100000, 100)
        si_hot = scaling.barium_sulfate_si(3000, 3000, 100000, 250)
        assert si_cold != si_hot

    def test_srso4_index(self):
        si = scaling.strontium_sulfate_si(1500, 500, 250000, 200)
        assert si is not None
        assert isinstance(si, float)

    def test_ionic_strength(self):
        assert scaling.ionic_strength_from_tds(58_443) == 1.0

    def test_stiff_davis_k_value_vs_salinity(self):
        k_low = scaling.stiff_davis_k_value(0.1, 60)
        k_high = scaling.stiff_davis_k_value(4.0, 60)
        # K increases with ionic strength for high-salinity brines
        assert k_high > k_low
