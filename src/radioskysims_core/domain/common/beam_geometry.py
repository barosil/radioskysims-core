"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/domain/common/beam_geometry.py

Descrição:
    Geometria do feixe: dobra de um padrão simétrico e ângulo sólido Ω.

    O ângulo sólido do feixe é obtido **integrando o padrão** (potência)
    sobre o elemento sólido ``sinθ dθ dφ``, com simetria azimutal (fator 2π)
    e o padrão dobrado por **simetria** (média de B(+θ) e B(−θ)) — e não por
    paridade do integrando ``B(θ)·sinθ`` (que é ímpar e se anularia se
    integrado na esfera inteira).

Copyright BINGO Collaboration
Last modified: 2026-10-13
"""

from __future__ import annotations

import numpy as np


def fold_symmetric(
    values: np.ndarray,
    angles_deg: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Dobra um padrão simétrico (espelho em θ=0) para a metade θ ≥ 0.

    Usa a **simetria** do feixe: cada ângulo θ ≥ 0 recebe a média das amostras
    em +θ e −θ. Não recorre à paridade do integrando.

    Parameters
    ----------
    values : array
        Padrão (potência), na ordem de ``angles_deg``.
    angles_deg : array
        Ângulos em graus (podem cobrir o intervalo negativo).

    Returns
    -------
    tuple[ndarray, ndarray]
        ``(angles_deg >= 0 crescentes, valores dobrados)``.
    """
    ang = np.asarray(angles_deg, dtype=float)
    val = np.asarray(values, dtype=float)
    order = np.argsort(ang, kind="stable")
    ang, val = ang[order], val[order]
    mask_pos = ang >= 0.0
    pos_ang, pos_val = ang[mask_pos], val[mask_pos]
    neg_ang, neg_val = ang[~mask_pos], val[~mask_pos]
    if pos_ang.size == 0:
        return np.array([0.0]), np.array([0.0])
    if neg_ang.size < 2:
        return pos_ang, pos_val
    mirrored = np.interp(-pos_ang, neg_ang, neg_val)
    # θ=0 é auto-simétrico: o espelho é o próprio valor (evita o clamp do interp).
    zero = pos_ang == 0.0
    if np.any(zero):
        mirrored = np.where(zero, pos_val, mirrored)
    return pos_ang, 0.5 * (pos_val + mirrored)


def solid_angle(beam_power: np.ndarray, angles_deg: np.ndarray) -> float:
    r"""Ângulo sólido do feixe :math:`\Omega = 2\pi\int_0^\pi B_n(\theta)\sin\theta\,d\theta`.

    ``B_n`` é o padrão de **potência** já normalizado ao pico (0 dB). O padrão
    é dobrado por simetria antes da integração.
    """
    half_ang, half_pow = fold_symmetric(beam_power, angles_deg)
    th = np.deg2rad(half_ang)
    return float(np.sum(half_pow * np.sin(th) * np.gradient(th)) * 2.0 * np.pi)


def directivity(beam_power: np.ndarray, angles_deg: np.ndarray) -> float:
    r"""Diretividade :math:`D = 4\pi/\Omega` do padrão de potência."""
    p = np.asarray(beam_power, dtype=float)
    if p.size == 0:
        return float("nan")
    pmax = float(np.max(p))
    if pmax <= 0.0:
        return float("nan")
    omega = solid_angle(p / pmax, angles_deg)
    return float(4.0 * np.pi / omega) if omega > 0.0 else float("nan")


__all__ = ["directivity", "fold_symmetric", "solid_angle"]
