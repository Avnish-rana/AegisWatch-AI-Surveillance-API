from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.src.database import Base
import uuid

class Responder(Base):
    __tablename__ = "responders"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    responder_id = Column(String, unique=True, index=True)
    name = Column(String)
    station = Column(String)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    latitude = Column(Float)
    longitude = Column(Float)
    availability = Column(String, default="AVAILABLE")
    role = Column(String)
    status = Column(String, default="ON_DUTY")
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
