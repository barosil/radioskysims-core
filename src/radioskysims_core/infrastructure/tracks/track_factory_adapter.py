from __future__ import annotations

import importlib
from typing import Any

import dask
import numpy as np
import xarray as xr
from dask import array as da

from radioskysims_core.application.ports.track_factory_port import (
    TrackFactoryPort,
)
from radioskysims_core.domain.common.logging import get_domain_logger

logger = get_domain_logger(__name__)

# Config padrão para skyfield — pode ser sobrescrita via construtor
_DEFAULT_SKYFIELD_FOLDER = "data/aux/skyfield"

# -------------------------------------------------
# Lazy imports
# -------------------------------------------------
_lazy_cache = {}


def _lazy_skyfield():
    """
    Lazily load the ``skyfield.api`` module.

    Returns:
        skyfield.api module.
    """
    if "skyfield" not in _lazy_cache:
        _lazy_cache["skyfield"] = importlib.import_module("skyfield.api")
    return _lazy_cache["skyfield"]


def _lazy_SatID():
    """
    Lazily load the SatID model.

    Returns:
        SatID class.
    """
    if "SatID" not in _lazy_cache:
        _lazy_cache["SatID"] = importlib.import_module(
            "radioskysims_sources.infrastructure.db.satellite.models"
        ).SatID
    return _lazy_cache["SatID"]


def _lazy_Tracks():
    """
    Lazily load the Tracks model.

    Returns:
        Tracks class.
    """
    if "Tracks" not in _lazy_cache:
        _lazy_cache["Tracks"] = importlib.import_module(".models", __package__).Tracks
    return _lazy_cache["Tracks"]


class TrackFactory(TrackFactoryPort):
    """
    Adapter (infrastructure implementation) responsável por construir tracks de satélites.

    A factory:
    - recebe blocos de satélites por intervalo temporal
    - calcula posições com Skyfield
    - constrói um Dataset xarray lazily com Dask
    """

    def __init__(
        self,
        satellites_dict: dict | None = None,
        skyfield_data_path: str | None = None,
    ) -> None:
        """
        Initialize the TrackFactory.

        Args:
            satellites_dict:
                Mapping between datetimes and satellite blocks (optional).
            skyfield_data_path:
                Caminho para os dados skyfield (opcional).
                Se não fornecido, usa o padrão.
        """
        self.satellites_dict = satellites_dict or {}
        self._sat_cache = {}
        self.satellite_blocks = None
        self.earthsats = None
        self.skyfield = SkyfieldAdapter(skyfield_data_path=skyfield_data_path)
        self._MAX_CHUNK_SIZE_BYTES = 100 * 1024 * 1024

    @staticmethod
    def _compute_xyz_km_tle(tle1: str, tle2: str, name: str, tt_jd: np.ndarray):
        """
        Compute satellite positions (km) for given TT Julian dates.

        Note: We reconstruct the Skyfield EarthSatellite inside the task to keep the
        dask graph pickle-safe (Skyfield's Satrec is not picklable).
        """
        sf = _lazy_skyfield()
        ts = sf.load.timescale()
        times = ts.tt_jd(tt_jd)
        sat = sf.EarthSatellite(tle1, tle2, name, ts)
        return sat.at(times).xyz.km.T

    def _build_block_dataset(self, satellites: list[Any], times: Any) -> xr.Dataset:
        """
        Build an xarray Dataset for a single time block.

        Args:
            satellites:
                List of domain satellite objects (with TLE).
            times:
                Skyfield time array.

        Returns:
            xarray.Dataset with lazy position computation.
        """
        delayed_arrays = []
        n_times = len(times)
        tt = np.asarray(times.tt, dtype=float)

        for sat in satellites:
            tle1 = sat.element.tle_line1
            tle2 = sat.element.tle_line2
            name = str(getattr(sat, "name", "") or getattr(sat, "norad_id", "sat"))
            delayed_xyz = dask.delayed(self._compute_xyz_km_tle)(tle1, tle2, name, tt)
            arr = da.from_delayed(delayed_xyz, shape=(n_times, 3), dtype=np.float64)
            delayed_arrays.append(arr)

        block = da.stack(delayed_arrays, axis=0)

        return xr.Dataset(
            data_vars={"positions": (["satellite", "time", "xyz"], block)},
            coords={
                "satellite": np.arange(len(satellites)),
                "time": times.tt,
                "xyz": ["x", "y", "z"],
            },
        )

    def _build_track_ds(self) -> xr.Dataset:
        """
        Build the full tracks dataset by concatenating all time blocks.

        Returns:
            xarray.Dataset with satellite tracks.
        """
        try:
            logger.info(
                "track_build_start",
                num_blocks=len(self.satellite_blocks or {}),
            )

            datasets: list[xr.Dataset] = []

            for block_idx, (_, block) in enumerate(self.satellite_blocks.items()):
                timerange = block["timerange"].to_skyfield()
                satellites = block["satellites"]

                logger.info(
                    "track_block_compute",
                    block_index=block_idx,
                    num_satellites=len(satellites),
                )

                times = self.skyfield.times(timerange)
                ds = self._build_block_dataset(satellites, times)

                ds = ds.assign_coords(
                    satellite=("satellite", [s.norad_id for s in satellites]),
                    names=("satellite", [s.name for s in satellites]),
                    constellation=(
                        "satellite",
                        [s.constellation for s in satellites],
                    ),
                    tle_line1=(
                        "satellite",
                        [s.element.tle_line1 for s in satellites],
                    ),
                    tle_line2=(
                        "satellite",
                        [s.element.tle_line2 for s in satellites],
                    ),
                )

                datasets.append(ds)
                logger.info("track_block_success", block_index=block_idx)

            out = xr.concat(datasets, dim="time")
            out.attrs["units"] = "km"

            logger.info(
                "track_build_success",
                num_satellites=len(out.satellite),
                num_times=len(out.time),
            )
            return out
        except Exception as e:
            logger.exception("track_build_failed", error=str(e))
            raise

    def build(self, satellites_block=None, scheduler: str | None = None):
        """
        Build satellite tracks.

        Args:
            scheduler:
                Optional Dask scheduler name.

        Returns:
            Tracks object built from the xarray Dataset.
        """
        try:
            logger.info(
                "track_build_start_full",
                num_blocks=len(satellites_block) if satellites_block else 0,
            )

            self.satellite_blocks = satellites_block
            if scheduler:
                dask.config.set(scheduler=scheduler)
                logger.info("track_scheduler_set", scheduler=scheduler)

            ds = self._build_track_ds()
            Tracks = _lazy_Tracks()
            result = Tracks.from_xr(ds)

            logger.info("track_build_complete", num_satellites=len(result.satellite_names))
            return result
        except Exception as e:
            logger.exception("track_build_complete_failed", error=str(e))
            raise

    # ========== TrackFactoryPort implementation ==========

    def build_dataset(
        self,
        satellites: list[Any],
        times: Any,
    ) -> xr.Dataset:
        """
        Implementação de TrackFactoryPort.build_dataset().

        Constrói um dataset de trajetórias para um bloco temporal.
        """
        return self._build_block_dataset(satellites, times)

    def build_full_tracks(
        self,
        satellites_dict: dict[Any, list[Any]],
    ) -> xr.Dataset:
        """
        Implementação de TrackFactoryPort.build_full_tracks().

        Constrói o dataset completo de tracks para múltiplos blocos temporais.
        """
        self.satellite_blocks = satellites_dict
        return self._build_track_ds()


