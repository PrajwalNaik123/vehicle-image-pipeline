import logging
import time

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import get_db, REDIS_URL, QUEUE_BACKEND, engine, Base
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


# Queue setup depends on QUEUE_BACKEND (see app/db.py for the trade-off notes).
# Only import/connect to Redis when actually using the "rq" backend so the
# "inline" backend can run with zero external dependencies.
if QUEUE_BACKEND == "rq":
    from redis import Redis
    from rq import Queue, Retry

    redis_conn = Redis.from_url(REDIS_URL)
    queue = Queue("image_processing", connection=redis_conn)
else:
    queue = None


@app.on_event("startup")
def on_startup():
    # For a take-home this is fine; a real project would use Alembic
    # migrations instead of create_all. See README trade-offs.
    #
    # Retry with backoff: on platforms like Render, the web service and the
    # database can start up in parallel, so the very first connection
    # attempt can hit a Postgres that isn't accepting connections yet. A
    # hard failure here would crash the whole app on every cold start, so
    # tolerate a few early failures instead of assuming the DB is instantly
    # reachable.
    attempts = 8
    for attempt in range(1, attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError:
            if attempt == attempts:
                raise
            wait = min(2 ** attempt, 20)
            logger.warning("Database not ready yet (attempt %d/%d), retrying in %ds", attempt, attempts, wait)
            time.sleep(wait)


@app.post("/images", response_model=UploadResponse, status_code=202)
def upload_image(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
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
    logger.info("Upload received: image_id=%s QUEUE_BACKEND=%s", image.id, QUEUE_BACKEND)

    if QUEUE_BACKEND == "rq":
        # Retry twice with backoff for transient failures (e.g. DB momentarily
        # unreachable from the worker). Permanent failures (corrupt image) still
        # get caught inside process_image and marked as `failed` explicitly.
        queue.enqueue(
            process_image,
            image.id,
            retry=Retry(max=2, interval=[5, 15]),
            job_timeout=120,
        )
    else:
        # "inline" backend: runs in a background thread within this same
        # process after the response is sent. No separate worker, no Redis --
        # trades away cross-process durability and automatic retries (a
        # process restart mid-job loses that job) for zero infra dependencies.
        logger.info("Dispatching in-process background task for image_id=%s", image.id)
        background_tasks.add_task(process_image, image.id)

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
