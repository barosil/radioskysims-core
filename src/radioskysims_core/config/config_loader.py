from __future__ import annotations

import logging
import re
import tomllib
from importlib.resources import files
from pathlib import Path
from typing import Any

import astropy.units as u
from astropy.time import Time

from radioskysims_core.domain.common import FrequencyRange, Observer, TimeRange
from radioskysims_core.paths import get_project_root

logger = logging.getLogger(__name__)


# ── Arquivo de settings ativo (suporte a settings nomeados) ──────────
# Permite carregar perfis alternativos como ``settings_planning.toml`` sem
# renomear/editar o ``settings.toml`` padrão. Definido via
# :func:`set_settings_file` (ou propagado por ``settings_file`` nos
# construtores de alto nível). ``None`` = usa o ``settings.toml`` padrão.
class _SettingsState:
    """Estado do arquivo de settings ativo (evita ``global``)."""

    def __init__(self) -> None:
        self.active: Path | None = None


_SETTINGS_STATE = _SettingsState()


def project_root() -> Path:
    """Diretório raiz do projeto (mesma pasta do ``pyproject.toml``)."""

    return get_project_root()


def resolve_settings_path(settings_file: str | Path | None = None) -> Path:
    """Resolve o caminho do arquivo de settings a usar.

    A ordem de busca é:

    1. ``settings_file`` explícito (resolvido em relação à raiz do projeto);
    2. arquivo ativo definido via :func:`set_settings_file`;
    3. ``settings.toml`` na raiz do projeto (mesma pasta do ``pyproject.toml``);
    4. ``settings.toml`` empacotado em ``radioskysims_core.config``
       (compatibilidade retroativa).
    """
    if settings_file is not None:
        path = Path(settings_file)
        if not path.is_absolute():
            path = project_root() / path
        if not path.exists():
            msg = f"settings: arquivo não encontrado: {path}"
            raise FileNotFoundError(msg)
        return path

    if _SETTINGS_STATE.active is not None:
        if not _SETTINGS_STATE.active.exists():
            msg = f"settings: arquivo ativo não encontrado: {_SETTINGS_STATE.active}"
            raise FileNotFoundError(msg)
        return _SETTINGS_STATE.active

    root_settings = project_root() / "settings.toml"
    if root_settings.exists():
        return root_settings
    # compatibilidade: usa o settings.toml dentro do pacote
    return Path(str(files("radioskysims_core.config") / "settings.toml"))


def set_settings_file(filename: str | Path | None) -> Path | None:
    """Define o arquivo de settings ativo para as próximas leituras.

    Ex.: ``set_settings_file("settings_planning.toml")`` faz com que
    ``load_config``, ``build_radiotelescope_from_settings`` e o
    ``SimOrchestrator`` usem esse arquivo. Passe ``None`` para voltar ao
    ``settings.toml`` padrão.

    Returns:
        Caminho absoluto resolvido, ou ``None`` ao resetar para o padrão.
    """
    if filename is None:
        _SETTINGS_STATE.active = None
        return None
    path = Path(filename)
    if not path.is_absolute():
        path = project_root() / path
    _SETTINGS_STATE.active = path
    return path


def load_config(
    key: str | None = None,
    *,
    settings_file: str | Path | None = None,
) -> dict[str, Any]:
    """

    Carrega as configurações do arquivo de settings.

    A ordem de busca é:

    1. arquivo informado em ``settings_file`` (ex.: ``settings_planning.toml``);
    2. arquivo ativo definido via :func:`set_settings_file`;
    3. ``settings.toml`` na raiz do projeto (mesma pasta do ``pyproject.toml``);
    4. ``settings.toml`` empacotado em ``radioskysims_core.config``
       (compatibilidade retroativa).
    """
    config_path = resolve_settings_path(settings_file)

    # Abrimos o arquivo no modo binário ('rb') e carregamos o conteúdo
    with config_path.open("rb") as f:
        config: dict[str, Any] = tomllib.load(f)
    if key:
        sections = key.split(".")
        current: dict[str, Any] | None = config
        for section in sections:
            if not isinstance(current, dict):
                current = {}
                break
            current = current.get(section, {})
        config = current if isinstance(current, dict) else {}
    if key == "paths":
        config = {**config, "root_folder": str(get_project_root())}
    return config


