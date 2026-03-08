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

This inserts 54 pre-built exercises into the database:
```bash
python db/seed.py
```

You should see: Seeded 54 exercises successfully.

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
| GET | /exercises/next?student_id=X | Get next adaptive exercise (add `&type=X` to filter by type) |
| GET | /exercises/{id} | Get single exercise |
| POST | /exercises/generate?student_id=X | Generate new AI exercises (add `&type=X` to force a single type) |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /sessions/ | Start a session |
| POST | /sessions/{id}/submit | Submit typed answer and get score |
| POST | /sessions/{id}/submit-handwriting | Submit handwriting image and get score |
| POST | /sessions/{id}/submit-tracing | Submit tracing result and get score |

---

## Exercise Types

Every exercise has a `type` field. The frontend must check this to decide what UI to show:

| type | Scope | What the student does | Submit endpoint |
|------|-------|-----------------------|-----------------|
| `word_typing` | word, sentence | Types a word or sentence into a text box | `/sessions/{id}/submit` |
| `sentence_typing` | word, sentence | Types a word or sentence into a text box | `/sessions/{id}/submit` |
| `handwriting` | word, sentence | Writes a word or sentence on paper, you photograph it | `/sessions/{id}/submit-handwriting` |
| `tracing` | letter, word | Traces a letter or word on screen canvas | `/sessions/{id}/submit-tracing` |

Both `word_typing` and `sentence_typing` use the same typed submit endpoint — they cover words and sentences.
`handwriting` covers words and sentences — same scope as typing but answered by photograph.
`tracing` covers letters and words only (never sentences) — answered by stroke data from the frontend canvas.
Only `tracing` uses the `submit-tracing` endpoint — **the frontend computes the score and sends it; the backend does not evaluate strokes.**

All four types go through the same adaptive selection, word mastery tracking, difficulty adjustment, and LLM feedback pipeline.

---

## Adaptive Exercise Selection

Every call to `GET /exercises/next` runs a weighted random selection. The weights depend on whether a `?type=` filter is provided and whether the student has repeated letter-confusion errors.

### Without `?type=` filter (default — mixed types)

The backend scans the student's last 20 sessions for character errors classified as `reversal` or `substitution` (e.g. confusing `b` and `d`). Any letter that appears 2 or more times in those errors is classified as a **confused letter**.

**If confused letters are found:**

| Pool | Weight | What's in it |
|------|--------|--------------|
| Struggle pool | 50% | Exercises whose `target_words` contain words the student scores below 70% on |
| Letter-tracing pool | 20% | Tracing exercises whose `expected` value is one of the confused letters |
| Level pool | 20% | Any exercise at the student's current difficulty level |
| Stretch pool | 10% | Exercises one level above the student's current level |

**If no confused letters are found:**

| Pool | Weight | What's in it |
|------|--------|--------------|
| Struggle pool | 60% | Exercises whose `target_words` contain words the student scores below 70% on |
| Level pool | 30% | Any exercise at the student's current difficulty level |
| Stretch pool | 10% | Exercises one level above the student's current level |

### With `?type=X` filter

All pools are restricted to exercises of that type only. The confused-letter cross-type injection is skipped (since you already specified the type). Selection uses the 60%/30%/10% split within that type.

Supported type values: `word_typing`, `sentence_typing`, `handwriting`, `tracing`

**Example calls:**
```
GET /exercises/next?student_id=b01c56ba-...              # mixed adaptive
GET /exercises/next?student_id=b01c56ba-...&type=tracing # tracing only
GET /exercises/next?student_id=b01c56ba-...&type=handwriting # handwriting only
```

### AI exercise generation with type filter

`POST /exercises/generate?student_id=X` accepts the same `&type=X` parameter. When provided, the LLM is instructed to generate **only** that exercise type with strict rules (e.g. tracing = single letter or word only, handwriting = max 5 words). Without the parameter, the LLM generates a balanced mix of all four types.

**Example calls:**
```
POST /exercises/generate?student_id=b01c56ba-...              # mixed types
POST /exercises/generate?student_id=b01c56ba-...&type=tracing # tracing exercises only
```

> **Partner integration tip:** In screen flows where the student has already chosen an activity type (e.g. they tapped a "Tracing" button), always pass `&type=tracing` to both endpoints so they only receive exercises of that type. In the main adaptive flow where the app chooses for them, omit `?type=` so the backend can automatically inject letter-tracing exercises when confusion patterns are detected.

### Automatic exercise generation when a type has no targeted exercises

The seed database covers common words but cannot anticipate every weak word a student develops. If a student is struggling with a word (e.g. "friend") but no seeded exercises for that word exist in the requested type (e.g. `word_typing`), the struggle pool for that type would normally be empty.

**This gap is filled automatically.** When `?type=X` is passed and the struggle pool is empty despite the student having weak words, `/exercises/next` calls the LLM inline, generates 3 new exercises targeting those exact weak words in the requested type, saves them permanently to the database, and immediately serves one as the response. No extra API call from the frontend is needed.

- The inline generation only triggers when the gap is detected — it is not called on every request
- The generated exercises are stored permanently, so all future requests for that type hit the normal struggle pool (no LLM delay)
- The only observable effect is a small extra latency (~1–2 s) on that one request where the gap is first detected

### How handwriting exercises are created

