import re

import pytesseract
from PIL import Image as PILImage

# Standard Indian registration format, e.g. "KA05MH1234" (state, RTO code,
# series letters, 4-digit number). Spaces/hyphens are stripped before matching.
PLATE_REGEX = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")


def _clean_candidate(raw_text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", raw_text.upper())


def check_plate(image_path: str) -> dict:
    try:
        img = PILImage.open(image_path)
        raw_text = pytesseract.image_to_string(img)
    except Exception as exc:
        return {
            "check_name": "plate_format_validation",
            "passed": False,
            "confidence": 0.3,
            "detail": f"OCR failed to run: {exc}",
        }

    candidates = [line.strip() for line in raw_text.splitlines() if line.strip()]
    cleaned_candidates = [_clean_candidate(c) for c in candidates]

    match = next((c for c in cleaned_candidates if PLATE_REGEX.match(c)), None)

    if match:
        return {
            "check_name": "plate_format_validation",
            "passed": True,
            "confidence": 0.8,
            "detail": f"Extracted plate '{match}' matches expected Indian format.",
        }

    if cleaned_candidates:
        return {
            "check_name": "plate_format_validation",
            "passed": False,
            "confidence": 0.5,
            "detail": f"OCR found text but nothing matched the expected plate format. "
                      f"Closest candidates: {cleaned_candidates[:3]}",
        }

    return {
        "check_name": "plate_format_validation",
        "passed": False,
        "confidence": 0.6,
        "detail": "OCR did not extract any readable text -- plate may be missing, "
                  "obscured, or image quality too low.",
    }
