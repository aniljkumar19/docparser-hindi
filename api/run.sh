#!/usr/bin/env bash
set -e
# Force Python to reload modules (clear .pyc cache)
find /app -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
find /app -name "*.pyc" -delete 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
