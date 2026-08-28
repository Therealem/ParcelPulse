"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import router as auth_router
from app.api.shipments import router as shipments_router
from app.api.tracking import router as tracking_router
from app.config import get_application_settings
from app.database import get_engine

logger = logging.getLogger(__name__)
application_settings = get_application_settings()

app = FastAPI(
    title="ParcelPulse API",
    description="Backend API for the ParcelPulse package tracking platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[application_settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tracking_router)
app.include_router(shipments_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return the API's current health status."""
    return {"status": "ok", "service": "parcelpulse-api"}


@app.get("/health/db", tags=["system"])
def database_health_check() -> dict[str, str]:
    """Verify that the API can execute a query against PostgreSQL."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, ValidationError) as error:
        logger.error("Database health check failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": "unavailable"},
        ) from error

    return {"status": "ok", "database": "connected"}
