# Backend Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y     tesseract-ocr ghostscript gcc libpq-dev curl   && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY samples ./samples

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
