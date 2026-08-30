"""\
Módulo: packages/radioskysims-core/src/radioskysims_core/config/tod_settings.py

Descrição:
    Schema tipado (pydantic) e validação leve para execuções de TOD
    (ticket TOD-001). Modela o arquivo mínimo de settings usado pelo pipeline
    (ver ``config/examples/tod_settings_example.toml``) e valida cenários
    essenciais com mensagens claras.

Copyright BINGO Collaboration
Last modified: 2026-08-30
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


class TimeRangeSettings(BaseModel):
    """Intervalo temporal da execução (entradas ISO 8601, cadência em s)."""

    start: str
    end: str
    cadence: float = Field(gt=0, description="Cadência em segundos.")


class FrequencyRangeSettings(BaseModel):
    """Faixa de frequência do TOD em MHz."""

    start_mhz: float = Field(gt=0)
    end_mhz: float = Field(gt=0)
    nchan: int = Field(gt=0)


class RadiotelescopeSettings(BaseModel):
    """Descrição mínima do radiotelescópio (inline)."""

    name: str
    latitude: float
    longitude: float
    altitude: float = 0.0


class SunSourceSettings(BaseModel):
    """Fonte local (Sol) na simulação."""

    enabled: bool = False


class SourcesSettings(BaseModel):
    """Seleção de fontes da simulação."""

    sun: SunSourceSettings = SunSourceSettings()


class OutputSettings(BaseModel):
    """Configuração de saída do TOD."""

    outdir: str
    format: Literal["netcdf", "zarr", "hdf5"] = "netcdf"
    filename_template: str = "tod_result_{timestamp}.nc"


class TodSettings(BaseModel):
    """Schema mínimo de settings para uma execução de TOD."""

    time_range: TimeRangeSettings
    frequency_range: FrequencyRangeSettings
    radiotelescope: RadiotelescopeSettings
    sources: SourcesSettings = SourcesSettings()
    output: OutputSettings


def load_tod_settings(path: str | Path) -> TodSettings:
    """Carrega e valida um arquivo TOML de settings de TOD.

    Args:
        path: caminho do arquivo TOML.

    Returns:
        TodSettings validado.

    Raises:
        FileNotFoundError: arquivo não encontrado.
        ValueError: conteúdo inválido (com mensagem clara).
    """
    p = Path(path)
    if not p.exists():
        msg = f"settings TOD não encontrado: {p}"
        raise FileNotFoundError(msg)
    with p.open("rb") as fh:
        data = tomllib.load(fh)
    return validate_settings(data)


def validate_settings(settings: dict[str, Any] | TodSettings) -> TodSettings:
    """Valida settings mínimos de TOD e retorna o modelo tipado.

    Aceita um ``dict`` (ex.: de ``tomllib``) ou um ``TodSettings``. Falha com
    ``ValueError`` de mensagem clara quando um cenário essencial é inválido.

    Args:
        settings: mapeamento ou modelo a validar.

    Returns:
        TodSettings validado.

    Raises:
        ValueError: se ``settings`` não for um mapeamento ou violar o schema.
    """
    if isinstance(settings, TodSettings):
        return settings
    if not isinstance(settings, dict):
        msg = "settings deve ser um mapeamento (dict) ou TodSettings"
        raise ValueError(msg)
    try:
        return TodSettings.model_validate(settings)
    except ValidationError as exc:
        parts = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
        msg = "settings TOD inválido: " + "; ".join(parts)
        raise ValueError(msg) from exc


__all__ = [
    "FrequencyRangeSettings",
    "OutputSettings",
    "RadiotelescopeSettings",
    "SourcesSettings",
    "SunSourceSettings",
    "TimeRangeSettings",
    "TodSettings",
    "load_tod_settings",
    "validate_settings",
]
