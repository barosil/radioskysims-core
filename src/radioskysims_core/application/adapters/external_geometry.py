"""
Módulo: src/radioskysims_core/application/adapters/external_geometry.py

Descrição:
    Implementações de provedores de geometria usando bibliotecas externas.
    Adapter: Skyfield (biblioteca de astrometria externa) → GeometryProviderPort.
    
    Movido de domain/geometry/skyfield_provider.py para application/adapters
    por estar acoplado a Skyfield (dependência externa, não parte do domínio puro).

Copyright BINGO Collaboration
Last modified: 2026-11-05
"""

from __future__ import annotations

import numpy as np
import xarray as xr
from skyfield.api import EarthSatellite, wgs84

from radioskysims_core.domain.geometry.interface import GeometryProviderPort
from radioskysims_core.infrastructure.tracks import TrackFactory


class SkyfieldGeometryProvider(GeometryProviderPort):
    """
    Adapter: Converte tracks orbitais em geometria observacional usando Skyfield.
    
    Implementa GeometryProviderPort (contrato do domínio) usando Skyfield
    como biblioteca externa de cálculos astronômicos.
    """

    def __init__(self, ts):
        self.ts = ts
        self.track_factory = TrackFactory()

    def compute(self, tracks, observer, _sat_block=None) -> xr.Dataset:
        """
        Computa geometria (azimute, elevação, range, RA/Dec) para tracks.

        Args:
            tracks: Dataset com dimensões time, satellite e coordenadas
                    (earthsats OR tle_line1/tle_line2)
            observer: Objeto com atributos lat (Angle), lon (Angle)
            _sat_block: Ignorado (compatibilidade de interface)

        Returns:
            xr.Dataset com data_vars (theta, range, az, el, ra, dec)
        """
        # TrackFactory stores `time` as TT Julian dates (float days).
        times = self.ts.tt_jd(np.asarray(tracks.time.values, dtype=float))

        obs = wgs84.latlon(
            observer.lat.value,
            observer.lon.value,
            # elevation_m=observer.height,
        )
        if "earthsats" in tracks.coords:
            sats = tracks.earthsats.values
        elif "tle_line1" in tracks.coords and "tle_line2" in tracks.coords:
            tle1s = tracks.tle_line1.values
            tle2s = tracks.tle_line2.values
            names = tracks.names.values if "names" in tracks.coords else tracks.satellite.values
            sats = [
                EarthSatellite(str(t1), str(t2), str(n), self.ts)
                for t1, t2, n in zip(tle1s, tle2s, names, strict=False)
            ]
        else:
            msg = (
                "tracks dataset must include 'earthsats' or TLE coordinates "
                "('tle_line1', 'tle_line2')."
            )
            raise ValueError(msg)

        topocentric = [sat.at(times) - obs.at(times) for sat in sats]

        alts = []
        azs = []
        rs = []
        thetas = []
        ra_list = []
        dec_list = []
        for topo in topocentric:
            alt, az, r = topo.altaz()
            ra, dec, _ = topo.radec()

            theta = np.pi / 2 - alt.radians
            alts.append(alt.radians)
            azs.append(az.radians)
            rs.append(r.m)
            thetas.append(theta)
            # RA/Dec em radianos (skyfield radec() retorna ra em horas, dec em graus)
            ra_list.append(ra.radians)
            dec_list.append(dec.radians)

        theta_arr = np.stack(thetas, axis=0)
        range_arr = np.stack(rs, axis=0)
        az_arr = np.stack(azs, axis=0)
        el_arr = np.stack(alts, axis=0)
        ra_arr = np.stack(ra_list, axis=0)
        dec_arr = np.stack(dec_list, axis=0)

        # Detach any auxiliary coords (names, TLEs, etc.) from dimension coords.
        sat_coords = np.asarray(tracks.satellite.values)
        time_coords = np.asarray(tracks.time.values, dtype=float)
        return xr.Dataset(
            data_vars={
                "theta": (["satellite", "time"], theta_arr),
                "range": (["satellite", "time"], range_arr),
                "az": (["satellite", "time"], az_arr),
                "el": (["satellite", "time"], el_arr),
                "ra": (["satellite", "time"], ra_arr),
                "dec": (["satellite", "time"], dec_arr),
            },
            coords={"satellite": sat_coords, "time": time_coords},
            attrs={"provider": "skyfield"},
        )

    def calculate_position(
        self,
        satellite,
        time,
        observer_lat: float,
        observer_lon: float,
    ) -> tuple:
        """
        Calcula posição (theta, phi, range) de um satélite.

        Args:
            satellite: Objeto EarthSatellite do Skyfield.
            time: Skyfield time object.
            observer_lat: Latitude em graus.
            observer_lon: Longitude em graus.

        Returns:
            tuple: (theta, phi, range) em radianos e metros.
        """
        obs = wgs84.latlon(observer_lat, observer_lon)
        topo = satellite.at(time) - obs.at(time)

        alt, az, r = topo.altaz()

        theta = np.pi / 2 - alt.radians
        phi = az.radians
        range_m = r.m

        return theta, phi, range_m

    def calculate_range(
        self,
        satellite,
        time,
        observer_lat: float | None = None,
        observer_lon: float | None = None,
    ):
        """
        Calcula distância satélite-observador.

        Args:
            satellite: Objeto EarthSatellite do Skyfield.
            time: Skyfield time object.
            observer_lat: Latitude em graus (opcional).
            observer_lon: Longitude em graus (opcional).

        Returns:
            Distance: Objeto Skyfield Distance ou valor em metros.
        """
        if observer_lat is None or observer_lon is None:
            return None

        obs = wgs84.latlon(observer_lat, observer_lon)
        topo = satellite.at(time) - obs.at(time)

        return topo.distance
