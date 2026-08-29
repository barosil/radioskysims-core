"""
Módulo: tests/domain/common/test_science_validator.py

Descrição:
    Testes unitários para ScienceValidator.
    Valida comportamento de validações de física (radioastronomia padrão).
"""

from __future__ import annotations

import numpy as np
import pytest
import xarray as xr
from scipy.constants import c, k

from radioskysims_core.domain.common.science_validator import ScienceValidator


def _solid_angle_deg(beam, angles):
    """Ω = 2π ∫₀^π B²(θ) sinθ dθ (ângulos em graus, metade positiva)."""
    angles = np.asarray(angles, dtype=float)
    beam = np.asarray(beam, dtype=float)
    idx = angles >= 0
    th = np.deg2rad(angles[idx])
    power = beam[idx] ** 2
    return float(np.sum(power * np.sin(th) * np.gradient(th)) * 2.0 * np.pi)


def _normalize_beam(beam, angles):
    """Normaliza o beam para ∫ B² dΩ = 1 (com sinθ, metade positiva)."""
    angles = np.asarray(angles, dtype=float)
    beam = np.asarray(beam, dtype=float)
    idx = angles >= 0
    th = np.deg2rad(angles[idx])
    power = beam[idx] ** 2
    integral = np.sum(power * np.sin(th) * np.gradient(th)) * 2.0 * np.pi
    return beam / np.sqrt(integral)


# Ω típico usado nos testes de conversão (feixe ~10° de FWHM → Ω ~ 1e-2 sr)
_OMEGA_TEST = 1.0e-2


