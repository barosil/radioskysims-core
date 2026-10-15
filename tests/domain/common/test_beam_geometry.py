"""\
Módulo: tests/domain/common/test_beam_geometry.py

Descrição:
    Testes da geometria do feixe: dobra por simetria e ângulo sólido Ω.

Copyright BINGO Collaboration
Last modified: 2026-10-13
"""

from __future__ import annotations

import numpy as np
import pytest
from radioskysims_core.domain.common.beam_geometry import (
    directivity,
    fold_symmetric,
    solid_angle,
)


def test_fold_symmetric_averages_both_halves():
    angles = np.array([-10.0, -5.0, 0.0, 5.0, 10.0])
    values = np.array([0.1, 0.2, 1.0, 0.3, 0.4])

    pos_ang, folded = fold_symmetric(values, angles)

    np.testing.assert_allclose(pos_ang, [0.0, 5.0, 10.0])
    # θ=±5 → média (0.3, 0.2)=0.25 ; θ=±10 → média (0.4, 0.1)=0.25
    np.testing.assert_allclose(folded, [1.0, 0.25, 0.25])


def test_fold_symmetric_handles_one_sided_pattern():
    angles = np.array([0.0, 5.0, 10.0])
    values = np.array([1.0, 0.5, 0.1])

    pos_ang, folded = fold_symmetric(values, angles)

    np.testing.assert_allclose(pos_ang, angles)
    np.testing.assert_allclose(folded, values)


def test_solid_angle_matches_gaussian_estimate():
    ang = np.arange(-90.0, 90.0 + 1e-9, 0.05)
    sigma_deg = 8.0
    amp = np.exp(-0.5 * (ang / sigma_deg) ** 2)

    omega = solid_angle(amp, ang)

    fwhm_rad = np.deg2rad(2.0 * np.sqrt(2.0 * np.log(2.0)) * sigma_deg)
    omega_gauss = (np.pi / (4.0 * np.log(2.0))) * fwhm_rad**2
    assert omega == pytest.approx(omega_gauss, rel=1e-2)
    assert directivity(amp, ang) == pytest.approx(4.0 * np.pi / omega, rel=1e-9)


def test_solid_angle_is_grid_independent_between_frequencies():
    ang = np.arange(-90.0, 90.0 + 1e-9, 0.1)
    narrow = np.exp(-0.5 * (ang / 5.0) ** 2)
    wide = np.exp(-0.5 * (ang / 12.0) ** 2)
    assert solid_angle(narrow, ang) < solid_angle(wide, ang)
