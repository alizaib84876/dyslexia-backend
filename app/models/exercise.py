from sqlalchemy import Column, String, Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from app.database import Base

class Exercise(Base):
    __tablename__ = "exercises"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type         = Column(String, nullable=False)   # word_typing, sentence_typing, handwriting
    content      = Column(Text, nullable=False)     # what the student sees
    expected     = Column(Text, nullable=False)     # exact correct answer
    target_words = Column(ARRAY(String), default=list)
    difficulty   = Column(Integer, nullable=False)  # 1-10
    age_group    = Column(String, default="all")    # "5-7", "8-10", "11-13", "all"
    source       = Column(String, default="pre_stored")
    times_served = Column(Integer, default=0)
    avg_accuracy = Column(Float, default=0.0)