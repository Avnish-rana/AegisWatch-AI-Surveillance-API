from sqlalchemy import Column, String, Float, Boolean, Text, DateTime
from sqlalchemy.sql import func
from backend.src.database import Base
import uuid

class Camera(Base):
    __tablename__ = "cameras"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id = Column(String, unique=True, index=True)
    name = Column(String)
    description = Column(String, nullable=True)
    source_type = Column(String) # RTSP, WEBCAM, FILE, DEMO
    source_url = Column(String)
    location_name = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    status = Column(String, default="OFFLINE") # ONLINE, OFFLINE, ERROR
    is_enabled = Column(Boolean, default=True)
    config_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
