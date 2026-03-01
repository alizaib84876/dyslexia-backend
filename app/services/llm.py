import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"


def generate_feedback(
    score: float,
    char_errors: list,
    target_words: list,
    student_age: int,
    exercise_type: str
) -> str:
    """
    Generate encouraging, age-appropriate feedback using Groq.
    Falls back to simple template if API call fails.
    """
    error_summary = ""
    if char_errors:
        reversals = [e for e in char_errors if e.get("error_type") == "reversal"]
        subs      = [e for e in char_errors if e.get("error_type") == "substitution"]

        if reversals:
            pairs = ", ".join(
                f"'{e['actual_char']}' instead of '{e['expected_char']}'"
                for e in reversals[:3]
            )
            error_summary += f"Letter reversals: {pairs}. "

        if subs:
            pairs = ", ".join(
                f"'{e['actual_char']}' instead of '{e['expected_char']}'"
                for e in subs[:3]
            )
            error_summary += f"Letter substitutions: {pairs}. "

    score_percent = round(score * 100)
    words_str     = ", ".join(target_words) if target_words else "the exercise"

    prompt = f"""You are a warm, encouraging teacher helping a child aged {student_age} who has dyslexia.
The child just completed a {exercise_type} exercise practicing these words: {words_str}.
Their score was {score_percent}%.
{f"Errors made: {error_summary}" if error_summary else "They made no errors."}

Write short feedback in exactly 3 sentences:
1. Acknowledge their score warmly and positively
2. Give one specific, gentle tip about their mistake if they made one, or praise their accuracy if they did not
3. Encourage them to keep going with energy

Rules:
- Never use the word dyslexia
- Use simple words a {student_age} year old understands
- Be warm, specific, and motivating
- Do not use bullet points or numbering in your response
- Maximum 60 words total
- Return plain text only, no formatting"""

    try:
        response = client.chat.completions.create(
            model    = MODEL,
            messages = [{"role": "user", "content": prompt}],
            max_tokens = 120,
            temperature = 0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Feedback generation failed: {e}")
        if score >= 0.8:
            return "Great work! You are doing really well. Keep it up!"
        elif score >= 0.5:
            return "Good effort! Every practice session makes you stronger. Keep going!"
        else:
            return "Keep trying! Hard work always pays off. You are doing great!"


def generate_exercises(
    weak_words: list,
    difficulty: int,
    student_age: int,
    count: int = 5
) -> list:
    """
    Generate new exercises targeting weak words using Groq.
    Returns a list of exercise dicts ready to insert into the database.
    """
    if not weak_words:
        return []

    words_str = ", ".join(weak_words[:8])

    prompt = f"""You are creating spelling exercises for a child aged {student_age} with dyslexia.
Difficulty level is {difficulty} out of 10.
These are words the child struggles with: {words_str}

Generate {count} exercises. Return ONLY a JSON array, no explanation, no markdown, no code blocks.
Each item must have exactly these fields:
- type: either "word_typing" or "sentence_typing"
- content: the instruction shown to the student
- expected: the exact correct answer in lowercase
- target_words: array of focus words from the struggle list used in this exercise

Rules:
- For word_typing: content = "Type this word: WORD", expected = the word in lowercase
- For sentence_typing: content = "Type this sentence: SENTENCE", expected = sentence in lowercase
- Sentences must be simple, short, and use the struggle words naturally
- Mix word_typing and sentence_typing
- All expected values must be lowercase

Example format:
[
  {{"type": "word_typing", "content": "Type this word: friend", "expected": "friend", "target_words": ["friend"]}},
  {{"type": "sentence_typing", "content": "Type this sentence: my friend went to school", "expected": "my friend went to school", "target_words": ["friend", "school"]}}
]"""

    try:
        response = client.chat.completions.create(
            model    = MODEL,
            messages = [{"role": "user", "content": prompt}],
            max_tokens  = 800,
            temperature = 0.7
        )
        text = response.choices[0].message.content.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        exercises = json.loads(text)

        valid = []
        for ex in exercises:
            if all(k in ex for k in ["type", "content", "expected", "target_words"]):
                valid.append(ex)
        return valid

    except Exception as e:
        print(f"Exercise generation failed: {e}")
        return []