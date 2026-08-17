"""Tests for geodetic CRS module (NAD27→NAD83, UTM projection, projected distance)."""

from mt_oil.domain import crs


class TestDatumInference:
    def test_pre_1990_nad27(self):
        assert crs.infer_datum_row("1985-06-01") == "nad27"

    def test_post_1990_nad83(self):
        assert crs.infer_datum_row("2005-06-01") == "nad83_wgs84"

    def test_none(self):
        assert crs.infer_datum_row(None) == "wgs84_assumed"


class TestNad27ToNad83:
    def test_shift_is_reasonable(self):
        lat, lon = crs.nad27_to_nad83(45.7833, -108.5007)
        # Shift should be ~10-40m scale (~0.0001-0.001 deg)
        assert abs(lat - 45.7833) < 0.01
        assert abs(lon - -108.5007) < 0.01


class TestToUtm13n:
    def test_montana_point(self):
        easting, northing = crs.to_utm13n(47.5, -105.2)
        # Zone 13 central meridian -105W → easting near 500k
        assert 400_000 < easting < 600_000
        # Northern hemisphere northing > 0
        assert northing > 1_000_000


class TestProjectedDistance:
    def test_same_point(self):
        dist, _method = crs.projected_distance(47.5, -105.2, 47.5, -105.2)
        assert dist < 1.0

    def test_nearby_wells(self):
        dist, method = crs.projected_distance(47.5, -105.2, 47.5010, -105.2)
        # ~111m per 0.001 deg latitude
        assert 90 < dist < 140
        assert "utm13n_projected" in method

    def test_mixed_datum_flag(self):
        _, method = crs.projected_distance(
            47.5, -105.2, 47.5010, -105.2, datum1="nad27", datum2="nad83_wgs84"
        )
        assert "mixed_datum" in method


class TestHaversineFallback:
    def test_kept_as_fallback(self):
        assert crs.haversine_distance(47.5, -105.2, 47.5, -105.2) == 0.0
        d = crs.haversine_distance(0, 0, 0, 1)
        assert 111_000 < d < 112_000
