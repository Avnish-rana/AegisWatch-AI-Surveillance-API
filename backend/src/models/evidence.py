from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.src.database import Base
import uuid

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"))
    evidence_type = Column(String)
    file_path = Column(Text)
    file_name = Column(Text)
    file_size = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
