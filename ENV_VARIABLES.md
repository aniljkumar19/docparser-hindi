# Environment Variables Reference

This document lists all environment variables used by DocParser API.

## Required Variables

### Database
- `DB_URL` - Database connection string
  - **Format**: `postgresql://user:password@host:port/dbname`
  - **Default**: `sqlite:///./doc.db` (SQLite, for development only)
  - **Production**: Use PostgreSQL connection string from Railway/your provider

### S3 Storage
- `S3_ENDPOINT` - S3-compatible storage endpoint URL
  - **Examples**: 
    - AWS: `https://s3.amazonaws.com`
    - MinIO: `http://localhost:9000` (dev) or `https://your-minio.com` (prod)
  - **Default**: `http://localhost:9000`

- `S3_ACCESS_KEY` - S3 access key ID
  - **Default**: `minio` (for local MinIO)

- `S3_SECRET_KEY` - S3 secret access key
  - **Default**: `minio123` (for local MinIO)

- `S3_BUCKET` - S3 bucket name
  - **Default**: `docparser`

- `S3_REGION` - S3 region
  - **Default**: `us-east-1`

- `S3_SECURE` - Use HTTPS for S3 connections
  - **Values**: `true` or `false`
  - **Default**: `false` (set to `true` for production)

### API Authentication
- `API_KEYS` - Comma-separated API keys with tenant mapping
  - **Format**: `key1:tenant1,key2:tenant2,key3:tenant3`
  - **Example**: `dev_123:tenant_1,prod_456:tenant_2`
  - **Required**: Yes (at least one key)

## Optional Variables

### Background Jobs (Redis)
- `REDIS_URL` - Redis connection string for background job processing
  - **Format**: `redis://host:port` or `redis://:password@host:port`
  - **Default**: Empty (jobs run synchronously if not set)
  - **Note**: If not provided, jobs will process immediately (blocking)

### File Upload
- `MAX_FILE_MB` - Maximum file size in megabytes
  - **Default**: `15`

### CORS
- `CORS_ORIGINS` - Allowed CORS origins (comma-separated)
  - **Format**: `http://localhost:3000,https://yourdomain.com`
  - **Default**: `http://localhost:3000,http://127.0.0.1:3000`
  - **Production**: Add your frontend domain(s)

### Server
- `PORT` - Server port (Railway sets this automatically)
  - **Default**: `8000`
  - **Note**: Don't override on Railway - it's set automatically

### Environment
- `ENV` - Environment name
  - **Examples**: `development`, `staging`, `production`
  - **Default**: Not set

## Railway-Specific Variables

Railway automatically provides:
- `PORT` - The port your app should listen on
- `DATABASE_URL` - If you provision a PostgreSQL database
- `REDIS_URL` - If you provision a Redis instance

You can use `DATABASE_URL` directly or map it to `DB_URL`:
```bash
DB_URL=$DATABASE_URL
```

## Example .env File (Development)

```bash
# Database
DB_URL=sqlite:///./doc.db

# S3 Storage (MinIO local)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_BUCKET=docparser
S3_REGION=us-east-1
S3_SECURE=false

# API Keys
API_KEYS=dev_123:tenant_1,test_456:tenant_2

# Redis (optional)
REDIS_URL=redis://localhost:6379

# File Upload
MAX_FILE_MB=15

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Environment
ENV=development
```

## Example Railway Environment Variables

```bash
# Database (from Railway PostgreSQL service)
DB_URL=$DATABASE_URL

# S3 Storage (AWS S3 or Railway storage)
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your_aws_access_key
S3_SECRET_KEY=your_aws_secret_key
S3_BUCKET=docparser-prod
S3_REGION=us-east-1
S3_SECURE=true

# API Keys
API_KEYS=prod_key_1:tenant_1,prod_key_2:tenant_2

# Redis (from Railway Redis service)
REDIS_URL=$REDIS_URL

# File Upload
MAX_FILE_MB=15

# CORS (add your frontend domain)
CORS_ORIGINS=https://your-dashboard.com,https://app.yourdomain.com

# Environment
ENV=production
```

