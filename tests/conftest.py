"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import create_app

# Ensure all models are registered before creating tables
from src.models import camera, event, alert_rule  # noqa: F401


@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite engine for tests.

    StaticPool ensures all sessions reuse a single connection so that the
    in-memory database (and its tables) is shared across the test session.
    """
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    _engine.dispose()


@pytest.fixture()
def db(engine):
    """Per-test DB session, rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(engine):
    """FastAPI test client with in-memory DB.

    We patch:
    1. The ``get_db`` dependency so API routes use the in-memory engine.
    2. ``src.database.create_tables`` to a no-op so lifespan doesn't touch the
       real on-disk database.
    3. ``src.camera.manager.camera_manager.startup`` to a no-op so no threads
       are spawned during tests.
    """
    from unittest.mock import patch

    Session = sessionmaker(bind=engine)

    def override_get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("src.main.create_tables"),
        patch("src.main.camera_manager.startup"),
        patch("src.main.camera_manager.shutdown"),
        patch("src.main.det_module.load_model"),
    ):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
