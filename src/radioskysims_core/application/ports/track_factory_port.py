"""
Módulo: radioskysims_core/application/ports/track_factory_port.py

Descrição:
    Port (interface) para fábrica de tracks de satélites. Define o contrato
    mínimo necessário pela camada de application para construir datasets
    xarray de trajetórias de satélites.

Copyright BINGO Collaboration
Last modified: 2026-11-05
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import xarray as xr


class TrackFactoryPort(ABC):
    """
    Port que define como construir tracks de satélites.

    Uma implementação deve ser capaz de:
    - receber satélites para um intervalo de tempo
    - calcular posições (coordenadas xyz)
    - retornar um dataset xarray

    Esta port permite desacoplar a lógica de construção de tracks
    (Skyfield, computação) da lógica de negócio (application).
    """

    @abstractmethod
    def build_dataset(
        self,
        satellites: list[Any],
        times: Any,
    ) -> xr.Dataset:
        """
        Constrói um dataset de trajetórias para um bloco temporal.

        Args:
            satellites:
                Lista de objetos satélite do domínio (com TLE).
            times:
                Objeto de tempos (typ. Skyfield timescale).

        Returns:
            xarray.Dataset com posições dos satélites (lazy/dask).
        """
        ...

    @abstractmethod
    def build_full_tracks(
        self,
        satellites_dict: dict[Any, list[Any]],
    ) -> xr.Dataset:
        """
        Constrói o dataset completo de tracks para múltiplos blocos temporais.

        Args:
            satellites_dict:
                Mapeamento de tempos → lista de satélites.

        Returns:
            xarray.Dataset agregado com todos os tracks.
        """
        ...
