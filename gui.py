"""Desktop GUI launcher — NightmareDesigns AI-Cam.

Starts the FastAPI/uvicorn server in a background thread, waits for it to be
ready, then opens a native desktop window via pywebview.

Platforms
---------
Windows   Uses the built-in Edge/WebView2 renderer (no extra install).
Linux     Uses WebKitGTK — install with:
              sudo apt install python3-webview   # or
              pip install pywebview[gtk]
Android   Not applicable; use the Progressive Web App (PWA) instead —
          open the server URL in Chrome and choose "Add to Home Screen".

Usage
-----
    python gui.py           # launch GUI directly
    python run.py --gui     # equivalent via the main entry-point
"""

from __future__ import annotations

import logging
import socket
import sys
import threading
import time

import uvicorn

from src.config import get_settings

logger = logging.getLogger(__name__)

_WINDOW_TITLE = "AI-Cam · NightmareDesigns"
_MIN_WIDTH = 900
_MIN_HEIGHT = 600
_DEFAULT_WIDTH = 1280
_DEFAULT_HEIGHT = 800


# ── Helpers ───────────────────────────────────────────────────────────────────


def _find_free_port() -> int:
    """Bind to port 0 and return the OS-assigned free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _port_in_use(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def _wait_for_server(host: str, port: int, timeout: float = 20.0) -> bool:
    """Poll until the HTTP server responds or *timeout* seconds elapse."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_in_use(host, port):
            return True
        time.sleep(0.15)
    return False


def _run_server(host: str, port: int) -> None:
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )


# ── Entry-point ───────────────────────────────────────────────────────────────


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )

    try:
        import webview  # type: ignore
    except ImportError:
        logger.error(
            "pywebview is not installed.\n"
            "  Install with:  pip install pywebview\n"
            "  On Linux also: sudo apt install python3-webview\n"
            "Falling back to headless server mode."
        )
        # Run as a plain server so the app is still usable via a browser.
        settings = get_settings()
        _run_server(settings.host, settings.port)
        return

    settings = get_settings()
    host = "127.0.0.1"
    port = settings.port

    # If the configured port is already occupied (e.g. another instance is
    # running), pick a fresh one so both can coexist.
    if _port_in_use(host, port):
        port = _find_free_port()
        logger.info("Default port busy — using port %d instead.", port)

    server_thread = threading.Thread(
        target=_run_server, args=(host, port), daemon=True, name="aicam-server"
    )
    server_thread.start()

    logger.info("Waiting for AI-Cam server on %s:%d …", host, port)
    if not _wait_for_server(host, port):
        logger.error("Server did not start within the timeout window. Exiting.")
        sys.exit(1)

    url = f"http://{host}:{port}/"
    logger.info("Opening NightmareDesigns AI-Cam GUI at %s", url)

    window = webview.create_window(
        _WINDOW_TITLE,
        url=url,
        width=_DEFAULT_WIDTH,
        height=_DEFAULT_HEIGHT,
        min_size=(_MIN_WIDTH, _MIN_HEIGHT),
        text_select=False,
    )

    # debug=True opens the DevTools panel (useful during development)
    webview.start(debug=settings.debug)


if __name__ == "__main__":
    main()
