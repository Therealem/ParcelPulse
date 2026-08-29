"""Registry of carrier adapters available to the tracking pipeline."""

from app.carriers.base import CarrierAdapter
from app.carriers.dhl import DHLAdapter
from app.carriers.fedex import FedExAdapter
from app.carriers.ups import UPSAdapter
from app.carriers.usps import USPSAdapter

CARRIER_ADAPTERS: tuple[CarrierAdapter, ...] = (
    UPSAdapter(),
    USPSAdapter(),
    FedExAdapter(),
    DHLAdapter(),
)
