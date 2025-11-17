# Quick Fixes Needed - Complete in 2 Days

## Current Issues (Need Fixing)

### 1. ❌ Bulk Upload Endpoint Not Registered
**Status:** Endpoint exists in code but not loaded  
**Fix:** `sudo docker-compose restart api`  
**Time:** 30 seconds

### 2. ❌ API Key Not Working  
**Status:** API_KEYS configured but container not loading it  
**Fix:** `sudo docker-compose restart api` (same as #1)  
**Time:** Same restart fixes both

### 3. ❌ Worker Not Running
**Status:** 2 jobs stuck in queue  
**Fix:** `sudo docker-compose up -d worker`  
**Time:** 30 seconds

## ONE COMMAND TO FIX EVERYTHING

```bash
cd /home/vncuser/apps/docparser

# Fix all issues at once
sudo docker-compose restart api
sudo docker-compose up -d worker

# Wait for services
sleep 10

# Verify
./verify_and_fix_bulk.sh
```

## What This Fixes

✅ Bulk upload endpoint will be registered  
✅ API keys will work  
✅ Worker will process queued jobs  
✅ Everything should work end-to-end  

## After Running

1. **Test bulk upload:** http://localhost:3000/bulk-upload
2. **Test single upload:** http://localhost:3000
3. **Check queued jobs:** Should start processing automatically

## Estimated Time

- **Fix time:** 2 minutes
- **Testing:** 5 minutes
- **Total:** ~10 minutes to complete

## Cursor Usage Tip

Since you have limited usage left:
- I'll be concise and efficient
- Focus on critical fixes only
- You can test/debug yourself after fixes are done

Let's get this done quickly! 🚀

