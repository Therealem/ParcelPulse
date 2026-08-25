"""Carrier detection based on common tracking-number formats."""

import re

_UPS_PATTERN = re.compile(r"^1Z[A-Z0-9]{16}$")
_USPS_DOMESTIC_PATTERN = re.compile(r"^9[2345]\d{18,20}$")
_USPS_INTERNATIONAL_PATTERN = re.compile(r"^[A-Z]{2}\d{9}US$")
_FEDEX_PATTERN = re.compile(r"^(?:\d{12}|\d{15}|\d{20})$")
_DHL_PATTERN = re.compile(r"^(?:\d{10}|JJD\d{16,20}|JD\d{16,20}|GM\d{16,18})$")


def detect_carrier(tracking_number: str) -> str:
    """Return the most likely carrier for a normalized tracking number."""
    normalized = "".join(tracking_number.split()).upper()

    if _UPS_PATTERN.fullmatch(normalized):
        return "UPS"
    if _USPS_DOMESTIC_PATTERN.fullmatch(
        normalized
    ) or _USPS_INTERNATIONAL_PATTERN.fullmatch(normalized):
        return "USPS"
    if _FEDEX_PATTERN.fullmatch(normalized):
        return "FedEx"
    if _DHL_PATTERN.fullmatch(normalized):
        return "DHL"

    return "Unknown"