class SkyfieldAdapter:
    """
    Adaptador fino para o Skyfield.

    Responsável por:
    - carregar Loader e Timescale sob demanda
    - converter intervalos de tempo em objetos Skyfield
    - cachear EarthSatellite para performance
    """

    def __init__(self, skyfield_data_path: str | None = None) -> None:
        self._loader = None
        self._ts = None
        self._sat_cache: dict[int, Any] = {}
        self._skyfield_data_path = skyfield_data_path

    @property
    def loader(self):
        """
        Skyfield Loader lazily initialized.

        Returns:
            skyfield.api.Loader
        """
        if self._loader is None:
            sf = _lazy_skyfield()
            if self._skyfield_data_path:
                loader_path = self._skyfield_data_path
            else:
                loader_path = _DEFAULT_SKYFIELD_FOLDER
            self._loader = sf.Loader(loader_path)
        return self._loader

    @property
    def ts(self):
        """
        Skyfield Timescale lazily initialized.

        Returns:
            skyfield.api.Timescale
        """
        if self._ts is None:
            self._ts = self.loader.timescale()
        return self._ts

    def times(self, timerange: Any):
        """
        Convert a time range into a Skyfield-compatible time object.

        Args:
            timerange:
                Object with a ``to_skyfield()`` method or already a Skyfield time.

        Returns:
            Skyfield time object.
        """
        return timerange.to_skyfield() if hasattr(timerange, "to_skyfield") else timerange

    def earthsatellite(self, satellite: Any):
        """
        Build or retrieve a cached EarthSatellite.

        Args:
            satellite:
                Domain satellite with TLE and metadata.

        Returns:
            skyfield.api.EarthSatellite
        """
        sf = _lazy_skyfield()
        key = int(getattr(satellite, "norad_id", id(satellite)))

        if key not in self._sat_cache:
            self._sat_cache[key] = sf.EarthSatellite(
                satellite.element.tle_line1,
                satellite.element.tle_line2,
                str(satellite.name),
                self.ts,
            )

        return self._sat_cache[key]
