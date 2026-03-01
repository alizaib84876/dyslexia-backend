from pydantic import BaseModel
from typing import Optional
import uuid

class StudentCreate(BaseModel):
    name: str
    age: Optional[int] = None

class StudentResponse(BaseModel):
    id: uuid.UUID
    name: str
    age: Optional[int]
    difficulty_level: int
    total_sessions: int
    streak_days: int

    model_config = {"from_attributes": True}