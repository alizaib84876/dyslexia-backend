import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
import app.models
from app.models.exercise import Exercise
from app.models.session import Session as SessionModel

def seed():
    db = SessionLocal()

    # Clear sessions first (they reference exercises via FK), then exercises
    db.query(SessionModel).delete()
    db.commit()
    db.query(Exercise).delete()
    db.commit()

    exercises = [

        # ── LEVEL 1-2 | word_typing ──────────────────────────────────────
        Exercise(type="word_typing", difficulty=1, age_group="5-7",
            content="Type this word: cat",
            expected="cat",
            target_words=["cat"]),

        Exercise(type="word_typing", difficulty=1, age_group="5-7",
            content="Type this word: bat",
            expected="bat",
            target_words=["bat"]),

        Exercise(type="word_typing", difficulty=1, age_group="5-7",
            content="Type this word: dog",
            expected="dog",
            target_words=["dog"]),

        Exercise(type="word_typing", difficulty=1, age_group="5-7",
            content="Type this word: run",
            expected="run",
            target_words=["run"]),

        Exercise(type="word_typing", difficulty=1, age_group="5-7",
            content="Type this word: sit",
            expected="sit",
            target_words=["sit"]),

        Exercise(type="word_typing", difficulty=2, age_group="5-7",
            content="Type this word: jump",
            expected="jump",
            target_words=["jump"]),

        Exercise(type="word_typing", difficulty=2, age_group="5-7",
            content="Type this word: play",
            expected="play",
            target_words=["play"]),

        Exercise(type="word_typing", difficulty=2, age_group="8-10",
            content="Type this word: ship",
            expected="ship",
            target_words=["ship"]),

        # ── LEVEL 1-2 | sentence_typing ──────────────────────────────────
        Exercise(type="sentence_typing", difficulty=1, age_group="5-7",
            content="Type this sentence: The cat sat on the mat",
            expected="the cat sat on the mat",
            target_words=["cat", "sat", "mat"]),

        Exercise(type="sentence_typing", difficulty=1, age_group="5-7",
            content="Type this sentence: The dog ran fast",
            expected="the dog ran fast",
            target_words=["dog", "ran", "fast"]),

        Exercise(type="sentence_typing", difficulty=2, age_group="5-7",
            content="Type this sentence: She can jump high",
            expected="she can jump high",
            target_words=["jump", "high"]),

        Exercise(type="sentence_typing", difficulty=2, age_group="8-10",
            content="Type this sentence: The big ship set sail",
            expected="the big ship set sail",
            target_words=["ship", "sail"]),

        # ── LEVEL 3-4 | word_typing ──────────────────────────────────────
        Exercise(type="word_typing", difficulty=3, age_group="8-10",
            content="Type this word: friend",
            expected="friend",
            target_words=["friend"]),

        Exercise(type="word_typing", difficulty=3, age_group="8-10",
            content="Type this word: people",
            expected="people",
            target_words=["people"]),

        Exercise(type="word_typing", difficulty=3, age_group="8-10",
            content="Type this word: school",
            expected="school",
            target_words=["school"]),

        Exercise(type="word_typing", difficulty=4, age_group="8-10",
            content="Type this word: because",
            expected="because",
            target_words=["because"]),

        Exercise(type="word_typing", difficulty=4, age_group="8-10",
            content="Type this word: enough",
            expected="enough",
            target_words=["enough"]),

        Exercise(type="word_typing", difficulty=4, age_group="8-10",
            content="Type this word: through",
            expected="through",
            target_words=["through"]),

        # ── LEVEL 3-4 | sentence_typing ──────────────────────────────────
        Exercise(type="sentence_typing", difficulty=3, age_group="8-10",
            content="Type this sentence: My friend came to school today",
            expected="my friend came to school today",
            target_words=["friend", "school", "today"]),

        Exercise(type="sentence_typing", difficulty=3, age_group="8-10",
            content="Type this sentence: People like to play outside",
            expected="people like to play outside",
            target_words=["people", "outside"]),

        Exercise(type="sentence_typing", difficulty=4, age_group="8-10",
            content="Type this sentence: She went to school because she loves learning",
            expected="she went to school because she loves learning",
            target_words=["school", "because", "learning"]),

        Exercise(type="sentence_typing", difficulty=4, age_group="8-10",
            content="Type this sentence: He ran fast enough to win the race",
            expected="he ran fast enough to win the race",
            target_words=["enough", "race"]),

        # ── LEVEL 5-6 | word_typing ──────────────────────────────────────
        Exercise(type="word_typing", difficulty=5, age_group="11-13",
            content="Type this word: necessary",
            expected="necessary",
            target_words=["necessary"]),

        Exercise(type="word_typing", difficulty=5, age_group="11-13",
            content="Type this word: beautiful",
            expected="beautiful",
            target_words=["beautiful"]),

        Exercise(type="word_typing", difficulty=6, age_group="11-13",
            content="Type this word: rhythm",
            expected="rhythm",
            target_words=["rhythm"]),

        Exercise(type="word_typing", difficulty=6, age_group="11-13",
            content="Type this word: necessary",
            expected="necessary",
            target_words=["necessary"]),

        # ── LEVEL 5-6 | sentence_typing ──────────────────────────────────
        Exercise(type="sentence_typing", difficulty=5, age_group="11-13",
            content="Type this sentence: It is necessary to study every day",
            expected="it is necessary to study every day",
            target_words=["necessary", "study", "every"]),

        Exercise(type="sentence_typing", difficulty=6, age_group="11-13",
            content="Type this sentence: The beautiful rhythm of the music filled the room",
            expected="the beautiful rhythm of the music filled the room",
            target_words=["beautiful", "rhythm", "music"]),

        # ── HANDWRITING | difficulty 1 ───────────────────────────────────
        Exercise(type="handwriting", difficulty=1, age_group="5-7",
            content="Write this sentence: The cat sat on the mat",
            expected="the cat sat on the mat",
            target_words=["cat", "sat", "mat"],
            source="pre_stored"),

        Exercise(type="handwriting", difficulty=1, age_group="5-7",
            content="Write this sentence: The dog ran fast",
            expected="the dog ran fast",
            target_words=["dog", "ran", "fast"],
            source="pre_stored"),

        # ── HANDWRITING | difficulty 2 ───────────────────────────────────
        Exercise(type="handwriting", difficulty=2, age_group="5-7",
            content="Write this sentence: I like to jump and play",
            expected="i like to jump and play",
            target_words=["jump", "play"],
            source="pre_stored"),

        Exercise(type="handwriting", difficulty=2, age_group="8-10",
            content="Write this sentence: The big ship set sail",
            expected="the big ship set sail",
            target_words=["ship", "sail"],
            source="pre_stored"),

        # ── HANDWRITING | difficulty 3 ───────────────────────────────────
        Exercise(type="handwriting", difficulty=3, age_group="8-10",
            content="Write this sentence: My friend came to school today",
            expected="my friend came to school today",
            target_words=["friend", "school", "today"],
            source="pre_stored"),

        Exercise(type="handwriting", difficulty=3, age_group="8-10",
            content="Write this sentence: Many people like to play outside",
            expected="many people like to play outside",
            target_words=["people", "outside"],
            source="pre_stored"),

        # ── HANDWRITING | difficulty 4 ───────────────────────────────────
        Exercise(type="handwriting", difficulty=4, age_group="8-10",
            content="Write this sentence: She ran fast enough to win the race",
            expected="she ran fast enough to win the race",
            target_words=["enough", "race"],
            source="pre_stored"),

        Exercise(type="handwriting", difficulty=4, age_group="8-10",
            content="Write this sentence: He went through the door because he was late",
            expected="he went through the door because he was late",
            target_words=["through", "because"],
            source="pre_stored"),

        # ── HANDWRITING | difficulty 5 ───────────────────────────────────
        Exercise(type="handwriting", difficulty=5, age_group="11-13",
            content="Write this sentence: It is necessary to study every day",
            expected="it is necessary to study every day",
            target_words=["necessary", "study"],
            source="pre_stored"),

        Exercise(type="handwriting", difficulty=5, age_group="11-13",
            content="Write this sentence: She wore a beautiful dress to school",
            expected="she wore a beautiful dress to school",
            target_words=["beautiful", "school"],
            source="pre_stored"),

        # ── HANDWRITING | difficulty 6 ───────────────────────────────────
        Exercise(type="handwriting", difficulty=6, age_group="11-13",
            content="Write this sentence: The beautiful rhythm of the music filled the room",
            expected="the beautiful rhythm of the music filled the room",
            target_words=["beautiful", "rhythm", "music"],
            source="pre_stored"),
    ]

    db.add_all(exercises)
    db.commit()
    db.close()
    print(f"Seeded {len(exercises)} exercises successfully.")

if __name__ == "__main__":
    seed()