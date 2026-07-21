import cv2

LOW_LIGHT_THRESHOLD = 60.0    # mean pixel value (0-255) below this = too dark
OVEREXPOSED_THRESHOLD = 220.0  # above this = likely overexposed / washed out


def check_brightness(image_path: str) -> dict:
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return {
            "check_name": "brightness_analysis",
            "passed": False,
            "confidence": 1.0,
            "detail": "Could not read image for brightness analysis.",
        }

    mean_val = float(img.mean())

    if mean_val < LOW_LIGHT_THRESHOLD:
        passed = False
        note = "Image appears too dark (low light)."
        distance = LOW_LIGHT_THRESHOLD - mean_val
    elif mean_val > OVEREXPOSED_THRESHOLD:
        passed = False
        note = "Image appears overexposed."
        distance = mean_val - OVEREXPOSED_THRESHOLD
    else:
        passed = True
        note = "Brightness is within acceptable range."
        distance = min(mean_val - LOW_LIGHT_THRESHOLD, OVEREXPOSED_THRESHOLD - mean_val)

    confidence = min(0.99, 0.5 + distance / 100)

    return {
        "check_name": "brightness_analysis",
        "passed": passed,
        "confidence": round(confidence, 2),
        "detail": f"Mean pixel value={mean_val:.1f} (dark<{LOW_LIGHT_THRESHOLD}, bright>{OVEREXPOSED_THRESHOLD}). {note}",
    }
