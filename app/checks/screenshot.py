from PIL import Image as PILImage

# Common device/screen resolutions. A photo whose dimensions exactly match one
# of these, combined with missing camera EXIF data, is a strong screenshot signal.
COMMON_SCREEN_RESOLUTIONS = {
    (1080, 1920), (1920, 1080), (1080, 2340), (1080, 2400), (1170, 2532),
    (1284, 2778), (750, 1334), (828, 1792), (2560, 1440), (1366, 768),
}


def check_screenshot(image_path: str) -> dict:
    """
    Heuristic only -- combines two weak signals:
      1. Missing camera EXIF (screenshots and re-saved/edited images usually lack it)
      2. Exact match to a known screen resolution

    Neither signal alone is reliable (many real camera photos are stripped of
    EXIF by messaging apps), so this check is intentionally conservative and
    only flags when both signals agree. See README trade-offs.
    """
    try:
        img = PILImage.open(image_path)
        exif = img.getexif()
        has_camera_exif = bool(exif) and any(tag in exif for tag in (271, 272, 306))  # Make, Model, DateTime
        dimensions = img.size
    except Exception as exc:
        return {
            "check_name": "screenshot_detection",
            "passed": True,
            "confidence": 0.2,
            "detail": f"Could not analyze metadata ({exc}); defaulting to pass with low confidence.",
        }

    resolution_matches = dimensions in COMMON_SCREEN_RESOLUTIONS or tuple(reversed(dimensions)) in COMMON_SCREEN_RESOLUTIONS

    is_likely_screenshot = resolution_matches and not has_camera_exif

    if is_likely_screenshot:
        detail = f"No camera EXIF found and dimensions {dimensions} match a common screen resolution."
        confidence = 0.65
    elif resolution_matches:
        detail = f"Dimensions {dimensions} match a common screen resolution, but camera EXIF is present -- likely a genuine photo."
        confidence = 0.6
    else:
        detail = f"Dimensions {dimensions} don't match common screen resolutions."
        confidence = 0.55

    return {
        "check_name": "screenshot_detection",
        "passed": not is_likely_screenshot,
        "confidence": confidence,
        "detail": detail,
    }
