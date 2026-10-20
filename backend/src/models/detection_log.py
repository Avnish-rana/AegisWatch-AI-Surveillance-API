from sqlalchemy import Column, String, Float, Text, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.src.database import Base
import uuid

class DetectionLog(Base):
    __tablename__ = "detection_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("cameras.id"))
    frame_number = Column(Integer)
    track_id = Column(Integer)
    class_name = Column(String)
    confidence = Column(Float)
    bbox_json = Column(Text)
    event_type = Column(String, nullable=True)
    risk_score = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)
