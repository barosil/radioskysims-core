"""
Módulo: src/radioskysims/domain/geometry/pointing.py

Descrição:
    Função para calcular a track temporal do pointing de uma antena
    com montagem alt-az fixa. Usa Skyfield para converter o pointing
    fixo em RA/Dec aparente ao longo do tempo, considerando a rotação
    da Terra e a localização do observador.

    Uso típico:
        pointing_track = compute_pointing_track(
            observer=observer,
            time_grid=time_grid,       # datetime64[ns]
            alt_deg=67.0,
            az_deg=0.0,
        )
        # Retorna Dataset com ra (deg) e dec (deg), dim (time,)

Copyright BINGO Collaboration
Last modified: 2026-07-28
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import xarray as xr
from astropy.time import Time as AstroTime
from skyfield.api import load as skyfield_load

from radioskysims_core.skyfield_loader import load_ephemeris

if TYPE_CHECKING:
    from radioskysims_core.domain.common import Observer


def compute_pointing_track(
    observer: Observer,
    time_grid: np.ndarray,
    *,
    alt_deg: float,
    az_deg: float,
) -> xr.Dataset:
    """Calcula a track de pointing (RA/Dec aparente) no tempo.

    Para uma antena com montagem alt-az fixa, a posição aparente
    no céu varia em RA/Dec ao longo do tempo devido à rotação
    da Terra. Esta função calcula essa variação usando Skyfield::

        apparent = (earth + obs_loc).at(t).from_altaz(
            alt_degrees=alt_deg, az_degrees=az_deg
        )

    Parameters
    ----------
    observer : Observer
        Observador terrestre (lat, lon, altura).
    time_grid : np.ndarray
        Grade temporal da simulação em datetime64[ns].
    alt_deg : float
        Altitude fixa da antena (graus).
    az_deg : float
        Azimute fixo da antena (graus).

    Returns
    -------
    xr.Dataset
        Dataset com variáveis ``ra`` (deg) e ``dec`` (deg),
        dimensão ``(time,)``.
    """
    eph = load_ephemeris()
    earth = eph["earth"]

    # Obtém localização wgs84 do observador via Observer.to_skyfield()
    obs_loc, _ = observer.to_skyfield()

    # Converte time_grid datetime64[ns] para TT Julian dates (Skyfield)
    astro_times = AstroTime(time_grid.astype("datetime64[ns]"), format="datetime64")
    tt_jd = np.asarray(astro_times.tt.jd, dtype=float)

    sf_ts = skyfield_load.timescale()
    skyfield_times = sf_ts.tt_jd(tt_jd)

    # Calcula posição aparente do pointing fixo em cada instante
    apparent = (
        (earth + obs_loc)
        .at(skyfield_times)
        .from_altaz(
            alt_degrees=alt_deg,
            az_degrees=az_deg,
        )
    )

    ra, dec, _ = apparent.radec()

    ra_deg = np.asarray(ra.degrees, dtype=float)
    dec_deg = np.asarray(dec.degrees, dtype=float)

    ds = xr.Dataset(
        data_vars={
            "ra": ("time", ra_deg, {"units": "deg", "description": "Right ascension (apparent)"}),
            "dec": (
                "time",
                dec_deg,
                {"units": "deg", "description": "Declination (apparent)"},
            ),
            "alt_deg": ("time", np.full_like(ra_deg, alt_deg), {"description": "Fixed altitude"}),
            "az_deg": ("time", np.full_like(ra_deg, az_deg), {"description": "Fixed azimuth"}),
        },
        coords={"time": time_grid},
        attrs={
            "provider": "skyfield",
            "pointing_alt_deg": alt_deg,
            "pointing_az_deg": az_deg,
            "observer_lat_deg": float(observer.lat.to_value("deg")),
            "observer_lon_deg": float(observer.lon.to_value("deg")),
        },
    )

    return ds
