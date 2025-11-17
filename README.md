# Doc Parser PRO (Queue + DB + Storage + Dashboard)

Production-minded scaffold:
- FastAPI API
- Redis + RQ background worker
- Postgres persistence (SQLAlchemy)
- S3/MinIO storage (boto3)
- Optional ClamAV (stubbed env)
- Next.js dashboard (upload tester)
- docker-compose for local dev
- Tally CSV/XML export + Zoho Books push stub
- Stripe metered billing usage recording

## Quick Start

```bash
docker compose up --build
# API: http://localhost:8000
# Dashboard: http://localhost:3000
# MinIO: http://localhost:9001 (minio / minio123)
# Redis: redis://localhost:6379
# Postgres: localhost:5432 (docdb/docuser/docpass)
```

Create a bucket **docparser** in MinIO console before first upload.

### Test
```bash
curl -s -X POST "http://localhost:8000/v1/parse"   -H "Authorization: Bearer dev_123"   -F "file=@api/samples/sample_invoice.txt" | jq

curl -s -H "Authorization: Bearer dev_123"   "http://localhost:8000/v1/jobs/<job_id>" | jq
```
