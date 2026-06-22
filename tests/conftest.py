import importlib
import sys
import types
from datetime import datetime

import pytest


class FakeResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar = scalar_value

    def fetchall(self):
        return self._rows

    def scalar(self):
        return self._scalar


class FakeConnection:
    def __init__(self, dataset):
        self.dataset = dataset

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement, params=None):
        sql = getattr(statement, "text", str(statement)).lower()
        params = params or {}

        if "select count(*) from kurra_journeys" in sql and "group by" not in sql:
            return FakeResult(scalar_value=len(self.dataset))

        if "group by vehicle_type" in sql:
            counts = {}
            for row in self.dataset:
                counts[row.vehicle_type] = counts.get(row.vehicle_type, 0) + 1
            rows = [types.SimpleNamespace(vehicle_type=k, cnt=v) for k, v in counts.items()]
            return FakeResult(rows=rows)

        if "select from_road as road" in sql and "group by from_road" in sql:
            counts = {}
            for row in self.dataset:
                counts[row.from_road] = counts.get(row.from_road, 0) + 1
            rows = [types.SimpleNamespace(road=k, count=v) for k, v in counts.items()]
            return FakeResult(rows=rows)

        if "extract(hour from timestamp)" in sql:
            counts = {}
            for row in self.dataset:
                hour = row.timestamp.hour
                counts[hour] = counts.get(hour, 0) + 1
            rows = [types.SimpleNamespace(hour=h, count=counts[h]) for h in sorted(counts)]
            return FakeResult(rows=rows)

        if "group by from_road, to_road" in sql:
            counts = {}
            for row in self.dataset:
                key = (row.from_road, row.to_road)
                counts[key] = counts.get(key, 0) + 1
            rows = [
                types.SimpleNamespace(from_road=k[0], to_road=k[1], count=v)
                for k, v in counts.items()
            ]
            return FakeResult(rows=rows)

        if "where 1=1" in sql:
            filtered = []
            for row in self.dataset:
                if params.get("camera_id") and row.camera_id != params["camera_id"]:
                    continue
                if params.get("vehicle_type") and row.vehicle_type != params["vehicle_type"]:
                    continue
                if params.get("from_road") and row.from_road != params["from_road"]:
                    continue
                if params.get("to_road") and row.to_road != params["to_road"]:
                    continue
                filtered.append(row)
            return FakeResult(rows=filtered)

        if "from kurra_journeys" in sql:
            rows = sorted(self.dataset, key=lambda r: r.timestamp, reverse=True)[:30]
            return FakeResult(rows=rows)

        return FakeResult(rows=[])


class FakeEngine:
    def __init__(self, dataset):
        self._dataset = dataset

    def connect(self):
        return FakeConnection(self._dataset)


@pytest.fixture
def app_with_sqlite(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    dataset = [
        types.SimpleNamespace(
            id=1,
            timestamp=datetime(2026, 6, 22, 8, 0, 0),
            camera_id="cam_101",
            track_id=1,
            vehicle_type="car",
            from_road="town",
            to_road="ngong",
        ),
        types.SimpleNamespace(
            id=2,
            timestamp=datetime(2026, 6, 22, 9, 15, 0),
            camera_id="cam_101",
            track_id=2,
            vehicle_type="truck",
            from_road="hospital",
            to_road="town",
        ),
    ]
    fake_engine = FakeEngine(dataset)

    # Force fresh imports so module-level engine/config picks up test environment.
    for mod in ("db", "dashboard"):
        if mod in sys.modules:
            del sys.modules[mod]

    import db  # noqa: WPS433

    monkeypatch.setattr(db, "engine", fake_engine)

    import dashboard  # noqa: WPS433

    monkeypatch.setattr(dashboard, "engine", fake_engine)

    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(dashboard, "SNAPSHOT_DIR", str(snapshot_dir))

    return dashboard.app
