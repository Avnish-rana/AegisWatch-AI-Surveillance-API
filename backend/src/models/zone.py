from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.src.database import Base
import uuid

class Zone(Base):
    __tablename__ = "zones"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, ForeignKey("cameras.id"))
    zone_name = Column(String)
    zone_type = Column(String)
    polygon_json = Column(Text)
    is_active = Column(Boolean, default=True)
    loitering_threshold_seconds = Column(Integer, default=300)
    color = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