- **Pre-seeded:** 13 handwriting exercises covering difficulty levels 1–6 are already in the database from seed
- **AI-generated:** Calling `POST /exercises/generate?student_id=X` uses the LLM to generate new exercises targeting the student's weak words — it generates a mix of all 4 types including handwriting and tracing

### Tracing exercises in detail

Tracing covers **letters and words only — never sentences.**

- **Letters** (difficulty 1–2): single letters the student confuses, e.g. `b`, `d`, `p`
- **Words** (difficulty 1–6): single words ranging from short to complex

The `content` field tells you exactly what to show:
- `"Trace this letter: b"` — show a single faint guide letter on canvas
- `"Trace this word: friend"` — show the full word as a faint guide path

The `expected` field is always a single letter or a single word (never a sentence).

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

### Tracing Exercise Flow

1. Create a student once and save the student_id
2. Call `GET /exercises/next?student_id=X` to get an exercise
3. Check the `type` field — if `type == "tracing"`, show the tracing canvas UI
4. Read `content` to know what to show: `"Trace this letter: b"` or `"Trace this word: cat"`
5. Render the letter/word as a faint dotted guide path on a canvas
6. The student traces over it with their finger (mobile) or mouse/stylus (web)
7. When they lift their finger/release the mouse, compute how closely their stroke matched the guide path — this gives you `trace_score` (0.0–1.0)
8. Optionally compute per-letter accuracy as a list of `stroke_errors`
9. Call `POST /sessions/ ` with `is_handwriting: false` to start a session
10. Call `POST /sessions/{id}/submit-tracing` with `trace_score`, `duration_seconds`, and optional `stroke_errors`
11. Display the score and feedback returned
12. Repeat from step 2 for the next exercise

**How to compute trace_score on the frontend:**
- Collect the student's drawn path as an array of `(x, y)` points
- Compare to your reference path for that letter/word using overlap percentage or path similarity
- A simple approach: divide the reference path into N evenly-spaced checkpoints, check what % of checkpoints have a drawn point within a threshold distance (e.g. 20px)
- That percentage is your `trace_score`
- For per-letter: segment the reference path by letter boundaries, compute the same per segment, report as `stroke_errors`
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
```
Or filter to one type:
```
GET /exercises/next?student_id=b01c56ba-...&type=tracing
```

```
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

Response (tracing example — auto-injected when student confuses b/d):
{
  "id": "c3b9f012-...",
  "type": "tracing",
  "content": "Trace this letter: b",
  "expected": "b",
  "target_words": ["b"],
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

### Submit Tracing Result
```
POST /sessions/abc123.../submit-tracing
Content-Type: application/json

{
  "trace_score": 0.82,
  "duration_seconds": 18,
  "stroke_errors": [
    {"letter": "b", "accuracy": 0.65},
    {"letter": "a", "accuracy": 0.95},
    {"letter": "t", "accuracy": 0.88}
  ]
}

Response:
{
  "session_id": "abc123-...",
  "score": 0.82,
  "stroke_errors": [
    {"letter": "b", "accuracy": 0.65},
    {"letter": "a", "accuracy": 0.95},
    {"letter": "t", "accuracy": 0.88}
  ],
  "feedback": "Great tracing! The letter 'b' needs a little more practice — try to follow the guide more slowly. Keep going, you are doing brilliant!",
  "new_difficulty_level": 1,
  "words_updated": ["bat"],
  "trace_score": 0.82
}
```

> `trace_score` — the value you computed on the frontend, echoed back for confirmation.
> `stroke_errors` — echoed back as stored. Send an empty list `[]` if you only have the overall score.
> `words_updated` — same as other exercise types, used for mastery tracking.

---

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
- `GET /students/{id}/stats` returns `accuracy_by_type` with a separate average score for each type: `word_typing`, `sentence_typing`, `handwriting`, `tracing` — use this to show per-type progress bars in your dashboard

### Handwriting-specific notes

- Set `is_handwriting: true` when calling `POST /sessions/` for a handwriting exercise
- Use `POST /sessions/{id}/submit-handwriting` (not `/submit`) for handwriting exercises — it accepts an image, not text
- Send the image as a `multipart/form-data` upload with the field name `file` (JPG or PNG only)
- The backend runs TrOCR OCR automatically — you never send the transcribed text, only the raw image
- `ocr_text` in the response shows what the OCR engine read — you can display this to the student so they know what was recognised
- The first handwriting submission after server start will be slower (~15–20 s) as the OCR model loads; all subsequent submissions are fast
- Image quality tips: good lighting, dark ink on white/light paper, single line, image reasonably cropped

### Tracing-specific notes

- Set `is_handwriting: false` when calling `POST /sessions/` for a tracing exercise (it is not a handwriting session)
- Use `POST /sessions/{id}/submit-tracing` — it accepts JSON, not an image
- **The backend does NOT evaluate stroke accuracy.** You must compute `trace_score` (0.0–1.0) on the frontend from the student's drawn path vs the reference path, then send it
- `stroke_errors` is optional but strongly recommended — send per-letter accuracy so the LLM can give specific feedback (e.g. "the letter b needs more practice")
- The `expected` field tells you exactly which letter or word to draw the guide path for
- `content` tells you the display instruction: `"Trace this letter: b"` or `"Trace this word: cat"`
- For letters, your guide path should be a single correctly-formed lowercase letter
- For words, your guide path should be the full word, with letter boundaries you can use to compute per-letter `stroke_errors`
- Threshold suggestion for scoring: student's drawn point within 15–25px of the nearest guide path point counts as correct; tune this for your canvas size