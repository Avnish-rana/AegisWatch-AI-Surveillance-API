from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.src.database import Base
import uuid

class IncidentStatusHistory(Base):
    __tablename__ = "incident_status_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"))
    from_status = Column(String)
    to_status = Column(String)
    changed_by = Column(String, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), default=func.now())
