# Mission-Critical Items for Production Beta

**Created:** 2025-01-XX  
**Status:** Pre-Beta Review  
**Priority:** Address before sharing with accountants

---

## 🚨 High Priority (Do Before Beta)

### 1. Rate Limiting Protection
**Issue:** Rate limiting middleware is disabled by default (`USE_API_KEY_MIDDLEWARE=false`)

**Risk:**
- API abuse and DDoS attacks
- Uncontrolled resource consumption
- Unexpected cost overruns

**Current State:**
- Rate limiting code exists in `api/app/middleware/auth.py`
- Database-backed API keys have `rate_limit_per_minute` and `rate_limit_per_hour` fields
- Middleware is disabled unless `USE_API_KEY_MIDDLEWARE=true` env var is set

**Fix:**
1. **Option A (Recommended):** Enable middleware in Railway
   - Set `USE_API_KEY_MIDDLEWARE=true` in Railway environment variables
   - This automatically applies rate limits to all endpoints

2. **Option B:** Add basic rate limiting to legacy `verify_api_key()` function
   - Add in-memory rate limit tracking (or Redis-based)
   - Check limits before processing requests

**Files to Modify:**
- `api/app/main.py` (line 23-25): Enable middleware
- Or: `api/app/security.py`: Add rate limiting to `verify_api_key()`

**Testing:**
- Test with multiple rapid requests
- Verify 429 status code when limits exceeded
- Check that limits reset after time window

---

### 2. File Type Validation
**Issue:** Only file size is checked (15MB), not file type/extension

**Risk:**
- Malicious file uploads (executables, scripts)
- Server crashes from invalid file formats
- Security vulnerabilities

**Current State:**
- `MAX_FILE_MB = 15` is enforced
- No file extension or MIME type validation
- Accepts any file type

**Fix:**
Add validation in `/v1/parse` and `/v1/bulk-parse` endpoints:

```python
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.json', '.csv', '.txt'}
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg', 'image/png', 'image/tiff',
    'application/json', 'text/csv', 'text/plain'
}

def validate_file_type(filename: str, content_type: str) -> bool:
    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    # Check MIME type
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        return False
    
    return True
```

**Files to Modify:**
- `api/app/main.py`: Add validation in `parse_endpoint()` (around line 998)
- `api/app/bulk_api.py`: Add validation in `bulk_parse_endpoint()` (around line 45)

**Error Message:**
```python
raise HTTPException(
    status_code=400,
    detail=f"File type not allowed. Allowed: PDF, images (JPG/PNG/TIFF), JSON, CSV, TXT"
)
```

**Testing:**
- Upload .exe, .zip, .docx files → should reject
- Upload valid PDF/image → should accept
- Check error messages are clear

---

### 3. Automated Database Backups
**Issue:** Backup scripts exist but aren't automated

**Risk:**
- Data loss on Railway/cloud failures
- No recovery point if database crashes
- Lost API keys, jobs, client data

**Current State:**
- Manual backup scripts exist: `export_db.sh`, `export_docker_db.sh`
- No scheduled backups
- Railway PostgreSQL may have automatic backups (check Railway dashboard)

**Fix:**
1. **Check Railway Backups First:**
   - Railway may already have automatic PostgreSQL backups
   - Check Railway dashboard → Database → Backups section
   - If enabled, document the retention policy

2. **If No Railway Backups, Set Up Automated Backups:**
   - **Option A:** Railway Cron Job
     - Create a scheduled job that runs `export_db.sh` daily
     - Store backups in S3/MinIO or external storage
   
   - **Option B:** External Backup Service
     - Use a service like `pg_dump` via cron on external server
     - Or use a managed backup service

3. **Backup Retention Policy:**
   - Daily backups for last 7 days
   - Weekly backups for last 4 weeks
   - Monthly backups for last 12 months

**Files to Create/Modify:**
- `scripts/backup_database.sh`: Automated backup script
- `scripts/restore_database.sh`: Restore from backup
- Railway cron job configuration

**Testing:**
- Run backup script manually
- Verify backup file is created
- Test restore process
- Document backup location and access

---

## ⚠️ Medium Priority (Address Soon)

### 4. Better Error Messages for Users
**Issue:** Generic "Server error" messages don't help users debug

**Risk:**
- Poor user experience
- Increased support burden
- Users can't self-diagnose issues

**Current State:**
- Many endpoints return generic `HTTPException(status_code=500, detail=str(e))`
- Error messages may expose internal details or be too vague

**Fix:**
Create user-friendly error messages:

