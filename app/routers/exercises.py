from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from app.database import get_db
from app.models.exercise import Exercise
from app.models.student import Student
from app.models.word_mastery import WordMastery
from app.schemas.exercise import ExerciseCreate, ExerciseResponse
import uuid, random
from app.services.llm import generate_exercises as llm_generate

router = APIRouter(prefix="/exercises", tags=["Exercises"])


@router.post("/", response_model=ExerciseResponse)
def create_exercise(data: ExerciseCreate, db: Session = Depends(get_db)):
    exercise = Exercise(**data.model_dump())
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.get("/", response_model=List[ExerciseResponse])
def list_exercises(
    difficulty: Optional[int] = Query(None),
    type:       Optional[str] = Query(None),
    db:         Session       = Depends(get_db)
):
    query = db.query(Exercise)
    if difficulty:
        query = query.filter(Exercise.difficulty == difficulty)
    if type:
        query = query.filter(Exercise.type == type)
    return query.all()


def get_weak_words(db, student_id) -> set:
    """Return words where mastery score is below 0.6."""
    weak = db.query(WordMastery).filter(
        WordMastery.student_id == student_id,
        WordMastery.mastery_score < 0.6
    ).all()
    return {wm.word.lower() for wm in weak}


def get_recent_exercise_ids(db, student_id, n=5) -> set:
    """Return IDs of the last n exercises this student did."""
    from app.models.session import Session as SessionModel
    recent = (
        db.query(SessionModel.exercise_id)
        .filter(SessionModel.student_id == student_id)
        .order_by(SessionModel.started_at.desc())
        .limit(n)
        .all()
    )
    return {row.exercise_id for row in recent}


def weighted_choice(pools: list):
    """
    Pick one exercise from weighted pools.
    pools = [(list_of_exercises, weight), ...]
    Skips empty pools and redistributes weight automatically.
    """
    non_empty = [(pool, weight) for pool, weight in pools if pool]
    if not non_empty:
        return None

    total = sum(w for _, w in non_empty)
    rand  = random.uniform(0, total)
    cumulative = 0.0
    for pool, weight in non_empty:
        cumulative += weight
        if rand <= cumulative:
            return random.choice(pool)
    return random.choice(non_empty[-1][0])


@router.get("/next", response_model=ExerciseResponse)
def get_next_exercise(student_id: uuid.UUID, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    level        = student.difficulty_level
    weak_words   = get_weak_words(db, student_id)
    recent_ids   = get_recent_exercise_ids(db, student_id, n=5)

    all_at_level = db.query(Exercise).filter(
        Exercise.difficulty == level
    ).all()

    # exercises not seen recently
    fresh_at_level = [e for e in all_at_level if e.id not in recent_ids]

    # exercises that contain at least one weak word
    struggle_pool = [
        e for e in fresh_at_level
        if any(w in weak_words for w in (e.target_words or []))
    ]

    # exercises at current level with no weak word overlap (consolidation)
    level_pool = [e for e in fresh_at_level if e not in struggle_pool]

    # stretch — one level above
    stretch_pool = db.query(Exercise).filter(
        Exercise.difficulty == level + 1
    ).all()

    # 60% struggle, 30% current level, 10% stretch
    chosen = weighted_choice([
        (struggle_pool, 0.6),   
        (level_pool,    0.3),
        (stretch_pool,  0.1),
    ])

    # fallback — if all pools empty just return anything at level
    if not chosen:
        chosen = random.choice(all_at_level) if all_at_level else None

    if not chosen:
        raise HTTPException(status_code=404, detail="No exercises found for this student")

    chosen.times_served += 1
    db.commit()
    return chosen


@router.get("/{exercise_id}", response_model=ExerciseResponse)
def get_exercise(exercise_id: uuid.UUID, db: Session = Depends(get_db)):
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ex


@router.post("/generate")
def generate_for_student(student_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Generate new exercises using Gemini targeting this student's weak words.
    Call this when the exercise bank is running low for a student.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    weak_words = list(get_weak_words(db, student_id))
    if not weak_words:
        return {"message": "No weak words found. Student is doing well!", "generated": 0}

    exercises = llm_generate(
        weak_words  = weak_words,
        difficulty  = student.difficulty_level,
        student_age = student.age or 10,
        count       = 5
    )

    if not exercises:
        return {"message": "Generation failed", "generated": 0}

    new_exercises = []
    for ex in exercises:
        new_ex = Exercise(
            type         = ex["type"],
            content      = ex["content"],
            expected     = ex["expected"],
            target_words = ex["target_words"],
            difficulty   = student.difficulty_level,
            age_group    = "all",
            source       = "ai_generated"
        )
        db.add(new_ex)
        new_exercises.append(new_ex)

    db.commit()

    return {
        "message":   f"Generated {len(new_exercises)} new exercises",
        "generated": len(new_exercises),
        "exercises": [
            {
                "type":         e.type,
                "content":      e.content,
                "target_words": e.target_words
            }
            for e in new_exercises
        ]
    }