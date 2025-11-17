# Quick Status Check

## Current Issue: Jobs Stuck in Queue

You have **2 jobs stuck in "queued" status**. This means:

✅ Jobs are being created successfully  
❌ Worker is NOT processing them  
❌ Jobs stay in "queued" forever  

## Why This Happens

The **worker** container processes jobs from the Redis queue. If the worker isn't running, jobs get stuck.

## Quick Fix

**Start the worker:**

```bash
cd /home/vncuser/apps/docparser
sudo docker-compose up -d worker
```

**Or restart all services:**

```bash
sudo docker-compose restart
```

## Check Worker Status

```bash
sudo docker-compose ps worker
```

Should show "Up" status.

## After Starting Worker

The queued jobs should start processing automatically. Check status:

```bash
export PGPASSWORD=docpass
psql -h localhost -p 55432 -U docuser -d docdb -c "SELECT id, status FROM jobs WHERE status = 'queued';"
```

## Summary

- ✅ API is running
- ✅ Database is working  
- ✅ Jobs are being created
- ❌ Worker is NOT running (needs to be started)
- ❌ Bulk upload endpoint not registered (needs API restart)

**Two things to fix tomorrow:**
1. Start worker: `sudo docker-compose up -d worker`
2. Restart API: `sudo docker-compose restart api` (for bulk upload)

