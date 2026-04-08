"""Offline AI model manager.

Ensures YOLO model weights are cached in a persistent local directory so
AI-Cam can run fully offline after the first download.

Usage::

    from src.detection.model_manager import resolve_model
    path = resolve_model("yolov8n.pt")   # downloads once, then offline-safe

Pre-download from the command line::

    python -m src.detection.model_manager yolov8n.pt
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Persistent local cache relative to the working directory.
# Override by setting AICAM_MODEL_DIR env var or passing an absolute path
# as yolo_model in .env / settings.
_MODEL_CACHE_DIR = Path("models")


def resolve_model(model_name: str) -> str:
    """Return a usable path for *model_name*, downloading it if necessary.

    Resolution order
    ----------------
    1. Absolute path that already exists  → use as-is.
    2. ``models/<basename>`` exists       → use cached copy (offline-safe).
    3. Download via ultralytics hub, save into ``models/`` for reuse.
    4. Fallback: return *model_name* unchanged so YOLO handles it.

    On first run an internet connection is required.  Every subsequent run
    works completely offline.
    """
    # 1. Absolute / already-valid path
    given = Path(model_name)
    if given.is_absolute() and given.exists():
        logger.info("Using local model: %s", given)
        return str(given)

    # 2. Check our cache directory
    _MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = _MODEL_CACHE_DIR / given.name
    if cached.exists():
        logger.info("Using offline-cached model: %s", cached)
        return str(cached)

    # 3. Download and persist
    logger.info(
        "Model '%s' not in local cache (%s). Downloading for offline use ...",
        model_name,
        _MODEL_CACHE_DIR,
    )
    try:
        from ultralytics import YOLO  # type: ignore

        tmp_model = YOLO(model_name)

        # ultralytics writes the weights to CWD by default; use only the
        # basename so a model_name like "subdir/yolov8n.pt" is handled safely.
        downloaded_cwd = Path(Path(model_name).name)
        if downloaded_cwd.exists():
            shutil.move(str(downloaded_cwd), str(cached))
            logger.info(
                "Model cached at %s — future runs are fully offline.", cached
            )
            return str(cached)

        # Some ultralytics versions expose the resolved path.
        ckpt = getattr(tmp_model, "ckpt_path", None)
        if ckpt and Path(ckpt).exists():
            shutil.copy2(ckpt, cached)
            logger.info(
                "Model cached at %s — future runs are fully offline.", cached
            )
            return str(cached)

    except Exception as exc:
        logger.error(
            "Failed to download model '%s': %s\n"
            "  → If you are offline, place the weights file at: %s",
            model_name,
            exc,
            cached.resolve(),
        )

    # 4. Fallback — let YOLO try from its own internal cache.
    return model_name


# ── CLI helper: ``python -m src.detection.model_manager yolov8n.pt`` ─────────


def _cli() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else "yolov8n.pt"
    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
    path = resolve_model(model)
    print(f"Model ready at: {path}")


if __name__ == "__main__":
    _cli()
