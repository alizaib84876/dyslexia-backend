from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime, timezone
import uuid
from app.database import Base

class WordMastery(Base):
    __tablename__ = "word_mastery"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id    = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    word          = Column(String, nullable=False)
    mastery_score = Column(Float, default=0.0)
    times_seen    = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    ease_factor   = Column(Float, default=2.5)   # for spaced rep later
    next_review   = Column(DateTime, nullable=True)
    last_seen     = Column(DateTime, nullable=True)