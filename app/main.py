from fastapi import FastAPI
from app.database import engine, Base
import app.models
from app.routers import students, exercises, sessions

app = FastAPI(title="Dyslexia Support API", version="1.0")

Base.metadata.create_all(bind=engine)

app.include_router(students.router)
app.include_router(exercises.router)
app.include_router(sessions.router)

@app.get("/")
def root():
    return {"status": "ok", "message": "Dyslexia Support API is running"}