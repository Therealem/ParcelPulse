"""Configuration-driven tracking provider selection."""

from pydantic import SecretStr

from app.config import TrackingProviderSettings
from app.tracking_providers.base import (
    ProviderConfigurationError,
    TrackingProvider,
)
from app.tracking_providers.mock_provider import MockTrackingProvider
from app.tracking_providers.shippo_provider import ShippoProvider


def create_tracking_provider(
    settings: TrackingProviderSettings,
) -> TrackingProvider:
    """Create the explicitly configured tracking provider."""
    if settings.tracking_provider == "mock":
        return MockTrackingProvider()

    if settings.tracking_provider == "shippo":
        api_token = _require_provider_secret(
            settings.shippo_api_token,
            "SHIPPO_API_TOKEN is required when TRACKING_PROVIDER=shippo",
        )
        return ShippoProvider(api_token)

    # EasyPost remains an optional legacy selection. Import it only when that
    # provider is explicitly selected so mock and Shippo do not depend on an
    # optional adapter being installed.
    from app.tracking_providers.easypost_provider import EasyPostProvider

    api_key = _require_provider_secret(
        settings.easypost_api_key,
        "EASYPOST_API_KEY is required when TRACKING_PROVIDER=easypost",
    )
    return EasyPostProvider(api_key)


def _require_provider_secret(
    secret: SecretStr | None,
    message: str,
) -> SecretStr:
    """Reject missing/documentation-placeholder provider credentials."""
    if secret is None:
        raise ProviderConfigurationError(message)

    value = secret.get_secret_value()
    if not value or value.lower().startswith(
        ("replace_", "paste_", "change_")
    ):
        raise ProviderConfigurationError(message)
    return secret
