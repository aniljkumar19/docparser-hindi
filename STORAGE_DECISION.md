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

## Backup Options

### Option 1: Railway CLI
```bash
# SSH into Railway container
railway run bash

# Create backup
tar -czf uploads-backup.tar.gz /app/uploads

# Download via Railway dashboard or CLI
```

### Option 2: Add Backup Endpoint
Could add an API endpoint to zip and download files:
```python
@app.get("/v1/admin/backup-uploads")
async def backup_uploads():
    # Zip /app/uploads and return as download
    ...
```

### Option 3: Scheduled Backups
Set up a cron job or scheduled task to periodically backup files to external storage.

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

