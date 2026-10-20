from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.src.database import Base
import uuid

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, unique=True, index=True)
    incident_type = Column(String)
    severity = Column(String)
    risk_score = Column(Float)
    ai_confidence = Column(Float)
    camera_id = Column(String, ForeignKey("cameras.id"), nullable=True)
    location_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    description = Column(Text)
    involved_track_ids = Column(Text)
    status = Column(String, default="NEW")
    assigned_responder_id = Column(String, ForeignKey("responders.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    source_type = Column(String, default="LIVE_CAMERA")  # LIVE_CAMERA | RECORDED_VIDEO
    video_name = Column(String, nullable=True)  # Only for RECORDED_VIDEO
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
