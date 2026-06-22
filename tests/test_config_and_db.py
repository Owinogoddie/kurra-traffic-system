import importlib
import sys

import pytest


def test_db_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    if "db" in sys.modules:
        del sys.modules["db"]

    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        importlib.import_module("db")


def test_config_dashboard_defaults(monkeypatch):
    monkeypatch.delenv("DASHBOARD_HOST", raising=False)
    monkeypatch.delenv("DASHBOARD_PORT", raising=False)

    if "config" in sys.modules:
        del sys.modules["config"]

    config = importlib.import_module("config")

    assert config.DASHBOARD_HOST == "0.0.0.0"
    assert config.DASHBOARD_PORT == 3300
    assert "cam_101" in config.CAMERAS
