from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey
from datetime import datetime, timezone
import uuid
from app.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id       = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    exercise_id      = Column(UUID(as_uuid=True), ForeignKey("exercises.id"), nullable=False)
    started_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    submitted_at     = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    student_response = Column(Text, nullable=True)
    expected         = Column(Text, nullable=True)
    score            = Column(Float, nullable=True)
    char_errors      = Column(JSONB, default=list)
    phonetic_score   = Column(Float, nullable=True)
    is_handwriting   = Column(Boolean, default=False)
    ocr_confidence   = Column(Float, nullable=True)