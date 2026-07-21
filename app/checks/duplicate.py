import imagehash
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from app.db import DUPLICATE_HASH_THRESHOLD
from app.models import ImageHash


def check_duplicate(image_path: str, image_id: str, db: Session) -> dict:
    """
    Computes a perceptual hash (phash) for the image and compares it against
    every previously-stored hash using Hamming distance.

    Trade-off: this is an O(n) scan over all stored hashes per upload. Fine
    for a take-home / small dataset; at scale you'd want a proper nearest-
    neighbour index (e.g. a vector/BK-tree index) instead of a full scan.
    """
    try:
        img = PILImage.open(image_path)
        current_hash = imagehash.phash(img)
    except Exception as exc:
        return {
            "check_name": "duplicate_detection",
            "passed": False,
            "confidence": 1.0,
            "detail": f"Could not compute perceptual hash: {exc}",
        }

    existing = db.query(ImageHash).filter(ImageHash.image_id != image_id).all()

    best_match = None
    best_distance = None
    for entry in existing:
        distance = current_hash - imagehash.hex_to_hash(entry.phash)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_match = entry.image_id

    is_duplicate = best_distance is not None and best_distance <= DUPLICATE_HASH_THRESHOLD

    # Upsert this image's own hash so future uploads can be compared against it.
    record = db.query(ImageHash).filter(ImageHash.image_id == image_id).one_or_none()
    if record is None:
        db.add(ImageHash(image_id=image_id, phash=str(current_hash)))
    else:
        record.phash = str(current_hash)

    if is_duplicate:
        detail = f"Near-duplicate of image {best_match} (Hamming distance={best_distance}, threshold={DUPLICATE_HASH_THRESHOLD})."
        confidence = max(0.5, 1 - best_distance / (DUPLICATE_HASH_THRESHOLD * 2))
    else:
        detail = "No matching image found within hash distance threshold." if best_distance is None \
            else f"Closest match distance={best_distance} (threshold={DUPLICATE_HASH_THRESHOLD}), not close enough to flag."
        confidence = 0.7

    return {
        "check_name": "duplicate_detection",
        "passed": not is_duplicate,
        "confidence": round(confidence, 2),
        "detail": detail,
    }
