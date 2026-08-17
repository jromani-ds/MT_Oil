"""Tests for lithology classification."""

from mt_oil.domain.lithology import classify_lithology


class TestClassifyLithology:
    def test_red_river_is_carbonate(self):
        result = classify_lithology("Red River")
        assert result.is_carbonate is True
        assert result.lithology == "carbonate"

    def test_bakken_is_not_carbonate(self):
        result = classify_lithology("Bakken")
        assert result.is_carbonate is False
        assert result.lithology == "siliciclastic"

    def test_empty_string_returns_fallback(self):
        result = classify_lithology("")
        assert result.is_carbonate is False
        assert result.lithology == "unknown"
        assert result.confidence == 0.0

    def test_case_insensitive(self):
        result = classify_lithology("red river")
        assert result.is_carbonate is True

    def test_unknown_formation_returns_fallback(self):
        result = classify_lithology("Nonexistent Formation XYZ")
        assert result.lithology == "unknown"
        assert result.is_carbonate is False
