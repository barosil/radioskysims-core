from __future__ import annotations

import numpy as np
import pytest


class FakeXYZ:
    def __init__(self, n):
        self.km = np.zeros((3, n))


class FakeAt:
    def __init__(self, n):
        self.xyz = FakeXYZ(n)


class FakeEarthSatellite:
    def __init__(self, *args, **_kwargs):
        pass

    def at(self, times):
        return FakeAt(len(times))


class FakeTimescale:
    def utc(self, *args, **_kwargs):
        return args

    def from_datetimes(self, times):
        return times


class FakeLoader:
    def __init__(self, *args, **kwargs):
        pass

    def timescale(self):
        return FakeTimescale()


@pytest.fixture
def fake_skyfield(monkeypatch):
    import types

    sf = types.SimpleNamespace(
        EarthSatellite=FakeEarthSatellite,
        Loader=FakeLoader,
    )

    monkeypatch.setattr(
        "radioskysims_core.domain.tracks.factory._lazy_skyfield",
        lambda: sf,
    )
