"""Development provider backed by deterministic carrier adapters."""

from collections.abc import Sequence

from app.carriers.base import CarrierAdapter, CarrierAdapterError
from app.carriers.registry import CARRIER_ADAPTERS
from app.tracking_providers.base import (
    ProviderUnavailableError,
    ProviderUnsupportedCarrierError,
    TrackingResult,
)


class MockTrackingProvider:
    """Preserve the existing deterministic mock carrier behavior."""

    name = "mock"

    def __init__(
        self,
        adapters: Sequence[CarrierAdapter] = CARRIER_ADAPTERS,
    ) -> None:
        self.adapters = adapters

    def track(self, tracking_number: str, carrier: str) -> TrackingResult:
        adapter = next(
            (
                candidate
                for candidate in self.adapters
                if candidate.name == carrier
            ),
            None,
        )
        if adapter is None:
            raise ProviderUnsupportedCarrierError(
                "The mock provider does not support this carrier"
            )

        try:
            return adapter.track(tracking_number)
        except CarrierAdapterError as error:
            raise ProviderUnavailableError(
                "The mock tracking adapter failed"
            ) from error
