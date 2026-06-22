from pathlib import Path

from fastapi.testclient import TestClient


def test_health_pages_render(app_with_sqlite):
    client = TestClient(app_with_sqlite)

    for path in ("/", "/stream", "/snapshots", "/filter"):
        response = client.get(path)
        assert response.status_code == 200


def test_api_smoke_json_endpoints(app_with_sqlite):
    client = TestClient(app_with_sqlite)

    journeys = client.get("/api/journeys")
    assert journeys.status_code == 200
    payload = journeys.json()
    assert "today_total" in payload
    assert "journeys" in payload

    counts = client.get("/api/counts")
    assert counts.status_code == 200
    assert isinstance(counts.json(), list)

    hourly = client.get("/api/hourly")
    assert hourly.status_code == 200
    assert isinstance(hourly.json(), list)

    flow = client.get("/api/flow")
    assert flow.status_code == 200
    assert isinstance(flow.json(), dict)


def test_api_filter_with_query_params(app_with_sqlite):
    client = TestClient(app_with_sqlite)

    response = client.get(
        "/api/filter",
        params={
            "camera_id": "cam_101",
            "vehicle_type": "car",
            "from_road": "town",
            "to_road": "ngong",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_snapshot_not_found_when_missing_file(app_with_sqlite):
    client = TestClient(app_with_sqlite)

    response = client.get("/api/snapshot/cam_101")
    assert response.status_code == 404


def test_snapshot_serves_file_when_present(app_with_sqlite, tmp_path):
    client = TestClient(app_with_sqlite)

    snap = tmp_path / "snapshots" / "cam_101.jpg"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_bytes(b"fake-jpeg")

    # Override app snapshot dir for this test case.
    import dashboard

    dashboard.SNAPSHOT_DIR = str(snap.parent)

    response = client.get("/api/snapshot/cam_101")
    assert response.status_code == 200
