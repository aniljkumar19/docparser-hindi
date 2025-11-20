# Railway API Key Debugging

## Issue: API Key Being Rejected

The middleware is working (401 without key), but the API key is being rejected.

### Possible Causes:

1. **Key Mismatch**
   - Railway `DOCPARSER_API_KEY` doesn't match what you're sending
   - Check for extra spaces, newlines, or different casing

2. **Middleware Not Enabled**
   - Check Railway logs for: `🔐 API Key Middleware ENABLED`
   - If not present, `USE_API_KEY_MIDDLEWARE` might not be set to `true`

3. **Environment Variable Not Loaded**
   - Railway might need a restart after setting variables
   - Check that variable is set in the correct service

### Debug Steps:

#### Step 1: Check Railway Logs
Look for these messages on startup:
```
🔐 API Key Middleware ENABLED (key length: XX)
   Rate limits: 60 req/min, 5 uploads/min
```

If you see:
```
⚠️  API Key Middleware DISABLED
```
Then `USE_API_KEY_MIDDLEWARE` is not set to `true`.

#### Step 2: Verify Environment Variables
In Railway dashboard:
1. Go to your service
2. Click "Variables" tab
3. Verify:
   - `USE_API_KEY_MIDDLEWARE=true` (exactly, no quotes)
   - `DOCPARSER_API_KEY=docparser_prod_ala2q7yv2pzu7wohv82qyrpu` (exactly, no quotes, no spaces)

#### Step 3: Test Key Directly
```bash
# Test with the exact key
curl -H "x-api-key: docparser_prod_ala2q7yv2pzu7wohv82qyrpu" \
  https://docparser-production-aa0e.up.railway.app/v1/jobs?limit=1

# Should return 200 or 404, NOT 401
```

#### Step 4: Check for Key Truncation
Sometimes Railway truncates long values. Check:
- Is the full key visible in Railway dashboard?
- Try a shorter key (16-24 chars) to test

#### Step 5: Restart Railway Service
After setting/changing environment variables:
1. Go to Railway dashboard
2. Click "Deployments"
3. Click "Redeploy" or trigger a new deployment

### Quick Fix: Use Shorter Key

If the key is too long or has issues, try a shorter one:

```bash
# Generate shorter key
python3 -c "import secrets, string; print('docparser_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for i in range(16)))"
```

Then:
1. Set the shorter key in Railway as `DOCPARSER_API_KEY`
2. Restart the service
3. Test again

### Alternative: Check if Legacy Auth is Interfering

If middleware is enabled but still failing, the legacy `verify_api_key()` might be interfering. Check Railway logs for:
- "Verifying API key" messages (means legacy system is running)
- "Middleware already authenticated" messages (means middleware worked)

### Expected Behavior:

**With middleware enabled:**
- No key → 401 "Missing API key"
- Wrong key → 401 "Invalid API key"
- Correct key → 200/404/400 (not 401)

**Current behavior:**
- No key → 401 ✅ (middleware working)
- Correct key → 401 ❌ (key mismatch or middleware not checking correctly)

### Next Steps:

1. Check Railway logs for middleware startup message
2. Verify `DOCPARSER_API_KEY` value in Railway matches exactly
3. Try redeploying after setting variables
4. If still failing, try a shorter key

