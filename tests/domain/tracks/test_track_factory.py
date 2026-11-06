from datetime import datetime

import pytest
from radioskysims_core.infrastructure.tracks import TrackFactory


def test_factory_init():
    factory = TrackFactory({})
    assert factory.satellites_dict == {}
    assert factory._sat_cache == {}


@pytest.mark.skip(
    reason="API legada do TrackFactory (attr 'loader') não existe mais no core; "
    "verificar cobertura atual em tests/domain/test_tracks.py."
)
def test_loader_lazy(fake_skyfield):  # noqa: ARG001
    factory = TrackFactory({})
    loader1 = factory.loader
    loader2 = factory.loader

    assert loader1 is loader2


class FakeSat:
    def __init__(self):
        self.name = "SAT-1"
        self.norad_id = 123
        self.constellation = "TEST"
        self.element = type(
            "Elt",
            (),
            {
                "tle_line1": "1 00000",
                "tle_line2": "2 00000",
            },
        )()


@pytest.mark.skip(reason="API legada do TrackFactory ('_build_earthsat') não existe mais no core.")
def test_satellite_cache(fake_skyfield):  # noqa: ARG001
    factory = TrackFactory({})
    sat = FakeSat()

    es1 = factory._build_earthsat(sat)
    es2 = factory._build_earthsat(sat)

    assert es1 is es2
    assert len(factory._sat_cache) == 1


@pytest.mark.skip(reason="API legada do TrackFactory ('_lazy_Tracks') não existe mais no core.")
def test_build_tracks_returns_tracks(monkeypatch, fake_skyfield):  # noqa: ARG001
    class FakeTracks:
        @classmethod
        def from_xr(cls, ds):
            return ds

    monkeypatch.setattr(
        "radioskysims_core.domain.tracks.factory._lazy_Tracks",
        lambda: FakeTracks,
    )

    t0 = datetime.utcnow()
    factory = TrackFactory(
        {
            t0: {
                "timerange": [t0],
                "satellites": [FakeSat()],
            }
        }
    )

    result = factory.build_tracks()
    assert hasattr(result, "positions")
