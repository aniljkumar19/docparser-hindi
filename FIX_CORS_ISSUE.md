# Fix CORS Issue - Dashboard Connection

## Problem
Dashboard shows CORS error: `Access to fetch at 'http://localhost:8000/v1/jobs' from origin 'http://locahost:3000' has been blocked`

## Root Cause
1. **Typo in browser URL**: Error shows `http://locahost:3000` (missing 'l') instead of `http://localhost:3000`
2. **CORS configuration**: Already fixed in code, but API needs restart

## Solution

### Step 1: Fix Browser URL
Make sure you're accessing:
- ✅ `http://localhost:3000` (correct)
- ❌ `http://locahost:3000` (typo - wrong)

### Step 2: Clear Browser Cache
1. Open browser DevTools (F12)
2. Right-click refresh button → "Empty Cache and Hard Reload"
3. Or: `Ctrl+Shift+Delete` → Clear cache for localhost

### Step 3: Restart API Server
The API needs to be restarted to pick up CORS changes:

```bash
# If running directly:
pkill -f "uvicorn app.main:app"
cd /home/vncuser/apps/docparser/api
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or if using Docker:
docker-compose restart api
```

### Step 4: Verify CORS is Working
```bash
curl -H "Origin: http://localhost:3000" -H "Authorization: Bearer dev_123" -I http://localhost:8000/v1/jobs
```

Should see:
```
access-control-allow-origin: http://localhost:3000
access-control-allow-credentials: true
```

## Current CORS Configuration
- ✅ Allows: `http://localhost:3000`
- ✅ Allows: `http://127.0.0.1:3000`
- ✅ Credentials: Enabled
- ✅ Methods: All (`*`)
- ✅ Headers: Authorization, Content-Type, x-api-key

## If Still Not Working
1. Check browser console for exact error
2. Verify API is running: `curl http://localhost:8000/`
3. Check API logs for CORS errors
4. Try incognito/private mode to bypass cache

