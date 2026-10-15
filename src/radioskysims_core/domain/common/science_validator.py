"""
Módulo: src/radioskysims/domain/common/science_validator.py

Descrição:
    Validador de correção física na simulação de radioastronomia.
    Implementa checagens de unidades, normalização e limites físicos.

Padrão DDD:
    Esta classe reside no domínio (Value Object) e implementa regras de negócio
    relacionadas a validação física. Não contém imports de infraestrutura,
    mantendo o domínio desacoplado de tecnologias específicas.
"""

from __future__ import annotations

import numpy as np
import xarray as xr
from scipy.constants import c, k

from radioskysims_core.domain.common.beam_geometry import solid_angle


class ScienceValidator:
    """
    Valida correção da física na simulação de radioastronomia.

    Implementa validações de:
    - Unidades de Density Spectral Power (PSD)
    - Normalização de padrão de radiação (beam)
    - Conversão PSD ↔ Temperatura brilho

    Métodos são estáticos (Value Object pattern).
    """

    @staticmethod
    def validate_psd_units(psd: xr.DataArray, expected_units: str = "W/Hz") -> None:
        """
        Valida que Power Spectral Density (PSD) está nas unidades corretas.

        Args:
            psd: DataArray do xarray com atributo 'units'.
            expected_units: Unidade esperada (default: "W/Hz").

        Raises:
            ValueError: Se unidades não correspondem às esperadas.

        Example:
            >>> data = xr.DataArray([1, 2, 3], attrs={"units": "W/Hz"})
            >>> ScienceValidator.validate_psd_units(data)  # OK

            >>> bad_data = xr.DataArray([1, 2, 3], attrs={"units": "V/Hz"})
            >>> ScienceValidator.validate_psd_units(bad_data)  # Raises ValueError
        """
        actual_units = psd.attrs.get("units", "unknown")
        if actual_units != expected_units:
            msg = f"PSD units: expected {expected_units}, got {actual_units}"
            raise ValueError(msg)

    @staticmethod
    def validate_beam_normalized(
        beam_amplitude: np.ndarray,
        angles: np.ndarray,
    ) -> float:
        """
        Valida que o padrão de radiação (beam) está normalizado.

        Critério: ∫B(θ) dΩ ≈ 1 (integral sobre ângulo sólido físico)

        Args:
            beam_amplitude: Array 1D com amplitude do feixe em função do ângulo.
            angles: Array 1D com ângulos em graus correspondentes ao beam.

        Returns:
            float: Valor da integral Ω = ∫ B_n dΩ (deve estar em [0.95, 1.05]).

        Raises:
            ValueError: Se integral está fora do intervalo [0.95, 1.05].

        Notes:
            - Assumindo simetria azimutal, Ω = 2π ∫₀^π B²(θ) sinθ dθ, com o
              padrão **dobrado por simetria** (média de B(+θ) e B(−θ)); não
              se usa a paridade do integrando ``B²(θ)·sinθ``.
            - Integral: ∑ B²(θ) · sinθ · dθ · 2π

        Example:
            >>> angles = np.linspace(0, 90, 100)
            >>> # Gaussian beam normalizado
            >>> beam = np.exp(-(angles / 30)**2)
            >>> integral = ScienceValidator.validate_beam_normalized(beam, angles)
            >>> print(f"Integral: {integral:.3f}")  # ~1.0
        """
        angles = np.asarray(angles, dtype=float)
        beam_amplitude = np.asarray(beam_amplitude, dtype=float)

        # Ω = 2π ∫₀^π B²(θ) sinθ dθ — padrão de potência dobrado por simetria.
        integral = solid_angle(beam_amplitude**2, angles)

        # Valida que está normalizado (tolerância de 5%)
        if not (0.95 <= integral <= 1.05):
            msg = f"Beam integral: {integral:.3f} (expected 1.0 ± 5%)"
            raise ValueError(msg)

        return float(integral)

    @staticmethod
    def validate_temperature_conversion(
        psd: float,
        frequency: float,
        range_m: float,
        Omega: float,
        expected_temp_range: tuple[float, float] = (1e-3, 1e6),
        n_pol: int = 1,
    ) -> float:
        """
        Valida conversão PSD → Temperatura de antena (radioastronomia padrão).

        Para uma fonte pontual não polarizada com recepção de 1 polarização:

            S_obs = PSD / (4π r²)          # diluição isotrópica (W/m²/Hz)
            T_A   = S_obs · λ² / (2 k_B Ω)  # λ = c/ν ; Ω = ∫ B_n dΩ

        Args:
            psd: Potência espectral total transmitida (W/Hz).
            frequency: Frequência (Hz).
            range_m: Distância (metros).
            Omega: Ângulo sólido do feixe (sr) — Ω = ∫ B_n dΩ.
            expected_temp_range: Faixa de temperatura esperada (K).
                                Default: (1e-3, 1e6) K.
            n_pol: Polarizações recebidas por canal (1 → fator 2 k_B;
                   2 → fator k_B).

        Returns:
            float: Temperatura de antena equivalente (K).

        Raises:
            ValueError: Se temperatura está fora da faixa esperada.

        Notes:
            - c: velocidade da luz (m/s); k: constante de Boltzmann (J/K).
            - Rayleigh-Jeans é válida para: hf << kT.

        Example:
            >>> psd = 1e-20  # W/Hz
            >>> freq = 1.4e9  # Hz (L-band)
            >>> range_m = 1e6  # 1000 km
            >>> Omega = 1e-3  # sr
            >>> T = ScienceValidator.validate_temperature_conversion(
            ...     psd, freq, range_m, Omega
            ... )
            >>> print(f"T = {T:.2e} K")
        """
        lam2 = (c / frequency) ** 2
        flux_at_observer = psd / (4 * np.pi * range_m**2)
        denom = 2 * k * Omega if n_pol == 1 else k * Omega
        T = flux_at_observer * lam2 / denom

        # Valida que está em faixa razoável
        if not (expected_temp_range[0] <= T <= expected_temp_range[1]):
            msg = f"Unrealistic temperature: {T:.2e} K (expected {expected_temp_range})"
            raise ValueError(msg)

        return float(T)
