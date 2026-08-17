"""Tests for gas properties module (Z-factor, downhole volumes)."""

from mt_oil.domain import gas


class TestHallYarboroughZ:
    def test_surface_conditions(self):
        # At low pressure, Z should be close to 1
        z = gas.hall_yarborough_z(100, 520, 0.65)
        assert 0.9 < z < 1.1

    def test_downhole_compressibility(self):
        # At 8000 psi / 200°F, Z > 1 for a gas
        z = gas.hall_yarborough_z(8000, 660, 0.65)
        assert z > 1.0

    def test_sour_gas_has_different_z(self):
        z_sweet = gas.hall_yarborough_z(8000, 660, 0.65)
        z_sour = gas.hall_yarborough_z(
            8000, 660, 0.65, h2s_mol_frac=0.1, co2_mol_frac=0.05
        )
        assert z_sweet != z_sour


class TestDownholeGasVolume:
    def test_compressibility_reduces_volume(self):
        # 1M SCF at surface = 7.48M gal; downhole at 8000 psi should be much less
        v_dh = gas.downhole_gas_volume(1_000_000, 8000, 660, 0.65)
        assert v_dh is not None
        assert v_dh < 1_000_000  # compressed
        surface_equiv = 1_000_000 * 7.4805
        assert v_dh < surface_equiv / 100  # ~100x+ compression at 8000 psi

    def test_zero_inputs(self):
        assert gas.downhole_gas_volume(0, 8000, 660) is None
        assert gas.downhole_gas_volume(1000, None, 660) is None


class TestDownholeGasDensity:
    def test_density_positive(self):
        z = gas.hall_yarborough_z(8000, 660, 0.65)
        rho = gas.downhole_gas_density_ppg(8000, z, 660, 0.65)
        assert rho is not None
        assert rho > 0


class TestBhpEstimate:
    def test_hydrostatic_added(self):
        # 8000 psi + 0.433 * 10000 ft
        assert gas.bhp_estimate(8000, 10000) == 8000 + 4330
