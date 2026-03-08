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
            python-dotenv python-Levenshtein pytest httpx pydantic groq \
            transformers torch Pillow python-multipart
```

> **Note:** `transformers` and `torch` are required for the handwriting OCR feature (TrOCR Large model). The first time a handwriting image is submitted the model (~2.2 GB) will be downloaded automatically from HuggingFace and cached on disk. This only happens once.

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

This inserts 41 pre-built exercises into the database:
```bash
python db/seed.py
```

You should see: Seeded 41 exercises successfully.

> **Note:** Running seed again will wipe all existing sessions and exercises and re-insert them from scratch. Only run it again if you want a clean slate.

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

> **Note on handwriting:** The TrOCR Large OCR model is loaded on the first handwriting request (not at startup). Expect a 15–20 second delay on that first request while the model loads into memory. Every subsequent request is fast.

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
| POST | /sessions/{id}/submit | Submit typed answer and get score |
| POST | /sessions/{id}/submit-handwriting | Submit handwriting image and get score |

---

## Exercise Types

Every exercise has a `type` field. The frontend must check this to decide what UI to show:

| type | What the student does | Submit endpoint |
|------|-----------------------|-----------------|
| `word_typing` | Types a word into a text box | `/sessions/{id}/submit` |
| `sentence_typing` | Types a sentence into a text box | `/sessions/{id}/submit` |
| `handwriting` | Writes on paper, you photograph it | `/sessions/{id}/submit-handwriting` |

Both `word_typing` and `sentence_typing` use the same typed submit endpoint.
Only `handwriting` uses the image upload endpoint.

All three types go through the same adaptive selection, word mastery tracking, difficulty adjustment, and LLM feedback pipeline — handwriting is not treated differently by the backend except for how the answer is received (image vs text).

### How handwriting exercises are created

- **Pre-seeded:** 13 handwriting exercises covering difficulty levels 1–6 are already in the database from seed
- **AI-generated:** Calling `POST /exercises/generate?student_id=X` uses the LLM to generate new exercises targeting the student's weak words — it generates a mix of all 3 types including handwriting, always as short single-line sentences (max 5 words) so OCR can read them accurately

---

## Integration Flow

### Typed Exercise Flow

1. Create a student once and save the student_id
2. Call GET /exercises/next?student_id=X to get an exercise
3. Show the exercise content field to the student
4. When student submits, call POST /sessions/ to start a session (set `is_handwriting: false`)
5. Call POST /sessions/{id}/submit with the student's typed response
6. Display the score and feedback returned
7. Repeat from step 2 for the next exercise
8. Call GET /students/{id}/stats anytime for dashboard data

### Handwriting Exercise Flow

1. Create a student once and save the student_id
2. Call GET /exercises/next?student_id=X to get an exercise
3. Show the exercise content field to the student
4. When student submits, call POST /sessions/ to start a session — set `is_handwriting: true`
5. Capture a photo or scan of the student's handwriting as a JPG or PNG file
6. Send it to POST /sessions/{id}/submit-handwriting as a multipart form upload (field name: `file`)
7. The backend runs OCR automatically, scores the result, and returns the same rich response plus `ocr_text` and `ocr_confidence`
8. Display the score, feedback, and optionally `ocr_text` so the student can see what the app read
9. Repeat from step 2 for the next exercise

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

Response (typed example):
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

Response (handwriting example):
{
  "id": "9fa329b1-...",
  "type": "handwriting",
  "content": "Write this word: ran",
  "expected": "ran",
  "target_words": ["ran"],
  "difficulty": 1,
  "age_group": "5-7",
  "source": "ai_generated"
}
```

> Check the `type` field first. If `type == "handwriting"`, show a camera/photo input and use the `submit-handwriting` endpoint. Otherwise show a text input and use the `submit` endpoint.

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

### Submit Handwriting Image
```
POST /sessions/36aee7e0-.../submit-handwriting
Content-Type: multipart/form-data

Fields:
  file             — JPG or PNG image of the student's handwriting (required)
  duration_seconds — how long the student took in seconds (optional, integer)
```

Example — student was asked to write **"ran"** but wrote **"ranch"**:
```json
{
  "session_id": "36aee7e0-...",
  "score": 0.6,
  "char_errors": [
    {"position": 3, "expected_char": "", "actual_char": "c", "error_type": "insertion"},
    {"position": 3, "expected_char": "", "actual_char": "h", "error_type": "insertion"}
  ],
  "phonetic_score": 0.6,
  "feedback": "You did great, 60% is awesome. I'm so proud you got the core letters right. Keep practicing!",
  "new_difficulty_level": 1,
  "words_updated": ["ran"],
  "ocr_text": "Ranch",
  "ocr_confidence": 0.777
}
```

> `ocr_text` — what the OCR engine read from the image. You can show this to the student so they know what was recognised.
> `ocr_confidence` — model confidence 0–1, for reference only. Scoring is done purely on the OCR text vs the expected answer.
> `char_errors` — exact character-level diff, same as typed exercises. Here `c` and `h` were extra insertions beyond "ran".

---

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

- The `content` field in the exercise is what you show to the student
- The `expected` field is the correct answer — do not show this to the student
- `score` is between 0.0 and 1.0 — multiply by 100 for percentage
- `feedback` is a ready-to-display string — show it directly to the student
- `new_difficulty_level` tells you the student's current level after this session
- Call `GET /exercises/generate?student_id=X` when you want fresh AI-generated exercises for a student

### Handwriting-specific notes

- Set `is_handwriting: true` when calling `POST /sessions/` for a handwriting exercise
- Use `POST /sessions/{id}/submit-handwriting` (not `/submit`) for handwriting exercises — it accepts an image, not text
- Send the image as a `multipart/form-data` upload with the field name `file` (JPG or PNG only)
- The backend runs TrOCR OCR automatically — you never send the transcribed text, only the raw image
- `ocr_text` in the response shows what the OCR engine read — you can display this to the student so they know what was recognised
- The first handwriting submission after server start will be slower (~15–20 s) as the OCR model loads; all subsequent submissions are fast
- Image quality tips for best OCR accuracy: good lighting, dark ink on white/light paper, write on a single line, keep the image reasonably cropped