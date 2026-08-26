"""Create the shipment table in the configured PostgreSQL database."""

from app.database.session import get_engine
from app.models import Shipment


def create_shipment_table() -> None:
    """Create only the shipment table when it does not already exist."""
    Shipment.__table__.create(bind=get_engine(), checkfirst=True)


if __name__ == "__main__":
    create_shipment_table()
    print("Shipment table is ready.")
