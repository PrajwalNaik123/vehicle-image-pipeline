import logging

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from redis import Redis
from rq import Queue, Retry
from sqlalchemy.orm import Session

from app.db import get_db, REDIS_URL, engine, Base
from app.models import Image, ImageStatus
from app.schemas import UploadResponse, StatusResponse, ResultsResponse, CheckResult
from app.storage import save_upload, validate_extension
from app.tasks import process_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pipeline.api")

app = FastAPI(title="Intelligent Media Processing Pipeline")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def dashboard():
    return FileResponse("app/static/index.html")

redis_conn = Redis.from_url(REDIS_URL)
queue = Queue("image_processing", connection=redis_conn)


@app.on_event("startup")
def on_startup():
    # For a take-home this is fine; a real project would use Alembic
    # migrations instead of create_all. See README trade-offs.
    Base.metadata.create_all(bind=engine)


@app.post("/images", response_model=UploadResponse, status_code=202)
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        validate_extension(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    storage_path, size_bytes = save_upload(file.file, file.filename)

    image = Image(
        original_filename=file.filename,
        storage_path=storage_path,
        content_type=file.content_type,
        size_bytes=size_bytes,
        status=ImageStatus.pending,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    # Retry twice with backoff for transient failures (e.g. DB momentarily
    # unreachable from the worker). Permanent failures (corrupt image) still
    # get caught inside process_image and marked as `failed` explicitly.
    queue.enqueue(
        process_image,
        image.id,
        retry=Retry(max=2, interval=[5, 15]),
        job_timeout=120,
    )

    return image


@app.get("/images/{image_id}/status", response_model=StatusResponse)
def get_status(image_id: str, db: Session = Depends(get_db)):
    image = db.query(Image).filter(Image.id == image_id).one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


@app.get("/images/{image_id}/results", response_model=ResultsResponse)
def get_results(image_id: str, db: Session = Depends(get_db)):
    image = db.query(Image).filter(Image.id == image_id).one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if image.status not in (ImageStatus.completed, ImageStatus.failed):
        raise HTTPException(
            status_code=409,
            detail=f"Image is still '{image.status.value}'. Poll /images/{image_id}/status until completed or failed.",
        )

    return ResultsResponse(
        id=image.id,
        status=image.status.value,
        failure_reason=image.failure_reason,
        results=[CheckResult.model_validate(r) for r in image.results],
    )


@app.get("/health")
def health():
    return {"status": "ok"}
