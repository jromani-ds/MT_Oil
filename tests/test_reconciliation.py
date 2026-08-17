"""Tests for the reconciliation engine."""

from mt_oil.reconciliation.engine import (
    _compute_net_perforated_ft,
    _is_blank,
    _variance_pct,
)
from mt_oil.reconciliation.schemas import (
    ProvenanceTag,
    ReconciledStimulation,
    SourceView,
    VarianceReport,
)


class TestIsBlank:
    def test_none_is_blank(self):
        assert _is_blank(None) is True

    def test_empty_string_is_blank(self):
        assert _is_blank("") is True

    def test_na_is_blank(self):
        assert _is_blank("N/A") is True

    def test_acidized_fraced_is_blank(self):
        assert _is_blank("acidized/fraced") is True

    def test_numeric_string_is_not_blank(self):
        assert _is_blank("0.5") is False

    def test_large_number_string_is_not_blank(self):
        assert _is_blank("1000") is False

    def test_nan_is_blank(self):
        assert _is_blank(float("nan")) is True


class TestVariancePct:
    def test_state_100_ff_110_returns_10(self):
        result = _variance_pct(100.0, 110.0)
        assert result == 10.0

    def test_state_100_ff_50_returns_50(self):
        result = _variance_pct(100.0, 50.0)
        assert result == 50.0

    def test_state_zero_returns_none(self):
        result = _variance_pct(0.0, 100.0)
        assert result is None

    def test_state_none_returns_none(self):
        result = _variance_pct(None, 100.0)
        assert result is None

    def test_ff_none_returns_none(self):
        result = _variance_pct(100.0, None)
        assert result is None


class TestComputeNetPerforatedFt:
    def test_two_open_perforations_sum(self):
        perfs = [
            {"top_md_ft": 10000.0, "bottom_md_ft": 10050.0, "status": "open"},
            {"top_md_ft": 10100.0, "bottom_md_ft": 10130.0, "status": "open"},
        ]
        result = _compute_net_perforated_ft(perfs)
        assert result == 80.0

    def test_closed_perforations_excluded(self):
        perfs = [
            {"top_md_ft": 10000.0, "bottom_md_ft": 10050.0, "status": "open"},
            {"top_md_ft": 10100.0, "bottom_md_ft": 10140.0, "status": "closed"},
        ]
        result = _compute_net_perforated_ft(perfs)
        assert result == 50.0

    def test_squeezed_perforations_excluded(self):
        perfs = [
            {"top_md_ft": 10000.0, "bottom_md_ft": 10050.0, "status": "open"},
            {"top_md_ft": 10100.0, "bottom_md_ft": 10140.0, "status": "squeezed"},
        ]
        result = _compute_net_perforated_ft(perfs)
        assert result == 50.0

    def test_empty_list_returns_zero(self):
        assert _compute_net_perforated_ft([]) == 0.0

    def test_no_open_status_still_included(self):
        perfs = [
            {"top_md_ft": 10000.0, "bottom_md_ft": 10050.0, "status": ""},
        ]
        result = _compute_net_perforated_ft(perfs)
        assert result == 50.0


class TestReconciliationSchemas:
    def test_provenance_tag_defaults(self):
        tag = ProvenanceTag(
            source="FracFocus (Disclosed)", field_name="total_proppant_lbs"
        )
        assert tag.source == "FracFocus (Disclosed)"
        assert tag.field_name == "total_proppant_lbs"
        assert tag.original_value is None

    def test_source_view_defaults(self):
        view = SourceView()
        assert view.total_clean_fluid_bbls is None
        assert view.provenance == []

    def test_variance_report_defaults(self):
        report = VarianceReport(status="Verified / Harmonized")
        assert report.status == "Verified / Harmonized"
        assert report.fluid_volume_delta_pct is None

    def test_reconciled_stimulation_defaults(self):
        r = ReconciledStimulation(api_number="2508323399")
        assert r.api_number == "2508323399"
        assert r.badge == "green"
        assert r.sanity_findings == []


class TestCweNormalization:
    def test_variance_reduced_with_cwe(self):
        """Verify that CWE normalization reduces false-positive variance."""
        from mt_oil.fracfocus.units import to_clean_water_equivalent

        # Sand displacement: 2M lbs * 0.0456 gal/lb = 91,200 gal = 2,171 bbl
        cwe = to_clean_water_equivalent(110_000, 2_000_000)
        assert cwe < 110_000
        var_cwe = abs(100_000 - cwe) / 100_000 * 100
        var_raw = abs(100_000 - 110_000) / 100_000 * 100
        assert var_cwe < var_raw
        # CWE pushes below 10% threshold, raw pushes above it
        assert var_cwe < 10
        assert var_raw >= 10
