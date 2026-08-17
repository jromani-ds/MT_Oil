"""Tests for engineering sanity check rules."""

from mt_oil.sanity.sanity_check import (
    check_acid_volume,
    check_choke,
    check_ppa,
    check_treating_pressure,
    compute_badge,
)


class TestCheckPpa:
    def test_normal_ppa_returns_green(self):
        findings = check_ppa(proppant_lbs=100000.0, clean_water_gal=50000.0)
        assert len(findings) == 1
        assert findings[0].severity == "green"
        assert findings[0].rule == "PPA"

    def test_high_ppa_returns_red(self):
        findings = check_ppa(proppant_lbs=550000.0, clean_water_gal=50000.0)
        assert len(findings) == 1
        assert findings[0].severity == "red"

    def test_acid_only_zero_proppant_returns_green(self):
        findings = check_ppa(
            proppant_lbs=0, clean_water_gal=None, treatment_class="matrix_acidizing"
        )
        assert len(findings) == 1
        assert findings[0].severity == "green"
        assert findings[0].raw_value == 0.0

    def test_acid_only_with_proppant_returns_red(self):
        findings = check_ppa(
            proppant_lbs=5000.0, clean_water_gal=None, treatment_class="acid_breakdown"
        )
        assert len(findings) == 1
        assert findings[0].severity == "red"


class TestCheckChoke:
    def test_small_choke_returns_green(self):
        findings = check_choke(0.375)
        assert len(findings) == 1
        assert findings[0].severity == "green"

    def test_value_24_normalized_returns_yellow(self):
        findings = check_choke(24)
        assert len(findings) == 1
        assert findings[0].severity == "yellow"
        assert findings[0].corrected_value == 24.0 / 64.0

    def test_very_high_value_returns_red(self):
        findings = check_choke(200)
        assert len(findings) == 1
        assert findings[0].severity == "red"

    def test_none_returns_empty(self):
        findings = check_choke(None)
        assert findings == []


class TestCheckTreatingPressure:
    def test_normal_pressure_returns_green(self):
        findings = check_treating_pressure(surface_pressure_psi=5000.0, tvd_ft=10000.0)
        assert any(f.severity == "green" for f in findings)

    def test_burst_pressure_returns_red(self):
        findings = check_treating_pressure(surface_pressure_psi=16000.0, tvd_ft=10000.0)
        assert any(f.severity == "red" for f in findings)
        assert any("burst" in f.message.lower() for f in findings)

    def test_low_fracture_gradient_returns_red(self):
        findings = check_treating_pressure(surface_pressure_psi=1000.0, tvd_ft=10000.0)
        assert any(f.severity == "red" for f in findings)
        assert any("gradient" in f.message.lower() for f in findings)

    def test_none_tvd_returns_empty(self):
        findings = check_treating_pressure(surface_pressure_psi=8000.0, tvd_ft=None)
        assert findings == []


class TestCheckAcidVolume:
    def test_acid_exceeds_carrier_returns_red(self):
        findings = check_acid_volume(
            acid_volume_gal=10000.0, total_carrier_volume_gal=5000.0
        )
        assert any(f.severity == "red" for f in findings)
        assert any("exceeds" in f.message.lower() for f in findings)

    def test_matrix_intensity_carbonate_returns_green(self):
        findings = check_acid_volume(
            acid_volume_gal=15000.0,
            total_carrier_volume_gal=30000.0,
            net_perforated_ft=100.0,
            is_carbonate=True,
        )
        assert any(f.severity == "green" for f in findings)
        assert any("matrix" in f.message.lower() for f in findings)

    def test_acid_volume_zero_returns_empty(self):
        findings = check_acid_volume(acid_volume_gal=0, total_carrier_volume_gal=1000.0)
        assert findings == []

    def test_no_carrier_does_not_crash(self):
        findings = check_acid_volume(
            acid_volume_gal=500.0, total_carrier_volume_gal=None, net_perforated_ft=50.0
        )
        assert len(findings) >= 0


class TestComputeBadge:
    def test_all_green_returns_green(self):
        from mt_oil.sanity.schemas import SanityFinding

        findings = [
            SanityFinding(rule="PPA", severity="green", message="ok"),
            SanityFinding(rule="Choke64ths", severity="green", message="ok"),
        ]
        assert compute_badge(findings) == "green"

    def test_one_yellow_returns_yellow(self):
        from mt_oil.sanity.schemas import SanityFinding

        findings = [
            SanityFinding(rule="PPA", severity="green", message="ok"),
            SanityFinding(rule="Choke64ths", severity="yellow", message="unusual"),
        ]
        assert compute_badge(findings) == "yellow"

    def test_one_red_returns_red(self):
        from mt_oil.sanity.schemas import SanityFinding

        findings = [
            SanityFinding(rule="PPA", severity="green", message="ok"),
            SanityFinding(rule="TreatingPressure", severity="red", message="burst"),
        ]
        assert compute_badge(findings) == "red"

    def test_empty_returns_green(self):
        assert compute_badge([]) == "green"
