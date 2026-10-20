from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.sql import func
from backend.src.database import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String, unique=True, index=True)
    setting_value = Column(Text)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
