from pydantic import BaseModel
from typing import Optional, List
import uuid

class SessionCreate(BaseModel):
    student_id: uuid.UUID
    exercise_id: uuid.UUID
    is_handwriting: Optional[bool] = False

class SessionSubmit(BaseModel):
    student_response: str
    duration_seconds: Optional[int] = None
    ocr_confidence: Optional[float] = None

class ErrorDetail(BaseModel):
    position: int
    expected_char: str
    actual_char: str
    error_type: str

class SessionResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    exercise_id: uuid.UUID
    score: Optional[float]
    char_errors: Optional[List[ErrorDetail]]
    phonetic_score: Optional[float]
    is_handwriting: bool

    model_config = {"from_attributes": True}

class SubmitResponse(BaseModel):
    session_id: uuid.UUID
    score: float
    char_errors: list
    phonetic_score: float
    feedback: str
    new_difficulty_level: int
    words_updated: List[str]