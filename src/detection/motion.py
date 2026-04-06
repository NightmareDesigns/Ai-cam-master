"""Background-subtraction / frame-differencing motion detector."""

from __future__ import annotations

import cv2
import numpy as np


class MotionDetector:
    """Simple motion detector using frame differencing + contour area threshold.

    Parameters
    ----------
    min_area:
        Minimum contour area (pixels²) to count as motion.
    blur_size:
        Gaussian blur kernel size applied before differencing.
    history:
        Number of frames kept by the background subtractor.
    """

    def __init__(
        self,
        min_area: int = 1500,
        blur_size: int = 21,
        history: int = 200,
    ) -> None:
        self.min_area = min_area
        self.blur_size = blur_size
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=history, varThreshold=40, detectShadows=False
        )

    def detect(self, frame: np.ndarray) -> bool:
        """Return ``True`` if significant motion is detected in *frame*."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (self.blur_size, self.blur_size), 0)
        mask = self._bg.apply(blurred)
        # Morphological clean-up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return any(cv2.contourArea(c) >= self.min_area for c in contours)

    def reset(self) -> None:
        """Reset the background model (e.g. after camera switch)."""
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=40, detectShadows=False
        )
