import logging

from app.db import SessionLocal
from app.models import Image, AnalysisResult, ImageStatus
from app.checks.blur import check_blur
from app.checks.brightness import check_brightness
from app.checks.duplicate import check_duplicate
from app.checks.ocr_plate import check_plate
from app.checks.screenshot import check_screenshot
from app.checks.tamper import check_tamper

logger = logging.getLogger("pipeline.tasks")

# Each check gets its own try/except in process_image so one broken check
# (e.g. a corrupt image tripping up OpenCV) doesn't take down the whole job --
# it's recorded as a failed check rather than failing the entire image.
CHECKS = [check_blur, check_brightness, check_screenshot, check_tamper, check_plate]


def process_image(image_id: str):
    """
    Entry point invoked by the RQ worker. Runs synchronously inside the
    worker process. Intentionally uses its own DB session (never reuses a
    session across threads/processes/requests).
    """
    db = SessionLocal()
    logger.info("process_image STARTED for image_id=%s", image_id)
    try:
        image = db.query(Image).filter(Image.id == image_id).one_or_none()
        if image is None:
            logger.error("process_image called with unknown image_id=%s", image_id)
            return

        image.status = ImageStatus.processing
        db.commit()

        image_path = image.storage_path
        results = []

        for check_fn in CHECKS:
            try:
                result = check_fn(image_path)
            except Exception as exc:
                logger.exception("Check %s raised an exception for image %s", check_fn.__name__, image_id)
                result = {
                    "check_name": check_fn.__name__,
                    "passed": False,
                    "confidence": 0.0,
                    "detail": f"Check crashed: {exc}",
                }
            results.append(result)

        # Duplicate check needs DB access, run separately.
        try:
            dup_result = check_duplicate(image_path, image_id, db)
        except Exception as exc:
            logger.exception("Duplicate check raised an exception for image %s", image_id)
            dup_result = {
                "check_name": "duplicate_detection",
                "passed": False,
                "confidence": 0.0,
                "detail": f"Check crashed: {exc}",
            }
        results.append(dup_result)

        for r in results:
            db.add(AnalysisResult(
                image_id=image_id,
                check_name=r["check_name"],
                passed=r["passed"],
                confidence=r["confidence"],
                detail=r.get("detail"),
            ))

        image.status = ImageStatus.completed
        db.commit()

    except Exception as exc:
        # Anything unexpected (DB down, disk error, etc.) marks the whole
        # image as failed with a reason, rather than leaving it stuck in
        # "processing" forever.
        logger.exception("process_image failed entirely for image %s", image_id)
        db.rollback()
        image = db.query(Image).filter(Image.id == image_id).one_or_none()
        if image is not None:
            image.status = ImageStatus.failed
            image.failure_reason = str(exc)
            db.commit()
    finally:
        db.close()
