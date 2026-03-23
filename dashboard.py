# dashboard.py
import os
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

app       = FastAPI()
app.mount("/static", StaticFiles(directory="templates"), name="static")
templates = Jinja2Templates(directory="templates")
engine    = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True, pool_size=3)

SNAPSHOT_DIR = "snapshots"

# ── PAGES ──
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/snapshots", response_class=HTMLResponse)
async def snapshots_page(request: Request):
    return templates.TemplateResponse("snapshots.html", {"request": request})

@app.get("/filter", response_class=HTMLResponse)
async def filter_page(request: Request):
    return templates.TemplateResponse("filter.html", {"request": request})

# ── SNAPSHOT IMAGE ──
@app.get("/api/snapshot/{camera_id}")
async def get_snapshot(camera_id: str):
    path = os.path.join(SNAPSHOT_DIR, f"{camera_id}.jpg")
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")
    return FileResponse("snapshots/placeholder.jpg", media_type="image/jpeg") \
        if os.path.exists("snapshots/placeholder.jpg") \
        else HTMLResponse("No snapshot", status_code=404)

# ── API: LIVE FEED + STATS ──
@app.get("/api/journeys")
async def get_journeys():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, timestamp, camera_id, track_id,
                   vehicle_type, from_road, to_road
            FROM kurra_journeys
            ORDER BY timestamp DESC LIMIT 30
        """)).fetchall()

        today_total = conn.execute(text("""
            SELECT COUNT(*) FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
        """)).scalar()

        type_rows = conn.execute(text("""
            SELECT vehicle_type, COUNT(*) as cnt
            FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
            GROUP BY vehicle_type
        """)).fetchall()

        return {
            "journeys": [
                {
                    "id":           r.id,
                    "timestamp":    r.timestamp.isoformat(),
                    "camera_id":    r.camera_id,
                    "track_id":     r.track_id,
                    "vehicle_type": r.vehicle_type,
                    "from_road":    r.from_road,
                    "to_road":      r.to_road,
                }
                for r in rows
            ],
            "today_total": today_total,
            "by_type":     {r.vehicle_type: r.cnt for r in type_rows},
        }

# ── API: COUNTS PER ROAD ──
@app.get("/api/counts")
async def get_counts():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT from_road as road, COUNT(*) as count
            FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
            GROUP BY from_road ORDER BY count DESC
        """)).fetchall()
        return [{"road": r.road, "count": r.count} for r in rows]

# ── API: HOURLY ──
@app.get("/api/hourly")
async def get_hourly():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT EXTRACT(HOUR FROM timestamp)::int as hour,
                   COUNT(*) as count
            FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
            GROUP BY hour ORDER BY hour
        """)).fetchall()
        return [{"hour": r.hour, "count": r.count} for r in rows]

# ── API: FLOW ──
@app.get("/api/flow")
async def get_flow():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT from_road, to_road, COUNT(*) as count
            FROM kurra_journeys
            WHERE timestamp::date = CURRENT_DATE
            GROUP BY from_road, to_road
        """)).fetchall()
        flow = {}
        for r in rows:
            if r.from_road not in flow:
                flow[r.from_road] = {}
            flow[r.from_road][r.to_road] = r.count
        return flow

# ── API: FILTER ──
@app.get("/api/filter")
async def filter_journeys(
    camera_id:    Optional[str] = None,
    vehicle_type: Optional[str] = None,
    from_road:    Optional[str] = None,
    to_road:      Optional[str] = None,
    date_from:    Optional[str] = None,
    date_to:      Optional[str] = None,
    time_from:    Optional[str] = None,
    time_to:      Optional[str] = None,
):
    filters = ["1=1"]
    params  = {}

    if camera_id:    filters.append("camera_id = :camera_id");       params["camera_id"]    = camera_id
    if vehicle_type: filters.append("vehicle_type = :vehicle_type"); params["vehicle_type"] = vehicle_type
    if from_road:    filters.append("from_road = :from_road");        params["from_road"]    = from_road
    if to_road:      filters.append("to_road = :to_road");            params["to_road"]      = to_road
    if date_from:    filters.append("timestamp::date >= :date_from"); params["date_from"]    = date_from
    if date_to:      filters.append("timestamp::date <= :date_to");   params["date_to"]      = date_to
    if time_from:    filters.append("timestamp::time >= :time_from"); params["time_from"]    = time_from
    if time_to:      filters.append("timestamp::time <= :time_to");   params["time_to"]      = time_to

    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT id, timestamp, camera_id, track_id,
                   vehicle_type, from_road, to_road
            FROM kurra_journeys
            WHERE {" AND ".join(filters)}
            ORDER BY timestamp DESC LIMIT 500
        """), params).fetchall()

        return [
            {
                "id":           r.id,
                "timestamp":    r.timestamp.isoformat(),
                "camera_id":    r.camera_id,
                "track_id":     r.track_id,
                "vehicle_type": r.vehicle_type,
                "from_road":    r.from_road,
                "to_road":      r.to_road,
            }
            for r in rows
        ]