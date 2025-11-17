# Storage Decision: Local File Storage on Railway

## Decision

**Use local file storage on Railway for testing and prototyping.**

Files are stored in `/app/uploads` on Railway's persistent disk. No S3/AWS configuration required.

## Rationale

- ✅ **Simpler setup** - No external services needed
- ✅ **Railway Pro account** - More disk space and better persistence
- ✅ **Good for testing/prototyping** - Fast iteration, no extra costs
- ✅ **Can take backups** - Files can be backed up if needed
- ✅ **Works immediately** - No S3 credentials to configure

## Implementation

### Storage Location
```
/app/uploads/uploads/{uuid}/{filename}
```

### Configuration
- **Default**: Local file storage (automatic)
- **No environment variables needed** for local storage
- Files persist across container restarts on Railway

### Code Location
- Storage logic: `api/app/storage.py`
- Automatically uses local storage if S3 is not configured
- Falls back to local storage if S3 fails

## Backup Commands

### Quick Backup (Railway CLI)

```bash
# Connect to Railway container
railway run bash

# Create compressed backup of all uploads
cd /app
tar -czf uploads-backup-$(date +%Y%m%d-%H%M%S).tar.gz uploads/

# List the backup file
ls -lh uploads-backup-*.tar.gz

# Exit container
exit
```

### Download Backup from Railway

**Option A: Via Railway Dashboard**
1. Go to Railway → Your service → Deployments
2. Click on a deployment
3. Use the terminal/SSH feature to download the backup file

**Option B: Via Railway CLI**
```bash
# Copy file from container to local machine
railway run cat /app/uploads-backup-*.tar.gz > backup.tar.gz
```

### Backup Specific Date Range

```bash
# Connect to Railway
railway run bash

# Backup files from last 7 days
cd /app/uploads
find . -type f -mtime -7 -exec tar -czf recent-uploads.tar.gz {} +

# Backup files older than 30 days (archive)
find . -type f -mtime +30 -exec tar -czf archive-uploads.tar.gz {} +
```

### Full Backup Script

```bash
#!/bin/bash
# backup-uploads.sh

# Connect to Railway and create backup
railway run bash << 'EOF'
cd /app
BACKUP_FILE="uploads-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$BACKUP_FILE" uploads/
echo "Backup created: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"
EOF
```

### Restore from Backup

```bash
# Connect to Railway
railway run bash

# Extract backup
cd /app
tar -xzf uploads-backup-YYYYMMDD-HHMMSS.tar.gz

# Verify files restored
ls -la uploads/
```

### Alternative: Add Backup Endpoint to API

Could add an API endpoint to zip and download files programmatically:
```python
@app.get("/v1/admin/backup-uploads")
async def backup_uploads(authorization: str = Header(...)):
    # Verify admin access
    # Create zip of /app/uploads
    # Return as downloadable file
    ...
```

### Scheduled Backups (Future)

Set up a cron job or scheduled task to periodically backup files:
- Use Railway's cron service
- Or external scheduler (GitHub Actions, etc.)
- Backup to S3 or external storage

## When to Consider S3

Consider migrating to S3 (AWS, Cloudflare R2, etc.) when:

- **Production with high volume** - Many files, large files
- **Need redundancy** - Files must survive service deletion
- **Multiple services** - Other services need to access the same files
- **Compliance requirements** - Need specific storage locations/regions
- **Cost optimization** - S3 might be cheaper at scale

## Migration Path (Future)

If you need to migrate to S3 later:

1. Set environment variable: `STORAGE_TYPE=s3`
2. Configure S3 credentials:
   - `S3_ENDPOINT`
   - `S3_ACCESS_KEY`
   - `S3_SECRET_KEY`
   - `S3_BUCKET`
   - `S3_REGION`
3. The code will automatically use S3 instead of local storage
4. Existing files in `/app/uploads` will remain (but won't be accessible via S3)
5. New files will go to S3

## Current Status

- ✅ Local file storage implemented
- ✅ Automatic fallback to local if S3 fails
- ✅ No S3 configuration required
- ✅ Files stored in `/app/uploads` on Railway disk

## Notes

- Railway Pro account provides persistent disk storage
- Files persist across container restarts
- Files are lost if service is deleted/recreated (backup before major changes)
- For production at scale, consider S3 for durability and redundancy

