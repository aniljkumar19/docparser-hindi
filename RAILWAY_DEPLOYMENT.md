# Railway Deployment Guide

This guide will help you deploy DocParser to Railway.

## Prerequisites

1. A Railway account (sign up at https://railway.app)
2. Your GitHub repository connected to Railway
3. Required environment variables configured

## Deployment Steps

### 1. Create a New Project on Railway

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `docparser` repository
5. Railway will auto-detect the Dockerfile

### 2. Configure Environment Variables

In Railway's project settings, add these environment variables:

#### Required Variables:

- `DB_URL` - PostgreSQL connection string (Railway can provision a PostgreSQL database)
  - Example: `postgresql://user:password@host:5432/dbname`
  - Or use Railway's PostgreSQL service and it will auto-inject `DATABASE_URL`

- `S3_ENDPOINT` - Your S3-compatible storage endpoint
  - For AWS S3: `https://s3.amazonaws.com`
  - For MinIO: Your MinIO endpoint URL
  - For Railway's storage: Check Railway's storage service

- `S3_ACCESS_KEY` - S3 access key ID

- `S3_SECRET_KEY` - S3 secret access key

- `S3_BUCKET` - S3 bucket name (default: `docparser`)

- `S3_REGION` - S3 region (default: `us-east-1`)

- `S3_SECURE` - Use HTTPS for S3 (default: `true` for production)

- `API_KEYS` - Comma-separated list of API keys in format: `key1:tenant1,key2:tenant2`
  - Example: `dev_123:tenant_1,prod_456:tenant_2`

#### Optional Variables:

- `REDIS_URL` - Redis connection string (for background job processing)
  - Railway can provision Redis, or use an external service
  - If not set, jobs will run synchronously

- `MAX_FILE_MB` - Maximum file size in MB (default: `15`)

- `PORT` - Server port (Railway sets this automatically, don't override)

- `ENV` - Environment name (e.g., `production`)

### 3. Provision Services (Optional but Recommended)

#### PostgreSQL Database:

1. In Railway project, click "New" → "Database" → "PostgreSQL"
2. Railway will automatically create a PostgreSQL instance
3. Copy the `DATABASE_URL` from the service settings
4. Set `DB_URL` environment variable to this value

#### Redis (for Background Jobs):

1. In Railway project, click "New" → "Database" → "Redis"
2. Railway will automatically create a Redis instance
3. Copy the `REDIS_URL` from the service settings
4. Set `REDIS_URL` environment variable to this value

### 4. Deploy

Railway will automatically:
1. Build the Docker image using the Dockerfile
2. Start the container
3. Expose the service on a public URL

You'll get a URL like: `https://docparser-production.up.railway.app`

### 5. Verify Deployment

1. Visit your Railway URL: `https://your-app.up.railway.app`
2. You should see the DocParser API landing page
3. Test the health endpoint: `https://your-app.up.railway.app/health`
4. Test parsing with a sample file using your API key

## Environment Variables Summary

```bash
# Database
DB_URL=postgresql://user:pass@host:5432/dbname

# S3 Storage
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET=docparser
S3_REGION=us-east-1
S3_SECURE=true

# API Authentication
API_KEYS=dev_123:tenant_1,prod_456:tenant_2

# Optional
REDIS_URL=redis://localhost:6379
MAX_FILE_MB=15
ENV=production
```

## Troubleshooting

### Build Fails

- Check Railway build logs for errors
- Ensure all dependencies in `api/requirements.txt` are valid
- Verify Dockerfile syntax

### App Crashes on Start

- Check environment variables are set correctly
- Verify database connection string format
- Check S3 credentials are valid
- Review Railway logs for error messages

### Jobs Not Processing

- Ensure `REDIS_URL` is set if using background jobs
- Check Redis service is running
- Verify worker is processing jobs (if using separate worker)

## Notes

- Railway automatically handles HTTPS/SSL
- The app listens on the port provided by Railway's `PORT` environment variable
- Database migrations should run automatically via `init_db()` on startup
- S3 bucket will be created automatically if it doesn't exist (via `ensure_bucket()`)

## Next Steps

After deployment:
1. Set up your frontend dashboard to point to the Railway API URL
2. Configure CORS origins in the API if needed
3. Set up monitoring and alerts
4. Configure custom domain (optional)

