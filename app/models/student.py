from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from app.database import Base

class Student(Base):
    __tablename__ = "students"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name             = Column(String, nullable=False)
    age              = Column(Integer, nullable=True)
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active      = Column(DateTime, nullable=True)
    difficulty_level = Column(Integer, default=1)
    total_sessions   = Column(Integer, default=0)
    streak_days      = Column(Integer, default=0)