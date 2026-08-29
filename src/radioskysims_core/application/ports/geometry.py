"""
Módulo: src/radioskysims/application/ports/geometry.py

Ports (Interfaces) da camada de Application para operacoes de Geometria.

Define o contrato entre o domínio e as implementações concretas de
cálculo geométrico (Skyfield, etc).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import xarray as xr


class GeometryProviderPort(ABC):
    """
    Port para cálculo de geometria observacional.

    Define o contrato para implementações que calculam parâmetros
    geométricos entre um observador fixo e trajetórias de satélites,
    sem comprometer a implementação concreta (Skyfield, etc).
    """

    @abstractmethod
    def compute(
        self,
        tracks: Any,
        observer: Any,
        sat_block: Any | None = None,
    ) -> xr.Dataset:
        """
        Calcula parâmetros geométricos observacionais.

        Retorna um Dataset com dimensão 'time' contendo as variáveis:
        - theta(time): Ângulo entre satélite e feixe (radianos)
        - range(time): Distância satélite-observador (metros)
        - az(time): Azimute (radianos, opcional)
        - el(time): Elevação (radianos, opcional)

        Args:
            tracks: Dataset com trajetórias dos satélites (time, satellite).
            observer: Observador/estação terrestre com atributos lat, lon, alt.
            sat_block: Bloco de satélites específicos (opcional).

        Returns:
            xr.Dataset: Dataset com dimensão 'time' e variáveis geométricas.

        Raises:
            ValueError: Se inputs estão em formato inválido.
            RuntimeError: Se cálculo não puder ser realizado.
        """
        raise NotImplementedError

    @abstractmethod
    def calculate_position(
        self,
        satellite: Any,
        time: Any,
        observer_lat: float,
        observer_lon: float,
    ) -> tuple[Any, Any, Any]:
        """
        Calcula posição (theta, phi, range) de um satélite.

        Args:
            satellite: Objeto satélite da infraestrutura.
            time: Timestep (pode ser Skyfield Time, numpy array, etc).
            observer_lat: Latitude do observador (graus).
            observer_lon: Longitude do observador (graus).

        Returns:
            tuple: (theta, phi, range) onde:
                - theta: Ângulo zenital (radianos)
                - phi: Azimute (radianos)
                - range: Distância (metros)

        Raises:
            ValueError: Se parâmetros inválidos.
        """
        raise NotImplementedError

    @abstractmethod
    def calculate_range(
        self,
        satellite: Any,
        time: Any,
        observer_lat: float | None = None,
        observer_lon: float | None = None,
    ) -> Any:
        """
        Calcula distância satélite-observador.

        Args:
            satellite: Objeto satélite da infraestrutura.
            time: Timestep.
            observer_lat: Latitude do observador (opcional).
            observer_lon: Longitude do observador (opcional).

        Returns:
            Distance: Distância em metros (ou array de distâncias).

        Raises:
            ValueError: Se parâmetros inválidos.
        """
        raise NotImplementedError
