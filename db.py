import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, text
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add DATABASE_URL to your environment or .env file."
    )

engine       = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=3)
Base         = declarative_base()
SessionLocal = sessionmaker(bind=engine)


class Journey(Base):
    __tablename__ = "kurra_journeys"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    timestamp    = Column(DateTime, default=datetime.utcnow)
    camera_id    = Column(String(20))
    track_id     = Column(Integer)
    vehicle_type = Column(String(30))
    from_road    = Column(String(30))
    to_road      = Column(String(30))


def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database ready")


def save_journey(camera_id, track_id, vehicle_type, from_road, to_road):
    session = SessionLocal()
    try:
        session.add(Journey(
            camera_id    = camera_id,
            track_id     = track_id,
            vehicle_type = vehicle_type,
            from_road    = from_road,
            to_road      = to_road,
            timestamp    = datetime.utcnow(),
        ))
        session.commit()
        print(f"💾 {from_road} → {to_road}  ({vehicle_type})  [{camera_id}]")
    except Exception as e:
        session.rollback()
        print(f"❌ Save failed: {e}")
    finally:
        session.close()