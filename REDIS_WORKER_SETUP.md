# Redis + Worker Setup Guide

## How It Works

The application now supports **automatic worker startup** in the same container:

1. **Without Redis**: Jobs process synchronously (API waits for parsing to finish)
2. **With Redis**: Jobs process asynchronously (API responds immediately, worker processes in background)

## Setup Steps

### Step 1: Provision Redis in Railway

1. Go to your Railway project
2. Click **"New"** → **"Database"** → **"Redis"**
3. Railway will create a Redis instance automatically

### Step 2: Get Redis Connection URL

1. Click on the Redis service you just created
2. Go to **"Variables"** tab
3. Find `REDIS_URL` (looks like: `redis://default:password@redis.railway.internal:6379`)
4. Copy the entire `REDIS_URL` value

### Step 3: Set REDIS_URL in Your API Service

1. Go to your **main API service** (not the Redis service)
2. Go to **"Variables"** tab
3. Click **"New Variable"**
4. Name: `REDIS_URL`
5. Value: Paste the Redis URL from Step 2
6. Click **"Add"**

### Step 4: Redeploy

Railway will automatically redeploy when you add the environment variable. Or manually trigger a redeploy.

## How It Works

The startup script (`api/start.sh`) automatically:

1. ✅ Checks if `REDIS_URL` is set and valid
2. ✅ Starts RQ worker in background (if Redis available)
3. ✅ Starts FastAPI API server (foreground - main process)
4. ✅ Handles graceful shutdown (kills worker when API stops)

## Verification

After deployment, check Railway logs. You should see:

```
🚀 Starting DocParser API...
✅ Redis detected: redis://...
🔄 Starting RQ worker in background...
   Worker PID: 123
🌐 Starting FastAPI server on port 8000...
```

If Redis is not configured, you'll see:

```
🚀 Starting DocParser API...
ℹ️  Redis not configured. Jobs will process synchronously.
🌐 Starting FastAPI server on port 8000...
```

## Testing

1. Upload a document via the dashboard
2. Check the API response - it should return immediately with `status: "queued"`
3. Check Railway logs - you should see the worker processing the job
4. Poll the job status - it should change from `queued` → `processing` → `succeeded`

## Benefits

✅ **Better UX**: API responds instantly, no waiting  
✅ **Scalable**: Can handle multiple jobs concurrently  
✅ **Resilient**: Failed jobs can retry without blocking API  
✅ **Simple**: No separate worker service needed (runs in same container)

## Troubleshooting

### Worker not starting?

- Check that `REDIS_URL` is set correctly
- Verify Redis service is running in Railway
- Check logs for connection errors

### Jobs still processing synchronously?

- Verify `REDIS_URL` is set (not empty)
- Make sure `REDIS_URL` doesn't point to `localhost` (won't work in Railway)
- Check logs to see if worker started

### Worker crashes?

- Check Railway logs for error messages
- Verify Redis connection is stable
- Worker will auto-restart if it crashes (Railway will restart the container)

## Current Status

- ✅ Startup script created (`api/start.sh`)
- ✅ Dockerfile updated to use startup script
- ✅ Automatic worker detection (starts only if Redis available)
- ✅ Graceful shutdown handling

## Next Steps (Optional)

If you need more advanced features:

1. **Separate Worker Service**: Create a dedicated Railway service just for the worker (better for high volume)
2. **Multiple Workers**: Run multiple worker processes for parallel processing
3. **Worker Monitoring**: Add health checks and metrics for worker status

For now, the single-container approach works great for most use cases!

