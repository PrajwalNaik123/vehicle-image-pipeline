import cv2

# Below this Laplacian variance, an image is considered blurry.
# Tuned loosely against typical phone photos -- not a calibrated threshold,
# see README trade-offs section.
BLUR_THRESHOLD = 100.0


def check_blur(image_path: str) -> dict:
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return {
            "check_name": "blur_detection",
            "passed": False,
            "confidence": 1.0,
            "detail": "Could not read image for blur analysis (unsupported or corrupt file).",
        }

    variance = cv2.Laplacian(img, cv2.CV_64F).var()
    is_blurry = variance < BLUR_THRESHOLD

    # Map variance to a rough confidence: far from the threshold = more confident.
    distance = abs(variance - BLUR_THRESHOLD)
    confidence = min(0.99, 0.5 + distance / (BLUR_THRESHOLD * 2))

    return {
        "check_name": "blur_detection",
        "passed": not is_blurry,
        "confidence": round(confidence, 2),
        "detail": f"Laplacian variance={variance:.1f} (threshold={BLUR_THRESHOLD}). "
                  f"{'Image appears blurry.' if is_blurry else 'Image appears sharp.'}",
    }
