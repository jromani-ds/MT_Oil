"""Tests for interference module."""

from mt_oil.domain import interference


class TestHaversine:
    def test_same_point(self):
        assert interference.haversine_distance(47.5, -105.2, 47.5, -105.2) == 0.0

    def test_known_distance(self):
        # ~111km per degree at equator
        d = interference.haversine_distance(0, 0, 0, 1)
        assert 111000 < d < 112000  # meters


class TestFindOffsetWells:
    def test_self_excluded(self):
        import pandas as pd

        df = pd.DataFrame(
            [
                {"API_WellNo": "2508323399", "latitude": 47.5, "longitude": -105.2},
                {"API_WellNo": "2508323400", "latitude": 47.5001, "longitude": -105.2},
            ]
        )
        offsets = interference.find_offset_wells("2508323399", df, radius_m=100)
        assert len(offsets) == 1
        assert offsets[0]["api_wellno"] == "2508323400"
        assert "distance_method" in offsets[0]


class TestDetectFracHitsConfidence:
    def _make_prod_df(self):
        import pandas as pd

        # Child frac date: 2020-07-01
        # Baseline (Jan-Jun 2020): high oil, low water
        # After (Jul-Sep 2020): oil drops, water spikes (frac hit signature)
        rows = []
        for month in range(1, 7):
            rows.append(
                {
                    "API_WellNo": "2508323400",
                    "Rpt_Date": pd.Timestamp(f"2020-{month:02d}-15"),
                    "BBLS_OIL_COND": 1000.0,
                    "MCF_GAS": 500.0,
                    "BBLS_WTR": 50.0,
                }
            )
        for month in range(7, 10):
            rows.append(
                {
                    "API_WellNo": "2508323400",
                    "Rpt_Date": pd.Timestamp(f"2020-{month:02d}-15"),
                    "BBLS_OIL_COND": 400.0,
                    "MCF_GAS": 400.0,
                    "BBLS_WTR": 400.0,
                }
            )
        return pd.DataFrame(rows)

    def test_frac_hit_high_confidence(self):
        prod = self._make_prod_df()
        hits = interference.detect_frac_hits(
            child_api_number="2508323399",
            child_frac_date="2020-07-01",
            offsets=[{"api_wellno": "2508323400", "distance_m": 200.0}],
            prod_df=prod,
            window_months=3,
        )
        assert len(hits) == 1
        hit = hits[0]
        assert hit["confidence"] >= 0.7
        assert hit["mechanism"] == "frac_hit"
        assert "water_cut_delta_pct" in hit
        assert hit["water_cut_delta_pct"] > 10  # water cut spiked

    def test_no_corroboration_low_confidence(self):
        import pandas as pd

        # Oil drops but no water/GOR signal → possible_interference, moderate confidence
        rows = []
        for month in range(1, 7):
            rows.append(
                {
                    "API_WellNo": "2508323400",
                    "Rpt_Date": pd.Timestamp(f"2020-{month:02d}-15"),
                    "BBLS_OIL_COND": 1000.0,
                    "MCF_GAS": 500.0,
                    "BBLS_WTR": 100.0,
                }
            )
        for month in range(7, 10):
            rows.append(
                {
                    "API_WellNo": "2508323400",
                    "Rpt_Date": pd.Timestamp(f"2020-{month:02d}-15"),
                    "BBLS_OIL_COND": 600.0,
                    "MCF_GAS": 300.0,
                    "BBLS_WTR": 60.0,
                }
            )
        prod = pd.DataFrame(rows)
        hits = interference.detect_frac_hits(
            child_api_number="2508323399",
            child_frac_date="2020-07-01",
            offsets=[{"api_wellno": "2508323400", "distance_m": 200.0}],
            prod_df=prod,
            window_months=3,
        )
        # Water cut stays ~same, GOR same → only oil drop >20%
        # (1000→600 = 40% drop) but no corroboration
        if hits:
            assert hits[0]["mechanism"] in ("possible_interference", "low_confidence")

    def test_no_drop_skipped(self):
        import pandas as pd

        rows = []
        for month in range(1, 10):
            rows.append(
                {
                    "API_WellNo": "2508323400",
                    "Rpt_Date": pd.Timestamp(f"2020-{month:02d}-15"),
                    "BBLS_OIL_COND": 1000.0,
                    "MCF_GAS": 500.0,
                    "BBLS_WTR": 100.0,
                }
            )
        prod = pd.DataFrame(rows)
        hits = interference.detect_frac_hits(
            child_api_number="2508323399",
            child_frac_date="2020-07-01",
            offsets=[{"api_wellno": "2508323400", "distance_m": 200.0}],
            prod_df=prod,
            window_months=3,
        )
        assert hits == []
