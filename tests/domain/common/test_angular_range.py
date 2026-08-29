from __future__ import annotations

import numpy as np
from astropy import units as u
from astropy.coordinates import Angle

from radioskysims_core.domain.common.models import AngularRange


def test_from_degrees():
    ar = AngularRange.from_degrees(0, 90, 10)
    assert np.isclose(ar.min, 0)
    assert np.isclose(ar.max, np.pi / 2)
    assert ar.resolution > 0


def test_from_hours():
    ar = AngularRange.from_hours(0, 6, 1)
    assert np.isclose(ar.max, Angle(6, unit=u.hourangle).rad)
    assert ar.resolution > 0


def test_from_array_degrees():
    ar = AngularRange.from_array([0, 30, 60, 90] * u.deg)
    assert np.isclose(ar.resolution, np.radians(30))


def test_from_array_hours():
    ar = AngularRange.from_array([0, 3, 6] * u.hourangle)
    expected = Angle(3, unit=u.hourangle).rad
    assert np.isclose(ar.resolution, expected)


def test_from_string():
    ar = AngularRange.from_string("0,90,30", unit=u.deg)
    assert ar.max == np.pi / 2


def test_from_config():
    cfg = {"min": 0, "max": 180, "resolution": 30, "unit": "deg"}
    ar = AngularRange.from_config(cfg)
    assert np.isclose(ar.max, np.pi)


def test_default_resolution():
    ar = AngularRange.from_degrees(0, 90)
    expected = np.radians(1)
    assert np.isclose(ar.resolution, expected)


def test_range_xarray():
    ar = AngularRange.from_degrees(0, 90, 30)
    xr_data = ar.range
    assert "angle" in xr_data.dims
    assert xr_data.attrs["units"] == "rad"


def test_repr():
    ar = AngularRange.from_degrees(0, 90, 30)
    assert "AngularRange" in repr(ar)
    assert "°" in repr(ar)


def test_summary():
    ar = AngularRange.from_degrees(0, 90, 30)
    summary = ar.summary()
    assert summary["entity"] == "AngularRange"
    assert summary["units"]["external"] == "deg"
    assert summary["is_monotonic"] is True