# Padrão de corte de fluxo no catálogo de rádio: "flux > X" ou "S > X" (Jy).
_RADIO_FLUX_RE = re.compile(
    r"(?:flux|S)\s*(>=|>)\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)


def radio_min_flux_jy(default: float = 0.1) -> float:
    """Corte de fluxo mínimo (Jy) para o catálogo de fontes de rádio.

    Lê a seção ``[radiosources]`` do ``settings.toml`` e extrai o limiar da
    ``query_str`` — ex.: ``"SELECT * FROM radiosources WHERE flux > .1"``
    resulta em ``0.1`` Jy. Esse é o ÚNICO critério de fluxo usado na
    consulta ao catálogo (nenhum valor é fixado em código).

    Args:
        default: Valor usado quando não há critério explícito no settings.

    Returns:
        Fluxo mínimo em Jy.
    """
    cfg = load_config("radiosources")
    query = str(cfg.get("query_str", ""))
    match = _RADIO_FLUX_RE.search(query)
    if match is not None:
        try:
            return float(match.group(2))
        except ValueError:
            pass
    return default


def _build_time_range_from_config(
    tr_cfg: list[Any] | tuple[Any, ...] | None,
    *,
    default: tuple[int, int, int] = (0, 0, 60),
) -> TimeRange:
    tr: list[Any] | tuple[Any, ...]
    if tr_cfg is None:
        tr = list(default)
    else:
        tr = tr_cfg
    if len(tr) != 3:
        msg = "settings.toml: time_range must be a 3-item list"
        raise ValueError(msg)

    t0, t1, dt = tr
    if isinstance(t0, (int, float)) and isinstance(t1, (int, float)):
        now = Time.now()
        start = now + t0 * u.s
        end = now + t1 * u.s
        return TimeRange.from_astropy(start, end, dt, unit=u.s)
    return TimeRange.from_iso(str(t0), str(t1), dt, unit=u.s)


def build_observer_from_settings(
    section: str = "radiotelescopes.default",
    *,
    location_order: str | None = None,
) -> Observer:
    """
    Build an Observer from settings.toml.

    Expected keys in the section:
        - lat: latitude (degrees)
        - lon: longitude (degrees)
        - height: meters (optional)
        - time_range: [start_s, end_s, step_s] offsets from now OR ISO strings
        - location_order: "lonlat" or "latlon" (optional, legacy)
    """
    cfg = load_config(section)

    if "observer" in cfg:
        cfg = cfg.get("observer", {})
    elif "observatory" in cfg:
        cfg = cfg.get("observatory", {})

    if "lat" in cfg and "lon" in cfg:
        lat = cfg.get("lat", 0.0)
        lon = cfg.get("lon", 0.0)
        height = cfg.get("height", 0.0)
    else:
        location = cfg.get("location", [0.0, 0.0])
        if not isinstance(location, (list, tuple)) or len(location) != 2:
            msg = "settings.toml: location must be a 2-item list"
            raise ValueError(msg)

        order = location_order or cfg.get("location_order", "lonlat")
        if order not in {"lonlat", "latlon"}:
            msg = "location_order must be 'lonlat' or 'latlon'"
            raise ValueError(msg)

        if order == "latlon":
            lat, lon = location
        else:
            lon, lat = location

        height = cfg.get("height", 0.0)

    tr_cfg = cfg.get("time_range")
    if tr_cfg is None:
        tr_cfg = load_config("simulations").get("time_range", [0, 0, 60])
    timeframe = _build_time_range_from_config(tr_cfg)

    return Observer(lat=lat, lon=lon, height=height, timeframe=timeframe)


def _build_frequency_range_from_config(
    fr_cfg: list[Any] | tuple[Any, ...] | str | None,
) -> FrequencyRange | None:
    if fr_cfg is None:
        return None
    if isinstance(fr_cfg, (list, tuple)) and len(fr_cfg) >= 2:
        resolution = fr_cfg[2] if len(fr_cfg) > 2 else None
        return FrequencyRange.from_floats(fr_cfg[0], fr_cfg[1], resolution, unit=u.MHz)
    if isinstance(fr_cfg, str):
        return FrequencyRange.from_string(fr_cfg, unit=u.MHz)
    return None


def build_radiotelescope_from_settings(
    name: str = "default",
    *,
    settings_file: str | Path | None = None,
) -> Any:
    # Imports lazy: os tipos de radiotelescópio pertencem ao pacote
    # ``radioskysims-radiotelescope`` (Fase 4). O núcleo permanece importável
    # sem radiotelescope; a função é específica de radiotelescópio.
    from radioskysims_radiotelescope.domain.radiotelescope.antenna.models import (
        Antenna,
        BeamSpec,
        Pointing,
    )
    from radioskysims_radiotelescope.domain.radiotelescope.backend.spectrometer.models import (
        SpectrometerBackend,
    )
    from radioskysims_radiotelescope.domain.radiotelescope.specs import RadiotelescopeSpec

    if settings_file is not None:
        # Propaga o arquivo ativo para todas as leituras subsequentes
        # (load_config, radio_min_flux_jy, config_loader do contexto, etc.).
        set_settings_file(settings_file)
    cfg = load_config(f"radiotelescopes.{name}")
    if not cfg:
        msg = f"settings.toml: radiotelescopes.{name} not found"
        raise ValueError(msg)

    observer = build_observer_from_settings(f"radiotelescopes.{name}")

    # Lê antenas: suporta tanto lista ([[antennas]]) quanto tabela única ([antenna])
    antennas_cfg_list = cfg.get("antennas")
    if antennas_cfg_list is None:
        # Fallback: tabela única [antenna]
        single = cfg.get("antenna")
        antennas_cfg_list = [single] if single else []

    built_antennas: list[Antenna] = []
    for ant_cfg in antennas_cfg_list:
        if not isinstance(ant_cfg, dict):
            continue
        horn_cfg = ant_cfg.get("horn", {})
        freq_cfg = ant_cfg.get("frequency_range") or horn_cfg.get("frequency", {}).get(
            "frequency_range"
        )
        antenna_fr = _build_frequency_range_from_config(freq_cfg)

        beam_cfg = ant_cfg.get("beam", {}) or horn_cfg.get("beam", {})
        pointing_cfg = ant_cfg.get("pointing", {})
        beam = BeamSpec(
            name=beam_cfg.get("name"),
            polarizations=beam_cfg.get("polarizations", []),
            beam_pattern_file=beam_cfg.get("pattern_file") or beam_cfg.get("beam_pattern_file"),
            frequency_range=antenna_fr,
            profile=beam_cfg.get("profile"),
            beam_width_deg=beam_cfg.get("beam_width_deg") or beam_cfg.get("sigma"),
        )

        # Backend associado a esta antena
        backend_cfg = ant_cfg.get("backend", {})
        if "spectrometer" in backend_cfg:
            backend_cfg = backend_cfg.get("spectrometer", {})
        backend_fr = _build_frequency_range_from_config(backend_cfg.get("frequency_range"))
        if antenna_fr is None and backend_fr is not None:
            antenna_fr = backend_fr
        backend = SpectrometerBackend(
            name=backend_cfg.get("name"),
            bandwidth_mhz=backend_cfg.get("bandwidth_MHz") or backend_cfg.get("bandwidth_mhz"),
            sampling_rate_mhz=backend_cfg.get("sampling_rate_MHz")
            or backend_cfg.get("sampling_rate_mhz"),
            integration_time_s=backend_cfg.get("integration_time_s"),
            num_channels=backend_cfg.get("num_channels"),
            system_temperature_k=backend_cfg.get("T_sys_K")
            or backend_cfg.get("system_temperature_k"),
            frequency_range=backend_fr,
        )

        antenna_obj = Antenna(
            name=ant_cfg.get("name") or horn_cfg.get("name", "horn"),
            effective_area_m2=(
                ant_cfg.get("effective_area_m2") or horn_cfg.get("effective_area_m2")
            ),
            frequency_range=antenna_fr,
            pointing=Pointing(
                mode=pointing_cfg.get("mode", "transit"),
                alt_deg=pointing_cfg.get("alt_deg", 90.0),
                az_deg=pointing_cfg.get("az_deg", 0.0),
                params=pointing_cfg.get("params", {}),
            ),
            beam=beam,
            backend=backend,
        )
        built_antennas.append(antenna_obj)

    return RadiotelescopeSpec(
        name=cfg.get("name", f"radiotelescope:{name}"),
        observer=observer,
        antennas=built_antennas,
    )


# Exemplo de uso
if __name__ == "__main__":
    config = load_config()
    logger.info("Configurações carregadas com sucesso:")
    logger.info(config)
    # Você pode acessar as variáveis como em um dicionário
    # Ex: print(config['database']['host'])
