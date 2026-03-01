from pydantic import BaseModel
from typing import Optional, List
import uuid

class ExerciseCreate(BaseModel):
    type: str
    content: str
    expected: str
    target_words: Optional[List[str]] = []
    difficulty: int
    age_group: Optional[str] = "all"

class ExerciseResponse(BaseModel):
    id: uuid.UUID
    type: str
    content: str
    expected: str
    target_words: List[str]
    difficulty: int
    age_group: str
    source: str

    model_config = {"from_attributes": True}