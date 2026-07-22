FROM python:3.11-slim

# tesseract-ocr: OCR engine used by pytesseract
# libgl1, libglib2.0-0: required by opencv-python-headless at import time
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# Default command for platforms (like Render) that just run the image as-is
# with no override. Falls back to 8000 if $PORT isn't set (e.g. plain
# `docker run`). docker-compose.yml overrides this with its own `command:`
# for local dev with --reload, so this line only matters for hosted
# deploys that don't specify their own start command.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}