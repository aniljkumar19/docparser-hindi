FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for PDF processing and OCR
RUN apt-get update && apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire api directory
COPY api/ /app/

# Railway provides PORT env var, default to 8000 if not set
ENV PORT=8000

# Expose the port
EXPOSE $PORT

# Run uvicorn with the correct module path
# Railway will set PORT env var automatically
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
