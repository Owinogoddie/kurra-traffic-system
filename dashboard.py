import asyncio
import os
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from dotenv import load_dotenv

from db import engine
import frame_slot

load_dotenv()

app = FastAPI(title="Jicho Smart v2")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SNAPSHOT_DIR = "snapshots"
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def page_live(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/stream", response_class=HTMLResponse)
async def page_stream(request: Request):
    return templates.TemplateResponse(request=request, name="stream.html")

@app.get("/snapshots", response_class=HTMLResponse)
async def page_snapshots(request: Request):
    return templates.TemplateResponse(request=request, name="snapshots.html")

@app.get("/filter", response_class=HTMLResponse)
async def page_filter(request: Request):
    return templates.TemplateResponse(request=request, name="filter.html")


# ── Snapshot image ─────────────────────────────────────────────────────────────

@app.get("/api/snapshot/{camera_id}")
async def get_snapshot(camera_id: str):
    path = os.path.join(SNAPSHOT_DIR, f"{camera_id}.jpg")
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg",
                            headers={"Cache-Control": "no-store"})
    return HTMLResponse("No snapshot yet", status_code=404)


# ── MJPEG live stream ──────────────────────────────────────────────────────────

@app.get("/api/stream/{camera_id}")
async def mjpeg_stream(camera_id: str):
    """
    Streams annotated frames as MJPEG.
    Works regardless of SHOW_FRAMES setting.
    Browser consumes it as a plain <img> tag — no JS needed.
    frame_slot is always non-None after init (placeholder until first real frame).
    """
    async def generate():
        while True:
            jpeg = frame_slot.slot.get_jpeg()   # always bytes, never None
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg +
                b"\r\n"
            )
            await asyncio.sleep(0.04)   # ~25 fps — raise/lower freely

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )


# ── Stats APIs ─────────────────────────────────────────────────────────────────

@app.get("/api/journeys")
async def api_journeys():
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT id, timestamp, camera_id, track_id, vehicle_type, from_road, to_road
            FROM kurra_journeys
            ORDER BY timestamp DESC LIMIT 30
        """)).fetchall()

        today_total = c.execute(text("""
            SELECT COUNT(*) FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
        """)).scalar()

        by_type = {r.vehicle_type: r.cnt for r in c.execute(text("""
            SELECT vehicle_type, COUNT(*) AS cnt
            FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
            GROUP BY vehicle_type
        """)).fetchall()}

    return {
        "today_total": today_total,
        "by_type":     by_type,
        "journeys": [{
            "id":           r.id,
            "timestamp":    r.timestamp.isoformat(),
            "camera_id":    r.camera_id,
            "track_id":     r.track_id,
            "vehicle_type": r.vehicle_type,
            "from_road":    r.from_road,
            "to_road":      r.to_road,
        } for r in rows],
    }


@app.get("/api/counts")
async def api_counts():
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT from_road AS road, COUNT(*) AS count
            FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
            GROUP BY from_road ORDER BY count DESC
        """)).fetchall()
    return [{"road": r.road, "count": r.count} for r in rows]


@app.get("/api/hourly")
async def api_hourly():
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT EXTRACT(HOUR FROM timestamp)::int AS hour, COUNT(*) AS count
            FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
            GROUP BY hour ORDER BY hour
        """)).fetchall()
    return [{"hour": r.hour, "count": r.count} for r in rows]


@app.get("/api/flow")
async def api_flow():
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT from_road, to_road, COUNT(*) AS count
            FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
            GROUP BY from_road, to_road
        """)).fetchall()
    flow = {}
    for r in rows:
        flow.setdefault(r.from_road, {})[r.to_road] = r.count
    return flow


# ── Filter ─────────────────────────────────────────────────────────────────────

@app.get("/api/filter")
async def api_filter(
    camera_id:    Optional[str] = None,
    vehicle_type: Optional[str] = None,
    from_road:    Optional[str] = None,
    to_road:      Optional[str] = None,
    date_from:    Optional[str] = None,
    date_to:      Optional[str] = None,
    time_from:    Optional[str] = None,
    time_to:      Optional[str] = None,
):
    clauses = ["1=1"]
    params  = {}
    if camera_id:    clauses.append("camera_id    = :camera_id");    params["camera_id"]    = camera_id
    if vehicle_type: clauses.append("vehicle_type = :vehicle_type"); params["vehicle_type"] = vehicle_type
    if from_road:    clauses.append("from_road    = :from_road");    params["from_road"]    = from_road
    if to_road:      clauses.append("to_road      = :to_road");      params["to_road"]      = to_road
    if date_from:    clauses.append("timestamp::date >= :date_from"); params["date_from"]   = date_from
    if date_to:      clauses.append("timestamp::date <= :date_to");   params["date_to"]     = date_to
    if time_from:    clauses.append("timestamp::time >= :time_from"); params["time_from"]   = time_from
    if time_to:      clauses.append("timestamp::time <= :time_to");   params["time_to"]     = time_to

    with engine.connect() as c:
        rows = c.execute(text(f"""
            SELECT id, timestamp, camera_id, track_id, vehicle_type, from_road, to_road
            FROM kurra_journeys
            WHERE {' AND '.join(clauses)}
            ORDER BY timestamp DESC LIMIT 500
        """), params).fetchall()

    return [{
        "id":           r.id,
        "timestamp":    r.timestamp.isoformat(),
        "camera_id":    r.camera_id,
        "track_id":     r.track_id,
        "vehicle_type": r.vehicle_type,
        "from_road":    r.from_road,
        "to_road":      r.to_road,
    } for r in rows]