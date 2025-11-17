# Fix: Bulk Upload "Not Found" Error

## Problem
The `/v1/bulk-parse` endpoint exists in the code but isn't registered in the running API server.

## Solution: Restart the API Server

The API is running directly (not in Docker). You need to restart it:

### Option 1: Manual Restart

```bash
# Find and kill the API process
ps aux | grep "uvicorn app.main" | grep -v grep

# Kill it (replace PID with actual process ID)
kill <PID>

# Start it again
cd /home/vncuser/apps/docparser/api
bash run.sh
```

### Option 2: Use the Script

```bash
cd /home/vncuser/apps/docparser
./restart_api_direct.sh
```

### Option 3: If Using Docker

```bash
sudo docker-compose restart api
```

## Verify It's Fixed

After restart, check:
```bash
curl -s "http://localhost:8000/openapi.json" | grep bulk-parse
```

If it shows the endpoint, it's working!

## Why This Happened

The endpoint code was added to `main.py` but the running server was started before that code existed. FastAPI needs a restart to register new routes.

