from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timezone
from app.database import get_db
from app.models.session import Session
from app.models.exercise import Exercise
from app.models.student import Student
from app.models.word_mastery import WordMastery
from app.schemas.session import SessionCreate, SessionSubmit, SubmitResponse
from app.services.evaluator import evaluate_response
import uuid
from app.services.llm import generate_feedback as llm_feedback
from app.models.exercise import Exercise as ExerciseModel

router = APIRouter(prefix="/sessions", tags=["Sessions"])

def update_word_mastery(db, student_id, words: list, was_correct: bool):
    for word in words:
        wm = db.query(WordMastery).filter_by(
            student_id=student_id, word=word.lower()
        ).first()
        if not wm:
            wm = WordMastery(
                student_id    = student_id,
                word          = word.lower(),
                times_seen    = 0,
                times_correct = 0,
                mastery_score = 0.0
            )
            db.add(wm)
            db.flush()

        wm.times_seen    = (wm.times_seen or 0) + 1
        wm.times_correct = (wm.times_correct or 0) + (1 if was_correct else 0)
        wm.last_seen     = datetime.now(timezone.utc)
        wm.mastery_score = wm.times_correct / wm.times_seen
    db.commit()

def update_difficulty(db, student, recent_n: int = 3):
    recent = (
        db.query(Session)
        .filter(Session.student_id == student.id, Session.score.isnot(None))
        .order_by(Session.submitted_at.desc())
        .limit(recent_n)
        .all()
    )
    if len(recent) < 2:
        return student.difficulty_level

    avg = sum(s.score for s in recent) / len(recent)
    if avg > 0.80:
        student.difficulty_level = min(10, student.difficulty_level + 1)
    elif avg < 0.50:
        student.difficulty_level = max(1,  student.difficulty_level - 1)
    db.commit()
    return student.difficulty_level

def simple_feedback(score: float, worst_word: str = "") -> str:
    if score >= 0.90:
        msg = "Outstanding! You are doing brilliantly!"
    elif score >= 0.75:
        msg = "Great job! Keep up the good work!"
    elif score >= 0.50:
        msg = "Good effort! Practice makes perfect."
    else:
        msg = "Keep going — every attempt makes you stronger!"

    if worst_word:
        msg += f" Focus a little extra on the word '{worst_word}'."
    return msg

@router.post("/", )
def create_session(data: SessionCreate, db: DBSession = Depends(get_db)):
    exercise = db.query(Exercise).filter(Exercise.id == data.exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    student = db.query(Student).filter(Student.id == data.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    session = Session(
        student_id     = data.student_id,
        exercise_id    = data.exercise_id,
        is_handwriting = data.is_handwriting,
        expected       = exercise.expected
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "expected": exercise.expected}

@router.post("/{session_id}/submit", response_model=SubmitResponse)
def submit_session(
    session_id: uuid.UUID,
    data:       SessionSubmit,
    db:         DBSession = Depends(get_db)
):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.score is not None:
        raise HTTPException(status_code=400, detail="Session already submitted")

    # 1. Evaluate
    result = evaluate_response(
        expected       = session.expected,
        actual         = data.student_response,
        is_handwriting = session.is_handwriting,
        ocr_confidence = data.ocr_confidence or 1.0
    )

    # 2. Save session result
    session.student_response = data.student_response
    session.submitted_at     = datetime.now(timezone.utc)
    session.duration_seconds = data.duration_seconds
    session.score            = result["score"]
    session.char_errors      = result["char_errors"]
    session.phonetic_score   = result["phonetic_score"]
    db.commit()

    # 3. Update student stats
    student = db.query(Student).filter(Student.id == session.student_id).first()
    student.total_sessions += 1
    student.last_active     = datetime.now(timezone.utc)
    db.commit()

    # 4. Update word mastery
    exercise     = db.query(Exercise).filter(Exercise.id == session.exercise_id).first()
    target_words = exercise.target_words or []
    was_correct  = result["score"] >= 0.75
    update_word_mastery(db, session.student_id, target_words, was_correct)

    # 5. Adjust difficulty
    new_level = update_difficulty(db, student)

    # 6. Simple feedback
    worst_word = ""
    if result["char_errors"]:
        worst_word = session.expected.split()[0] if session.expected else ""
    exercise_for_feedback = db.query(ExerciseModel).filter(
        ExerciseModel.id == session.exercise_id
    ).first()
    age = student.age or 10
    feedback = llm_feedback(
        score         = result["score"],
        char_errors   = result["char_errors"],
        target_words  = target_words,
        student_age   = age,
        exercise_type = exercise_for_feedback.type if exercise_for_feedback else "typing"
    )

    return SubmitResponse(
        session_id        = session.id,
        score             = result["score"],
        char_errors       = result["char_errors"],
        phonetic_score    = result["phonetic_score"],
        feedback          = feedback,
        new_difficulty_level = new_level,
        words_updated     = target_words
    )