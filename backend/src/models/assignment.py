from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.src.database import Base
import uuid

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"))
    responder_id = Column(String, ForeignKey("responders.id"))
    assigned_by = Column(String, ForeignKey("users.id"))
    distance_km = Column(Float)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    arrived_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="PENDING")
    rejection_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
