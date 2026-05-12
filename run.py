"""Application entry point — run with ``python run.py``."""

import sys

import uvicorn

from src.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    is_frozen = getattr(sys, "frozen", False)
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        # Auto-reload uses a subprocess and filesystem watchers which do not
        # behave correctly in packaged executables.
        reload=(settings.debug and not is_frozen),
        log_level="info",
    )
