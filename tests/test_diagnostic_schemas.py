"""Tests for new diagnostic schemas."""

from mt_oil.schemas.wellfile import (
    DiagnosticData,
    DirectionalSurvey,
    FlowbackData,
    FluidPvt,
    GasMoleFractions,
    StepRateTest,
    SurveyPoint,
    WaterAnalysis,
    WellfileExtractionPayload,
)


class TestDiagnosticData:
    def test_defaults(self):
        d = DiagnosticData()
        assert d.step_rate_tests == []
        assert d.breakdown_pressure_psi is None

    def test_full(self):
        d = DiagnosticData(
            step_rate_tests=[StepRateTest(rate_bpm=10, isip_psi=5000)],
            breakdown_pressure_psi=8000,
            closure_pressure_psi=6000,
        )
        assert d.step_rate_tests[0].isip_psi == 5000


class TestWaterAnalysis:
    def test_defaults(self):
        w = WaterAnalysis()
        assert w.tds_mg_l is None
        assert w.ca_mg_l is None


class TestFluidPvt:
    def test_gas_mole_fractions(self):
        g = GasMoleFractions(c1=0.9, n2=0.05, co2=0.05)
        assert g.c1 == 0.9

    def test_full(self):
        f = FluidPvt(oil_api_gravity=40, bubble_point_psi=3000)
        assert f.oil_api_gravity == 40


class TestFlowbackData:
    def test_defaults(self):
        f = FlowbackData()
        assert f.swab_tally == []
        assert f.proppant_flowback == []


class TestDirectionalSurvey:
    def test_all_stations_kept(self):
        s = DirectionalSurvey(
            survey_points=[
                SurveyPoint(md_ft=0, inclination_deg=0, azimuth_deg=0, tvd_ft=0),
                SurveyPoint(md_ft=100, inclination_deg=90, azimuth_deg=0, tvd_ft=100),
            ]
        )
        assert len(s.survey_points) == 2

    def test_default_empty(self):
        s = DirectionalSurvey()
        assert s.survey_points == []


class TestPayloadExtension:
    def test_new_sections_none_by_default(self):
        p = WellfileExtractionPayload()
        assert p.diagnostics is None
        assert p.water_chemistry is None
        assert p.fluid_pvt is None
        assert p.flowback is None
        assert p.directional_survey is None