```python
# Instead of:
raise HTTPException(status_code=500, detail=str(e))

# Use:
if "File too large" in str(e):
    raise HTTPException(
        status_code=400,
        detail=f"File size ({mb:.2f} MB) exceeds maximum allowed ({MAX_FILE_MB} MB). Please compress or split the file."
    )
elif "Unsupported document type" in str(e):
    raise HTTPException(
        status_code=400,
        detail="Document type not recognized. Supported: invoices, GSTR-1/2B/3B, sales/purchase registers, bank statements."
    )
elif "Parsing failed" in str(e):
    raise HTTPException(
        status_code=422,
        detail="Unable to parse document. Please ensure the document is clear and contains readable text. Try: 1) Better quality scan, 2) OCR if needed, 3) Check document format."
    )
else:
    # Log full error internally, return generic message
    logging.error(f"Internal error: {e}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail="An error occurred processing your request. Please try again or contact support if the issue persists."
    )
```

**Files to Modify:**
- `api/app/main.py`: All endpoints with error handling
- `api/app/worker.py`: Job processing errors
- `api/app/parsers/router.py`: Parsing errors

**Error Categories:**
- **400 Bad Request:** Invalid input (file size, type, format)
- **401 Unauthorized:** Missing/invalid API key
- **404 Not Found:** Job/document not found
- **422 Unprocessable:** Parsing failed, data quality issues
- **429 Too Many Requests:** Rate limit exceeded
- **500 Internal Server Error:** Unexpected server errors (log details, return generic message)

**Testing:**
- Test each error scenario
- Verify error messages are helpful
- Ensure no sensitive info leaked (stack traces, file paths)

---

### 5. Job Failure Notifications
**Issue:** Users must poll to check job status; no notifications when jobs fail

**Risk:**
- Users don't know when jobs fail
- Delayed issue detection
- Poor user experience

**Current State:**
- Jobs have status: `queued`, `processing`, `succeeded`, `failed`
- No webhook or notification system
- Users must manually check job status

**Fix:**
1. **Webhook Support (Recommended):**
   - Add webhook registration endpoint
   - Call webhook when job status changes to `failed` or `succeeded`
   - Include job details in webhook payload

2. **Email Notifications (Alternative):**
   - Send email when job fails
   - Include error message and job ID
   - Require email in API key registration

**Implementation:**
```python
# In worker.py, after job fails:
if job.status == "failed":
    # Trigger webhook if registered
    webhook_url = get_webhook_for_tenant(tenant_id)
    if webhook_url:
        send_webhook(webhook_url, {
            "event": "job.failed",
            "job_id": job.id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
```

**Files to Modify:**
- `api/app/worker.py`: Add webhook/email on job failure
- `api/app/db.py`: Add webhook_url to ApiKey or Client model
- `api/app/main.py`: Add webhook registration endpoint

**Testing:**
- Register webhook
- Upload file that will fail
- Verify webhook is called
- Test webhook retry logic

---

### 6. Audit Logging
**Issue:** No audit trail for sensitive operations

**Risk:**
- Compliance issues (GDPR, data privacy)
- Security incidents hard to trace
- No accountability for data access

**Current State:**
- Basic logging exists (application logs)
- No structured audit log
- No tracking of who accessed what data

**Fix:**
Create audit log table and log key operations:

```python
# New table: audit_logs
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    tenant_id = Column(String)
    api_key_id = Column(String)
    action = Column(String)  # 'file_upload', 'job_access', 'export_download', 'api_key_created'
    resource_type = Column(String)  # 'job', 'file', 'api_key'
    resource_id = Column(String)
    ip_address = Column(String)
    user_agent = Column(String)
    details = Column(JSON)

# Log key operations:
def log_audit_event(db, tenant_id, api_key_id, action, resource_type, resource_id, ip, user_agent, details=None):
    audit = AuditLog(
        id=generate_id(),
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip,
        user_agent=user_agent,
        details=details or {}
    )
    db.add(audit)
    db.commit()
```

**Operations to Log:**
- File uploads
- Job creation/access
- Data exports (CSV, XML, JSON)
- API key creation/deletion
- Admin actions
- Failed authentication attempts

**Files to Modify:**
- `api/app/db.py`: Add AuditLog model
- `api/app/main.py`: Add audit logging to endpoints
- `api/app/security.py`: Log auth failures

**Retention:**
- Keep audit logs for 1 year minimum (compliance)
- Archive older logs if needed

**Testing:**
- Perform various operations
- Verify audit logs are created
- Test audit log query endpoint (admin only)

---

## 📋 Low Priority (Post-Beta)

### 7. Health Check Monitoring
**Issue:** `/health` endpoint exists but may not be monitored

