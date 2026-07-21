import os
import shutil
import uuid

from app.db import STORAGE_DIR

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def ensure_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)


def validate_extension(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")
    return ext


def save_upload(file_obj, original_filename: str) -> tuple[str, int]:
    """
    Saves an uploaded file-like object to STORAGE_DIR under a random name
    (keeps the original extension). Returns (storage_path, size_bytes).

    NOTE: local disk storage is a deliberate simplification for this
    assignment. Swapping this function for an S3 upload is the only
    change needed to move to cloud storage -- callers only depend on
    getting back a path/key string.
    """
    ensure_storage_dir()
    ext = validate_extension(original_filename)
    unique_name = f"{uuid.uuid4()}{ext}"
    dest_path = os.path.join(STORAGE_DIR, unique_name)

    with open(dest_path, "wb") as out_file:
        shutil.copyfileobj(file_obj, out_file)

    size_bytes = os.path.getsize(dest_path)
    return dest_path, size_bytes
