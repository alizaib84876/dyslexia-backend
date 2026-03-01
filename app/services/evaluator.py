import Levenshtein
import re

def normalize(text: str) -> str:
    """Lowercase, remove punctuation, strip extra spaces."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

def get_char_errors(expected: str, actual: str) -> list:
    """Return list of character-level errors with position and type."""
    ops = Levenshtein.editops(actual, expected)
    errors = []
    for op, src_pos, dest_pos in ops:
        expected_char = expected[dest_pos] if dest_pos < len(expected) else ""
        actual_char   = actual[src_pos]   if src_pos  < len(actual)   else ""

        if op == "replace":
            error_type = "substitution"
            # detect common dyslexia reversals
            pair = tuple(sorted([expected_char, actual_char]))
            if pair in [("b","d"), ("p","q"), ("b","p"), ("d","q"), ("n","u"), ("m","w")]:
                error_type = "reversal"
        elif op == "delete":
            error_type = "insertion"   # student inserted an extra char
        elif op == "insert":
            error_type = "omission"    # student omitted a char

        errors.append({
            "position":      dest_pos,
            "expected_char": expected_char,
            "actual_char":   actual_char,
            "error_type":    error_type
        })
    return errors

def simple_phonetic(word: str) -> str:
    """Very simple phonetic normalization for partial credit."""
    word = word.lower()
    word = re.sub(r"ph", "f", word)
    word = re.sub(r"ck", "k", word)
    word = re.sub(r"gh", "", word)
    word = re.sub(r"kn", "n", word)
    word = re.sub(r"wr", "r", word)
    word = re.sub(r"[aeiou]+", "a", word)  # collapse vowels
    return word

def compute_phonetic_score(expected: str, actual: str) -> float:
    """Score based on phonetic similarity — rewards correct sound even if spelling differs."""
    exp_words = expected.split()
    act_words = actual.split()
    if not exp_words:
        return 1.0

    total = 0.0
    for i, exp_word in enumerate(exp_words):
        act_word = act_words[i] if i < len(act_words) else ""
        exp_phon = simple_phonetic(exp_word)
        act_phon = simple_phonetic(act_word)
        dist     = Levenshtein.distance(exp_phon, act_phon)
        max_len  = max(len(exp_phon), len(act_phon), 1)
        total   += 1.0 - (dist / max_len)

    return round(total / len(exp_words), 3)

def evaluate_response(
    expected:       str,
    actual:         str,
    is_handwriting: bool  = False,
    ocr_confidence: float = 1.0
) -> dict:
    """
    Main evaluation function.
    Returns score, char_errors, phonetic_score.
    """
    # For handwriting with low OCR confidence, be more lenient
    confidence_threshold = 0.75
    if is_handwriting and ocr_confidence and ocr_confidence < confidence_threshold:
        # give partial benefit of the doubt — use phonetic score as main signal
        phonetic = compute_phonetic_score(normalize(expected), normalize(actual))
        return {
            "score":         round(phonetic * 0.9, 3),  # slight penalty for uncertainty
            "char_errors":   [],
            "phonetic_score": phonetic,
            "note":          "Low OCR confidence — scored on phonetic similarity"
        }

    exp_norm = normalize(expected)
    act_norm = normalize(actual)

    # character-level score
    dist    = Levenshtein.distance(exp_norm, act_norm)
    max_len = max(len(exp_norm), len(act_norm), 1)
    score   = round(1.0 - (dist / max_len), 3)

    char_errors   = get_char_errors(exp_norm, act_norm)
    phonetic_score = compute_phonetic_score(exp_norm, act_norm)

    # if phonetically correct but spelled wrong, boost score slightly
    if phonetic_score > 0.85 and score < phonetic_score:
        score = round((score + phonetic_score) / 2, 3)

    return {
        "score":          max(0.0, min(1.0, score)),
        "char_errors":    char_errors,
        "phonetic_score": phonetic_score
    }