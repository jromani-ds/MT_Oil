"""Tests for tortuosity and directional survey modules."""

from mt_oil.domain import tortuosity


class TestComputeDLS:
    def test_vertical_no_change(self):
        # 0° inc, 0° az → 0° inc, 0° az → 0 DLS
        assert tortuosity.compute_dls(0, 0, 0, 0, 100) == 0.0

    def test_lateral_dogleg(self):
        # 90° inc, 0° az → 90° inc, 5° az → ~5°/100ft
        dls = tortuosity.compute_dls(90, 0, 90, 5, 100)
        assert dls is not None
        assert dls > 0

    def test_zero_delta_md(self):
        assert tortuosity.compute_dls(90, 0, 90, 5, 0) is None


class TestEnrichSurvey:
    def test_first_point_has_zero_dls(self):
        points = [
            {"md_ft": 0, "inclination_deg": 0, "azimuth_deg": 0, "tvd_ft": 0},
            {"md_ft": 100, "inclination_deg": 90, "azimuth_deg": 0, "tvd_ft": 100},
        ]
        enriched = tortuosity.enrich_survey_with_dls(points)
        assert len(enriched) == 2
        assert enriched[0]["dls_deg_per_100ft"] == 0.0
        assert enriched[1]["dls_deg_per_100ft"] > 0


class TestTortuosityHotspots:
    def test_no_hotspots(self):
        points = [
            {
                "md_ft": 10000,
                "inclination_deg": 90,
                "azimuth_deg": 0,
                "tvd_ft": 8000,
                "dls_deg_per_100ft": 1.0,
            },
            {
                "md_ft": 10100,
                "inclination_deg": 90,
                "azimuth_deg": 1,
                "tvd_ft": 8000,
                "dls_deg_per_100ft": 1.5,
            },
        ]
        assert tortuosity.find_tortuosity_hotspots(points, threshold_dls=3.0) == []

    def test_hotspot_detected(self):
        points = [
            {
                "md_ft": 10000,
                "inclination_deg": 90,
                "azimuth_deg": 0,
                "tvd_ft": 8000,
                "dls_deg_per_100ft": 5.0,
            },
        ]
        hotspots = tortuosity.find_tortuosity_hotspots(points, threshold_dls=3.0)
        assert len(hotspots) == 1
        assert hotspots[0]["dls_deg_per_100ft"] == 5.0


class TestMaxDlsInLateral:
    def test_max_dls(self):
        points = [
            {"inclination_deg": 90, "dls_deg_per_100ft": 2.0},
            {"inclination_deg": 90, "dls_deg_per_100ft": 5.0},
            {"inclination_deg": 45, "dls_deg_per_100ft": 10.0},  # not lateral
        ]
        assert tortuosity.max_dls_in_lateral(points) == 5.0


class TestLandedPosition:
    def test_in_zone(self):
        survey = [
            {"md_ft": 10000, "tvd_ft": 9950, "inclination_deg": 90, "azimuth_deg": 0}
        ]
        tops = [{"formation_name": "Bakken", "tvd_ft": 9900}]
        result = tortuosity.check_landed_position(survey, tops)
        assert result is not None
        assert result["assessment"] == "IN_ZONE"

    def test_no_data(self):
        assert tortuosity.check_landed_position([], []) is None
