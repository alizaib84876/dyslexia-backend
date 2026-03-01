# Dyslexia Support System — Exercise Backend API

A fully adaptive exercise backend for dyslexic children. Handles exercise delivery,
scoring, word mastery tracking, difficulty adjustment, LLM feedback, and exercise generation.

---

## Requirements

Make sure you have these installed on your machine before starting:

- Python 3.9 or higher — https://www.python.org/downloads/
- Docker Desktop — https://www.docker.com/products/docker-desktop/
- Git — https://git-scm.com

---

## Step 1 — Clone the Repository

Open Terminal and run:
```bash
git clone https://github.com/alizaib84876/dyslexia-backend.git
cd dyslexia-backend
```

---

## Step 2 — Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see (venv) at the start of your terminal line.

---

## Step 3 — Install All Dependencies
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic \
            python-dotenv python-Levenshtein pytest httpx pydantic groq
```

---

## Step 4 — Create Your .env File

Create a file called `.env` in the project root (same folder as this README):
```
DATABASE_URL=postgresql://dev:devpass@localhost:5432/dyslexia_db
GROQ_API_KEY=your_groq_api_key_here
```

To get your free Groq API key:
1. Go to https://console.groq.com
2. Sign up with Google
3. Click API Keys and create a new key
4. Paste it in the .env file above

---

## Step 5 — Start the Database

Make sure Docker Desktop is open and running, then run:
```bash
docker run --name dyslexia-db \
  -e POSTGRES_DB=dyslexia_db \
  -e POSTGRES_USER=dev \
  -e POSTGRES_PASSWORD=devpass \
  -p 5432:5432 \
  -d postgres:15
```

Verify it is running:
```bash
docker ps
```

You should see a row with postgres:15 and status Up.

Note: You only need to run the docker run command once ever.
After that, to start the database again after a reboot just run:
```bash
docker start dyslexia-db
```

---

## Step 6 — Seed Exercise Data

This inserts 30 pre-built exercises into the database:
```bash
python db/seed.py
```

You should see: Seeded 30 exercises successfully.

Note: Only run this once. Running it again will clear and re-seed the database.

---

## Step 7 — Start the Server
```bash
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## Step 8 — Open API Docs

Open this in your browser:
```
http://127.0.0.1:8000/docs
```

You will see all endpoints with full request and response formats.
You can test every endpoint directly from this page.

---

## Every Time You Restart Your Laptop

Run these 3 commands in order:
```bash
docker start dyslexia-db
cd path/to/dyslexia-backend
source venv/bin/activate
uvicorn app.main:app --reload
```

---

## API Endpoints — Quick Reference

### Students

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /students/ | Create a new student |
| GET | /students/{id} | Get student profile |
| GET | /students/{id}/mastery | Get word mastery list |
| GET | /students/{id}/stats | Get full progress report |

### Exercises

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /exercises/ | List all exercises |
| GET | /exercises/next?student_id=X | Get next adaptive exercise |
| GET | /exercises/{id} | Get single exercise |
| POST | /exercises/generate?student_id=X | Generate new exercises via AI |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /sessions/ | Start a session |
| POST | /sessions/{id}/submit | Submit answer and get score |

---

## Integration Flow

This is the exact order your frontend should call the API:

1. Create a student once and save the student_id
2. Call GET /exercises/next?student_id=X to get an exercise
3. Show the exercise content field to the student
4. When student submits, call POST /sessions/ to start a session
5. Call POST /sessions/{id}/submit with the student response
6. Display the score and feedback returned
7. Repeat from step 2 for the next exercise
8. Call GET /students/{id}/stats anytime for dashboard data

---

## Request and Response Examples

### Create Student
```
POST /students/
{
  "name": "Ali",
  "age": 10
}

Response:
{
  "id": "b01c56ba-...",
  "name": "Ali",
  "age": 10,
  "difficulty_level": 1,
  "total_sessions": 0,
  "streak_days": 0
}
```

### Get Next Exercise
```
GET /exercises/next?student_id=b01c56ba-...

Response:
{
  "id": "df90b771-...",
  "type": "word_typing",
  "content": "Type this word: cat",
  "expected": "cat",
  "target_words": ["cat"],
  "difficulty": 1,
  "age_group": "5-7",
  "source": "pre_stored"
}
```

### Start Session
```
POST /sessions/
{
  "student_id": "b01c56ba-...",
  "exercise_id": "df90b771-...",
  "is_handwriting": false
}

Response:
{
  "session_id": "2164f8e8-...",
  "expected": "cat"
}
```

### Submit Answer
```
POST /sessions/2164f8e8-.../submit
{
  "student_response": "kat",
  "duration_seconds": 15
}

Response:
{
  "session_id": "2164f8e8-...",
  "score": 0.667,
  "char_errors": [
    {
      "position": 0,
      "expected_char": "c",
      "actual_char": "k",
      "error_type": "substitution"
    }
  ],
  "phonetic_score": 1.0,
  "feedback": "Good effort! The letter 'c' can sometimes sound like 'k', you are thinking like a great speller. Keep going, you are doing amazing!",
  "new_difficulty_level": 1,
  "words_updated": ["cat"]
}
```

### Get Student Stats
```
GET /students/b01c56ba-.../stats

Response:
{
  "student_id": "b01c56ba-...",
  "student_name": "Ali",
  "current_difficulty": 2,
  "total_sessions": 5,
  "average_score": 0.743,
  "score_trend": [0.667, 0.834, 0.834, 0.834],
  "words_mastered": ["cat"],
  "words_struggling": ["dog"],
  "total_words_practiced": 2,
  "top_confusion_pairs": [
    {"pattern": "a -> o", "count": 3}
  ],
  "accuracy_by_type": {
    "word_typing": 0.743
  }
}
```

---

## Notes for Frontend Integration

- The content field in the exercise is what you show to the student
- The expected field is the correct answer — do not show this to the student
- score is between 0.0 and 1.0 — multiply by 100 for percentage
- feedback is a ready-to-display string — show it directly to the student
- new_difficulty_level tells you the student's current level after this session
- For handwriting exercises set is_handwriting to true in the session and pass ocr_confidence in the submit
- Call GET /exercises/generate?student_id=X when you want fresh AI-generated exercises for a student