class TestPSDUnits:
    """Testes para validação de unidades de PSD."""

    def test_psd_units_valid(self):
        """Deve passar quando unidades estão corretas."""
        data = xr.DataArray(
            [1.0, 2.0, 3.0],
            attrs={"units": "W/Hz"},
        )
        # Não deve levantar exceção
        ScienceValidator.validate_psd_units(data, expected_units="W/Hz")

    def test_psd_units_invalid(self):
        """Deve falhar quando unidades estão incorretas."""
        data = xr.DataArray(
            [1.0, 2.0, 3.0],
            attrs={"units": "V/Hz"},
        )
        with pytest.raises(ValueError, match="PSD units"):
            ScienceValidator.validate_psd_units(data, expected_units="W/Hz")

    def test_psd_units_missing(self):
        """Deve falhar quando unidades não são especificadas."""
        data = xr.DataArray([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="PSD units"):
            ScienceValidator.validate_psd_units(data, expected_units="W/Hz")

    def test_psd_units_custom_expected(self):
        """Deve validar com unidades customizadas."""
        data = xr.DataArray(
            [1.0, 2.0, 3.0],
            attrs={"units": "mW/Hz"},
        )
        # Deve passar
        ScienceValidator.validate_psd_units(data, expected_units="mW/Hz")

        # Deve falhar com outra unidade
        with pytest.raises(ValueError):
            ScienceValidator.validate_psd_units(data, expected_units="W/Hz")


class TestBeamNormalized:
    """Testes para validação de normalização do feixe."""

    def test_beam_normalized_valid(self):
        """Deve passar quando feixe está normalizado."""
        angles = np.linspace(-45, 45, 500)
        sigma = 10  # graus
        beam = np.exp(-0.5 * (angles / sigma) ** 2)
        beam = _normalize_beam(beam, angles)

        integral = ScienceValidator.validate_beam_normalized(beam, angles)

        # Integral deve estar em [0.95, 1.05]
        assert 0.95 <= integral <= 1.05

    def test_beam_normalized_return_value(self):
        """Deve retornar valor da integral."""
        angles = np.linspace(-45, 45, 300)
        sigma = 12
        beam = np.exp(-0.5 * (angles / sigma) ** 2)
        beam = _normalize_beam(beam, angles)

        integral = ScienceValidator.validate_beam_normalized(beam, angles)

        # Verificar que retorna float
        assert isinstance(integral, (float, np.floating))

    def test_beam_not_normalized_too_low(self):
        """Deve falhar quando integral < 0.95."""
        angles = np.linspace(-45, 45, 200)
        # Beam com integral pequena (muito concentrado)
        beam = np.exp(-(angles / 2) ** 2)

        with pytest.raises(ValueError, match="Beam integral"):
            ScienceValidator.validate_beam_normalized(beam, angles)

    def test_beam_not_normalized_too_high(self):
        """Deve falhar quando integral > 1.05."""
        angles = np.linspace(-45, 45, 100)
        # Beam com integral grande (muito largo)
        beam = np.ones_like(angles)

        with pytest.raises(ValueError, match="Beam integral"):
            ScienceValidator.validate_beam_normalized(beam, angles)

    def test_beam_sinc_like(self):
        """Deve validar beam tipo sinc (normalizado)."""
        angles = np.linspace(-15, 15, 300)
        x = np.deg2rad(angles)
        with np.errstate(divide="ignore", invalid="ignore"):
            beam = np.sinc(x / 0.1)
        beam = np.abs(beam)
        beam = _normalize_beam(beam, angles)

        integral = ScienceValidator.validate_beam_normalized(beam, angles)
        assert 0.95 <= integral <= 1.05

    def test_beam_flat(self):
        """Beam plano deve ter integral grande."""
        angles = np.linspace(-45, 45, 100)
        beam = np.ones_like(angles)

        with pytest.raises(ValueError, match="Beam integral"):
            ScienceValidator.validate_beam_normalized(beam, angles)

    def test_solid_angle_consistency(self):
        """Ω calculado deve coincidir com o helper de referência."""
        angles = np.linspace(-45, 45, 400)
        beam = _normalize_beam(np.exp(-0.5 * (angles / 10) ** 2), angles)
        assert ScienceValidator.validate_beam_normalized(beam, angles) == pytest.approx(
            _solid_angle_deg(beam, angles), rel=1e-9
        )


class TestTemperatureConversion:
    """Testes para validação de conversão PSD → Temperatura (Kraus)."""

    @staticmethod
    def _psd_for_T(T_expected, frequency, range_m, Omega):
        """PSD (W/Hz) que produz T_expected via T = S·λ²/(2 k Ω),
        com S = PSD/(4π r²)."""
        lam2 = (c / frequency) ** 2
        return T_expected * 4 * np.pi * range_m**2 * (2 * k * Omega) / lam2

    def test_temperature_conversion_valid(self):
        """Deve passar com valores físicos realistas."""
        frequency = 1.4e9  # Hz (L-band)
        range_m = 1e6  # 1000 km
        T_expected = 10  # K
        psd = self._psd_for_T(T_expected, frequency, range_m, _OMEGA_TEST)

        T = ScienceValidator.validate_temperature_conversion(
            psd, frequency, range_m, _OMEGA_TEST,
            expected_temp_range=(0.1, 1e6),
        )

        assert 9.5 <= T <= 10.5
        assert isinstance(T, (float, np.floating))

    def test_temperature_conversion_cold(self):
        """Deve validar temperatura fria (próxima a 0 K)."""
        frequency = 10e9  # Hz (X-band)
        range_m = 1e7  # 10000 km
        T_expected = 0.5  # K
        psd = self._psd_for_T(T_expected, frequency, range_m, _OMEGA_TEST)

        T = ScienceValidator.validate_temperature_conversion(
            psd, frequency, range_m, _OMEGA_TEST,
            expected_temp_range=(0.1, 1e6),
        )

        assert 0.4 <= T <= 0.6

    def test_temperature_conversion_hot(self):
        """Deve validar temperatura quente."""
        frequency = 1e9  # Hz
        range_m = 1000  # metros (perto)
        T_expected = 1000  # K
        psd = self._psd_for_T(T_expected, frequency, range_m, _OMEGA_TEST)

        T = ScienceValidator.validate_temperature_conversion(
            psd, frequency, range_m, _OMEGA_TEST,
            expected_temp_range=(1, 1e6),
        )

        assert 900 <= T <= 1100

    def test_temperature_conversion_unrealistic_too_cold(self):
        """Deve falhar com temperatura abaixo de limite."""
        frequency = 1.4e9
        range_m = 1e6
        T_cold = 0.01  # K
        psd_cold = self._psd_for_T(T_cold, frequency, range_m, _OMEGA_TEST)

        with pytest.raises(ValueError, match="Unrealistic temperature"):
            ScienceValidator.validate_temperature_conversion(
                psd_cold, frequency, range_m, _OMEGA_TEST,
                expected_temp_range=(0.1, 1e6),
            )

    def test_temperature_conversion_unrealistic_too_hot(self):
        """Deve falhar com temperatura acima de limite."""
        frequency = 1.4e9
        range_m = 1e6
        T_hot = 1e8  # K (acima do limite)
        psd_hot = self._psd_for_T(T_hot, frequency, range_m, _OMEGA_TEST)

        with pytest.raises(ValueError, match="Unrealistic temperature"):
            ScienceValidator.validate_temperature_conversion(
                psd_hot, frequency, range_m, _OMEGA_TEST,
                expected_temp_range=(1, 1e6),
            )

    def test_temperature_conversion_custom_range(self):
        """Deve validar com faixa customizada."""
        frequency = 1.4e9
        range_m = 1e6
        T_val = 50  # K
        psd = self._psd_for_T(T_val, frequency, range_m, _OMEGA_TEST)

        T = ScienceValidator.validate_temperature_conversion(
            psd, frequency, range_m, _OMEGA_TEST,
            expected_temp_range=(1, 1e8),
        )

        assert isinstance(T, (float, np.floating))
        assert 45 <= T <= 55

    def test_temperature_conversion_physical_consistency(self):
        """Deve validar consistência física com mudanças de parâmetros."""
        frequency = 1.4e9
        range_m = 1e6
        T_val = 10
        base_psd = self._psd_for_T(T_val, frequency, range_m, _OMEGA_TEST)

        T_base = ScienceValidator.validate_temperature_conversion(
            base_psd, frequency, range_m, _OMEGA_TEST,
            expected_temp_range=(0.1, 1e7),
        )

        # Aumentar PSD deve aumentar T
        T_high_psd = ScienceValidator.validate_temperature_conversion(
            base_psd * 10, frequency, range_m, _OMEGA_TEST,
            expected_temp_range=(0.1, 1e7),
        )
        assert T_high_psd > T_base

        # Aumentar frequência deve diminuir T (λ² no numerador)
        T_high_freq = ScienceValidator.validate_temperature_conversion(
            base_psd, frequency * 2, range_m, _OMEGA_TEST,
            expected_temp_range=(0.1, 1e7),
        )
        assert T_high_freq < T_base

        # Aumentar Ω deve diminuir T (T ∝ 1/Ω)
        T_wide_beam = ScienceValidator.validate_temperature_conversion(
            base_psd, frequency, range_m, _OMEGA_TEST * 4,
            expected_temp_range=(0.1, 1e7),
        )
        assert T_wide_beam < T_base


class TestScienceValidatorIntegration:
    """Testes de integração entre validadores."""

    def test_multiple_validations(self):
        """Deve executar múltiplas validações sem conflitos."""
        # PSD
        psd_data = xr.DataArray([1e-8, 2e-8], attrs={"units": "W/Hz"})
        ScienceValidator.validate_psd_units(psd_data)

        # Beam
        angles = np.linspace(-45, 45, 400)
        beam = _normalize_beam(np.exp(-0.5 * (angles / 10) ** 2), angles)
        Omega = ScienceValidator.validate_beam_normalized(beam, angles)

        # Temperature (com valores realistas)
        frequency = 1.4e9
        range_m = 1e6
        T_val = 10
        lam2 = (c / frequency) ** 2
        psd = T_val * 4 * np.pi * range_m**2 * (2 * k * Omega) / lam2

        T = ScienceValidator.validate_temperature_conversion(
            psd, frequency, range_m, Omega,
            expected_temp_range=(1, 1e6),
        )

        assert 9.5 <= T <= 10.5

    def test_all_methods_are_static(self):
        """Deve ser possível chamar métodos sem instância."""
        angles = np.linspace(-45, 45, 400)
        beam = _normalize_beam(np.exp(-0.5 * (angles / 10) ** 2), angles)

        integral = ScienceValidator.validate_beam_normalized(beam, angles)
        assert integral is not None