**Risk:**
- Downtime goes unnoticed
- Slow incident response

**Fix:**
- Set up uptime monitoring service (UptimeRobot, Pingdom, Better Uptime)
- Monitor `/health` endpoint every 1-5 minutes
- Set up alerts (email, SMS, Slack)

**Current Endpoint:**
- `GET /health` returns: `{"status": "ok", "service": "docparser-api", "version": "0.2.0"}`

**Action Items:**
- Sign up for monitoring service
- Add `/health` endpoint URL
- Configure alert channels
- Test alert delivery

---

### 8. Data Retention Policy
**Issue:** No automatic cleanup of old jobs/files

**Risk:**
- Database/storage bloat
- Increasing costs
- Performance degradation

**Fix:**
Implement retention policy:

```python
# Delete jobs older than 90 days
def cleanup_old_jobs(db, days=90):
    cutoff = datetime.utcnow() - timedelta(days=days)
    old_jobs = db.query(Job).filter(Job.created_at < cutoff).all()
    for job in old_jobs:
        # Delete associated files from S3
        if job.object_key:
            delete_file_from_s3(job.object_key)
        db.delete(job)
    db.commit()
```

**Retention Policy:**
- Jobs: 90 days (configurable per tenant)
- Files: Delete when job is deleted
- Audit logs: 1 year minimum

**Files to Create:**
- `api/app/cleanup.py`: Cleanup script
- Railway cron job to run daily

**Testing:**
- Create test jobs with old timestamps
- Run cleanup script
- Verify jobs/files are deleted
- Verify recent jobs are kept

---

## 🎯 Quick Wins (Can Implement Today)

### Priority Order:
1. **Enable Rate Limiting** (5 minutes)
   - Set `USE_API_KEY_MIDDLEWARE=true` in Railway
   - Test with rapid requests

2. **Add File Type Validation** (30 minutes)
   - Add validation function
   - Update parse endpoints
   - Test with various file types

3. **Improve Error Messages** (1 hour)
   - Create error message helper
   - Update all endpoints
   - Test error scenarios

---

## 📝 Implementation Checklist

### Before Beta Launch:
- [ ] Enable rate limiting (`USE_API_KEY_MIDDLEWARE=true`)
- [ ] Add file type validation
- [ ] Improve error messages
- [ ] Verify database backups (Railway or manual)
- [ ] Test all error scenarios
- [ ] Document API rate limits for users

### Post-Beta (Week 1-2):
- [ ] Set up job failure notifications (webhooks)
- [ ] Implement audit logging
- [ ] Set up health check monitoring
- [ ] Create data retention policy

### Future Enhancements:
- [ ] Search/filter in dashboard
- [ ] Multi-GSTIN support per tenant
- [ ] Scheduled exports
- [ ] Email notifications
- [ ] Data encryption at rest
- [ ] API usage analytics dashboard

---

## 🔍 Testing Checklist

For each implemented item:

1. **Rate Limiting:**
   - [ ] Send 100 requests in 1 minute → should get 429 after limit
   - [ ] Verify limits reset after time window
   - [ ] Check different API keys have separate limits

2. **File Type Validation:**
   - [ ] Upload .exe, .zip, .docx → should reject
   - [ ] Upload PDF, JPG, PNG, JSON → should accept
   - [ ] Verify clear error messages

3. **Error Messages:**
   - [ ] Test each error scenario
   - [ ] Verify messages are helpful
   - [ ] Ensure no sensitive info leaked

4. **Database Backups:**
   - [ ] Run backup script
   - [ ] Verify backup file created
   - [ ] Test restore process

5. **Job Notifications:**
   - [ ] Register webhook
   - [ ] Upload file that fails
   - [ ] Verify webhook called

6. **Audit Logging:**
   - [ ] Perform various operations
   - [ ] Verify logs created
   - [ ] Test log query endpoint

---

## 📚 Related Files

- `api/app/main.py` - Main API endpoints
- `api/app/security.py` - API key authentication
- `api/app/middleware/auth.py` - Rate limiting middleware
- `api/app/worker.py` - Background job processing
- `api/app/db.py` - Database models
- `api/app/bulk_api.py` - Bulk upload endpoints
- `scripts/export_db.sh` - Database backup script

---

## 🆘 Support & Questions

If you need help implementing any of these items:
1. Review the code sections mentioned
2. Check existing implementations (rate limiting, error handling)
3. Test incrementally (one item at a time)
4. Document any issues or questions

---

**Last Updated:** 2025-01-XX  
**Next Review:** After beta feedback from accountants


