"""Create ParcelPulse tables in the configured PostgreSQL database."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_engine
from app.models import Base, Shipment
from app.services.shipment_service import add_mock_tracking_events

MOCK_UPS_TRACKING_NUMBER = "1Z999AA10123456784"


def create_database_tables() -> None:
    """Create all registered tables that do not already exist."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        shipment = session.scalar(
            select(Shipment).where(
                Shipment.tracking_number == MOCK_UPS_TRACKING_NUMBER
            )
        )
        if shipment is not None:
            add_mock_tracking_events(shipment, shipment.carrier)
            session.commit()


def create_shipment_table() -> None:
    """Create database tables through the original public helper name."""
    create_database_tables()


if __name__ == "__main__":
    create_database_tables()
    print("ParcelPulse database tables are ready.")
