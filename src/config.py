"""Application configuration via environment variables / .env file."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    secret_key: str = "change-me-to-a-random-secret"

    # Storage
    database_url: str = "sqlite:///./aicam.db"
    recordings_dir: str = "./recordings"
    snapshots_dir: str = "./snapshots"
    max_recording_days: int = 30

    # Detection
    yolo_model: str = "yolov8n.pt"
    detection_confidence: float = 0.45
    tracked_classes: str = "person,car,truck,bus,motorcycle,bicycle,dog,cat"

    # Streaming
    stream_fps: int = 10
    stream_jpeg_quality: int = 75

    # Alerts
    alert_cooldown_seconds: int = 30

    # Email notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_from: str = ""
    alert_email_to: str = ""

    @property
    def tracked_classes_list(self) -> List[str]:
        if not self.tracked_classes.strip():
            return []
        return [c.strip().lower() for c in self.tracked_classes.split(",") if c.strip()]

    def ensure_dirs(self) -> None:
        os.makedirs(self.recordings_dir, exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
