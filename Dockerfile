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
