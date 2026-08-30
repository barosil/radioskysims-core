"""Testes do schema de settings de TOD (radioskysims_core.config.tod_settings)."""

from __future__ import annotations

import pytest
from radioskysims_core.config.tod_settings import (
    TodSettings,
    load_tod_settings,
    validate_settings,
)

VALID = {
    "time_range": {
        "start": "2026-08-01T00:00:00Z",
        "end": "2026-08-01T00:10:00Z",
        "cadence": 1.0,
    },
    "frequency_range": {"start_mhz": 980.0, "end_mhz": 1260.0, "nchan": 4},
    "radiotelescope": {
        "name": "example_rt",
        "latitude": -7.0,
        "longitude": -38.0,
        "altitude": 100.0,
    },
    "sources": {"sun": {"enabled": True}},
    "output": {"outdir": "data/TOD/", "format": "netcdf"},
}


def test_validate_valid_dict() -> None:
    model = validate_settings(VALID)
    assert isinstance(model, TodSettings)
    assert model.time_range.cadence == 1.0
    assert model.sources.sun.enabled is True
    assert model.output.format == "netcdf"


def test_validate_accepts_model() -> None:
    model = validate_settings(VALID)
    assert validate_settings(model) is model


def test_validate_defaults() -> None:
    minimal = {
        "time_range": {
            "start": "2026-08-01T00:00:00Z",
            "end": "2026-08-01T00:10:00Z",
            "cadence": 5,
        },
        "frequency_range": {"start_mhz": 1000.0, "end_mhz": 1250.0, "nchan": 8},
        "radiotelescope": {"name": "rt", "latitude": 0.0, "longitude": 0.0},
        "output": {"outdir": "data/TOD/"},
    }
    model = validate_settings(minimal)
    assert model.output.filename_template == "tod_result_{timestamp}.nc"
    assert model.sources.sun.enabled is False


def test_validate_missing_time_range_raises() -> None:
    bad = dict(VALID)
    bad.pop("time_range")
    with pytest.raises(ValueError, match="time_range"):
        validate_settings(bad)


def test_validate_cadence_invalid_raises() -> None:
    bad = dict(VALID)
    bad["time_range"] = {**bad["time_range"], "cadence": -1}
    with pytest.raises(ValueError):
        validate_settings(bad)


def test_validate_invalid_format_raises() -> None:
    bad = dict(VALID)
    bad["output"] = {**bad["output"], "format": "fits"}
    with pytest.raises(ValueError, match="format"):
        validate_settings(bad)


def test_validate_non_mapping_raises() -> None:
    with pytest.raises(ValueError, match="mapeamento"):
        validate_settings("not-a-dict")  # type: ignore[arg-type]


def test_load_tod_settings_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_tod_settings("nao-existe-settings.toml")


def test_load_tod_settings_example(tmp_path) -> None:
    p = tmp_path / "settings.toml"
    p.write_text(
        "[time_range]\n"
        'start = "2026-08-01T00:00:00Z"\n'
        'end = "2026-08-01T00:10:00Z"\n'
        "cadence = 1.0\n"
        "[frequency_range]\n"
        "start_mhz = 980.0\n"
        "end_mhz = 1260.0\n"
        "nchan = 4\n"
        "[radiotelescope]\n"
        'name = "example_rt"\n'
        "latitude = -7.0\n"
        "longitude = -38.0\n"
        "altitude = 100.0\n"
        "[sources.sun]\n"
        "enabled = true\n"
        "[output]\n"
        'outdir = "data/TOD/"\n'
        'format = "netcdf"\n'
    )
    model = load_tod_settings(p)
    assert model.radiotelescope.name == "example_rt"
    assert model.frequency_range.nchan == 4
