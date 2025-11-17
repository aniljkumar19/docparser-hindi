FROM node:20-alpine AS dashboard-builder

# Build the Next.js dashboard
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm ci
COPY dashboard/ ./
# Set API base URL for production build
ARG NEXT_PUBLIC_DOCPARSER_API_BASE
ENV NEXT_PUBLIC_DOCPARSER_API_BASE=${NEXT_PUBLIC_DOCPARSER_API_BASE:-}
RUN npm run build

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

# Copy samples directory for sample documents
COPY samples/ /app/samples/

# Copy built dashboard static files from builder stage
COPY --from=dashboard-builder /app/dashboard/out /app/dashboard/out

# Railway provides PORT env var, default to 8000 if not set
ENV PORT=8000

# Expose the port
EXPOSE 8000

# Run uvicorn with the correct module path
# Railway will set PORT env var automatically
# Use shell form to properly expand $PORT variable
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
