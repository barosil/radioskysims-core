from __future__ import annotations

import logging

from radioskysims_core.domain.common.logging import DomainLogger


def test_domain_logger_debug_preserves_exc_info(caplog) -> None:
    logger = DomainLogger("tests.domain_logger")

    with caplog.at_level(logging.DEBUG, logger="tests.domain_logger"):
        try:
            msg = "zarr failure"
            raise RuntimeError(msg)
        except RuntimeError:
            logger.debug(
                "tracks_zarr_metadata_consolidation_failed",
                exc_info=True,
            )

    assert len(caplog.records) == 1
    assert caplog.records[0].exc_info is not None
