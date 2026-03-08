from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timezone
from app.database import get_db
from app.models.session import Session
from app.models.exercise import Exercise
from app.models.student import Student
from app.models.word_mastery import WordMastery
from app.schemas.session import SessionCreate, SessionSubmit, SubmitResponse, HandwritingSubmitResponse, TracingSubmit, TracingSubmitResponse
from app.services.evaluator import evaluate_response
import uuid
from app.services.llm import generate_feedback as llm_feedback
from app.models.exercise import Exercise as ExerciseModel
from app.services.ocr import run_ocr

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


@router.post("/{session_id}/submit-handwriting", response_model=HandwritingSubmitResponse)
async def submit_handwriting(
    session_id: uuid.UUID,
    file:       UploadFile = File(...),
    duration_seconds: int | None = Form(None),
    db:         DBSession  = Depends(get_db)
):
    """
    Submit a handwriting exercise by uploading a photo (jpg/png).

    1. Validates image type
    2. Runs Tesseract OCR → extracted text + confidence
    3. Passes OCR output to the same evaluate_response() pipeline
    4. Identical orchestration as /submit (word mastery, difficulty, LLM feedback)
    5. Returns SubmitResponse + ocr_text + ocr_confidence
    """
    # ── Validate image format ────────────────────────────────────────
    allowed = {"image/jpeg", "image/png"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{file.content_type}'. Must be jpg or png."
        )

    # ── Load session ─────────────────────────────────────────────────
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.score is not None:
        raise HTTPException(status_code=400, detail="Session already submitted")

    # ── Run OCR ──────────────────────────────────────────────────────
    image_bytes = await file.read()
    ocr_result  = run_ocr(image_bytes)
    ocr_text       = ocr_result["text"]
    ocr_confidence = ocr_result["confidence"]

    if not ocr_text.strip():
        raise HTTPException(
            status_code=422,
            detail="OCR could not extract any text from the image. "
                   "Please retake the photo with better lighting and clearer writing."
        )

    # ── 1. Evaluate (same function as typing) ────────────────────────
    result = evaluate_response(
        expected       = session.expected,
        actual         = ocr_text,
        is_handwriting = True,
        ocr_confidence = ocr_confidence
    )

    # ── 2. Save session result ───────────────────────────────────────
    session.student_response = ocr_text
    session.submitted_at     = datetime.now(timezone.utc)
    session.duration_seconds = duration_seconds
    session.score            = result["score"]
    session.char_errors      = result["char_errors"]
    session.phonetic_score   = result["phonetic_score"]
    session.is_handwriting   = True
    session.ocr_confidence   = ocr_confidence
    db.commit()

    # ── 3. Update student stats ──────────────────────────────────────
    student = db.query(Student).filter(Student.id == session.student_id).first()
    student.total_sessions += 1
    student.last_active     = datetime.now(timezone.utc)
    db.commit()

    # ── 4. Update word mastery ───────────────────────────────────────
    exercise     = db.query(Exercise).filter(Exercise.id == session.exercise_id).first()
    target_words = exercise.target_words or []
    was_correct  = result["score"] >= 0.75
    update_word_mastery(db, session.student_id, target_words, was_correct)

    # ── 5. Adjust difficulty ─────────────────────────────────────────
    new_level = update_difficulty(db, student)

    # ── 6. LLM feedback ─────────────────────────────────────────────
    age = student.age or 10
    feedback = llm_feedback(
        score         = result["score"],
        char_errors   = result["char_errors"],
        target_words  = target_words,
        student_age   = age,
        exercise_type = "handwriting"
    )

    return HandwritingSubmitResponse(
        session_id           = session.id,
        score                = result["score"],
        char_errors          = result["char_errors"],
        phonetic_score       = result["phonetic_score"],
        feedback             = feedback,
        new_difficulty_level = new_level,
        words_updated        = target_words,
        ocr_text             = ocr_text,
        ocr_confidence       = ocr_confidence
    )


@router.post("/{session_id}/submit-tracing", response_model=TracingSubmitResponse)
def submit_tracing(
    session_id: uuid.UUID,
    data:       TracingSubmit,
    db:         DBSession = Depends(get_db)
):
    """
    Submit a tracing exercise result.

    The frontend is responsible for computing trace_score (0.0–1.0) by
    comparing the student's drawn strokes against the reference path on canvas.
    The backend records the result, updates word mastery and difficulty,
    and returns LLM feedback — identical pipeline to typing and handwriting.

    stroke_errors is an optional list of per-letter accuracy breakdowns:
      [{"letter": "b", "accuracy": 0.45}, ...]
    Send it when you have per-letter data — it improves feedback quality.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.score is not None:
        raise HTTPException(status_code=400, detail="Session already submitted")

    # Clamp to valid range
    trace_score   = max(0.0, min(1.0, data.trace_score))
    stroke_errors = [e.model_dump() for e in (data.stroke_errors or [])]

    # ── 1. Save session result ───────────────────────────────────────
    session.student_response = session.expected   # student traced this word/letter
    session.submitted_at     = datetime.now(timezone.utc)
    session.duration_seconds = data.duration_seconds
    session.score            = trace_score
    session.char_errors      = stroke_errors       # reuse JSONB column for stroke data
    session.phonetic_score   = trace_score         # not applicable — mirror score
    db.commit()

    # ── 2. Update student stats ──────────────────────────────────────
    student = db.query(Student).filter(Student.id == session.student_id).first()
    student.total_sessions += 1
    student.last_active     = datetime.now(timezone.utc)
    db.commit()

    # ── 3. Update word mastery ───────────────────────────────────────
    exercise     = db.query(Exercise).filter(Exercise.id == session.exercise_id).first()
    target_words = exercise.target_words or []
    was_correct  = trace_score >= 0.75
    update_word_mastery(db, session.student_id, target_words, was_correct)

    # ── 4. Adjust difficulty ─────────────────────────────────────────
    new_level = update_difficulty(db, student)

    # ── 5. LLM feedback ─────────────────────────────────────────────
    age = student.age or 10
    feedback = llm_feedback(
        score         = trace_score,
        char_errors   = stroke_errors,
        target_words  = target_words,
        student_age   = age,
        exercise_type = "tracing"
    )

    return TracingSubmitResponse(
        session_id           = session.id,
        score                = trace_score,
        stroke_errors        = stroke_errors,
        feedback             = feedback,
        new_difficulty_level = new_level,
        words_updated        = target_words,
        trace_score          = trace_score
    )