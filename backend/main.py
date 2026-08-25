"""Compatibility entry point for running Uvicorn from the backend directory."""

from app.main import app

__all__ = ["app"]
