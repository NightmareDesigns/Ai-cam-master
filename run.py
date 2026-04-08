"""Application entry point — run with ``python run.py``.

Flags
-----
(no flags)  Start the FastAPI server only (headless / background service).
--gui       Also open the NightmareDesigns desktop window (Windows / Linux).
            Equivalent to running ``python gui.py`` directly.
"""

import argparse

import uvicorn

from src.config import get_settings

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-Cam server")
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the desktop GUI window (requires pywebview)",
    )
    args = parser.parse_args()

    if args.gui:
        # Delegate to gui.py which starts the server internally.
        from gui import main as gui_main  # type: ignore

        gui_main()
    else:
        settings = get_settings()
        uvicorn.run(
            "src.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info",
        )
