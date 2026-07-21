import io

import numpy as np
from PIL import Image as PILImage

ELA_QUALITY = 90
# Above this, treat as suspicious. Threshold picked empirically/loosely --
# ELA is a classic but noisy heuristic, not a certainty. See README trade-offs.
ELA_MEAN_THRESHOLD = 8.0


def check_tamper(image_path: str) -> dict:
    """
    Error Level Analysis: re-compress the image at a fixed JPEG quality and
    diff against the original. Regions that were edited after the last save
    tend to show a different (usually higher) error level than the rest of
    the image. This is a classic, cheap heuristic -- not forensic-grade.
    """
    try:
        original = PILImage.open(image_path).convert("RGB")
    except Exception as exc:
        return {
            "check_name": "tamper_heuristic",
            "passed": True,
            "confidence": 0.2,
            "detail": f"Could not open image for ELA ({exc}); defaulting to pass with low confidence.",
        }

    buffer = io.BytesIO()
    original.save(buffer, "JPEG", quality=ELA_QUALITY)
    buffer.seek(0)
    recompressed = PILImage.open(buffer).convert("RGB")

    diff = np.abs(np.asarray(original, dtype=np.int16) - np.asarray(recompressed, dtype=np.int16))
    mean_error = float(diff.mean())
    max_region_error = float(diff.max())

    is_suspicious = mean_error > ELA_MEAN_THRESHOLD

    confidence = min(0.9, 0.4 + abs(mean_error - ELA_MEAN_THRESHOLD) / (ELA_MEAN_THRESHOLD * 2))

    return {
        "check_name": "tamper_heuristic",
        "passed": not is_suspicious,
        "confidence": round(confidence, 2),
        "detail": f"ELA mean error={mean_error:.2f}, max={max_region_error:.0f} (threshold={ELA_MEAN_THRESHOLD}). "
                  f"{'Elevated compression-error pattern -- possible editing.' if is_suspicious else 'No strong tampering signal.'}",
    }
