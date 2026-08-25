"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.tracking import router as tracking_router

app = FastAPI(
    title="ParcelPulse API",
    description="Backend API for the ParcelPulse package tracking platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracking_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return the API's current health status."""
    return {"status": "ok", "service": "parcelpulse-api"}
