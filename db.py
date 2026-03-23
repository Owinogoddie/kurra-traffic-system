# db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine      = create_engine(DATABASE_URL, pool_pre_ping=True)
Base        = declarative_base()
SessionLocal = sessionmaker(bind=engine)


class Journey(Base):
    __tablename__ = "kurra_journeys"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    timestamp    = Column(DateTime, default=datetime.utcnow)
    camera_id    = Column(String(20))   # cam_101, cam_102, cam_103
    track_id     = Column(Integer)      # ByteTrack vehicle ID
    vehicle_type = Column(String(30))   # car, truck, bus, motorcycle
    from_road    = Column(String(30))   # town, ngong, 5th_ave, hospital
    to_road      = Column(String(30))   # town, ngong, 5th_ave, hospital


def init_db():
    """Create table if it doesn't exist."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database ready!")


def save_journey(camera_id, track_id, vehicle_type, from_road, to_road):
    """Save one completed journey to DB."""
    session = SessionLocal()
    try:
        journey = Journey(
            camera_id=camera_id,
            track_id=track_id,
            vehicle_type=vehicle_type,
            from_road=from_road,
            to_road=to_road,
            timestamp=datetime.utcnow()
        )
        session.add(journey)
        session.commit()
        print(f"💾 Saved: {from_road} → {to_road} ({vehicle_type}) [{camera_id}]")
    except Exception as e:
        session.rollback()
        print(f"❌ Save failed: {e}")
    finally:
        session.close()


def get_journeys(camera_id=None):
    """
    Fetch journeys from DB.
    Optionally filter by camera.
    """
    session = SessionLocal()
    try:
        query = session.query(Journey)
        if camera_id:
            query = query.filter(Journey.camera_id == camera_id)
        return query.order_by(Journey.timestamp.desc()).all()
    finally:
        session.close()