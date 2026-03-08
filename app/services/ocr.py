"""
OCR service — Microsoft TrOCR Large (handwritten).

Uses `microsoft/trocr-large-handwritten` via Hugging Face Transformers.
Preprocessing: convert to grayscale only.

Drop-in replaceable: swap `run_ocr()` with any other OCR backend
— nothing else in the pipeline changes.
"""

import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
from io import BytesIO

# ── Model loading (lazy singleton) ────────────────────────────────────
_processor = None
_model     = None
MODEL_NAME = "microsoft/trocr-large-handwritten"


def _load_model():
    """Load TrOCR Large once and cache in module globals."""
    global _processor, _model
    if _processor is None:
        print(f"Loading TrOCR model: {MODEL_NAME} ...")
        _processor = TrOCRProcessor.from_pretrained(MODEL_NAME)
        _model     = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
        _model.eval()
        print("TrOCR model loaded.")


# ── Main OCR function ────────────────────────────────────────────────

def run_ocr(image_bytes: bytes) -> dict:
    """
    Run TrOCR Large on a single-line handwriting image.

    Pipeline: grayscale → RGB (3-channel) → infer.

    Returns
    -------
    dict with keys:
        text           – extracted string (stripped)
        confidence     – average token-level confidence (0-1)
        raw_confidence – same value × 100
    """
    _load_model()

    raw_image = Image.open(BytesIO(image_bytes))
    gray      = raw_image.convert("L")       # grayscale
    processed = gray.convert("RGB")          # model expects 3 channels

    pixel_values = _processor(
        images=processed, return_tensors="pt"
    ).pixel_values

    with torch.no_grad():
        outputs = _model.generate(
            pixel_values,
            max_new_tokens=128,
            output_scores=True,
            return_dict_in_generate=True,
        )

    import re
    text = _processor.batch_decode(
        outputs.sequences, skip_special_tokens=True
    )[0].strip()
    # Remove trailing punctuation/spaces that are OCR artifacts, not student mistakes
    text = re.sub(r"[\s\.\,\!\?\;]+$", "", text).strip()

    confidence = 0.0
    if outputs.scores:
        probs = [
            torch.softmax(score, dim=-1).max().item()
            for score in outputs.scores
        ]
        confidence = round(sum(probs) / len(probs), 3) if probs else 0.0

    return {
        "text":           text,
        "confidence":     confidence,
        "raw_confidence": round(confidence * 100, 1),
    }
