from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict


class SatelliteBlock(TypedDict):
    """
    Bloco de satélites associado a um intervalo temporal.

    Keys:
        timerange:
            Objeto representando o intervalo de tempo.
            Pode ser um TimeRange de domínio ou skyfield.Time.
        satellites:
            Lista de satélites de domínio associados ao intervalo.
    """

    timerange: Any
    satellites: list[Any]


SatelliteBlocks = dict[datetime, SatelliteBlock]
