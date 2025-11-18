# Railway Restart Required After Adding ADMIN_TOKEN

## The Issue

You've set `ADMIN_TOKEN` in Railway, but you're getting:
```
"ADMIN_TOKEN not configured"
```

## Why This Happens

Railway needs to **restart the service** to pick up new environment variables. The running container still has the old environment (without `ADMIN_TOKEN`).

## How to Fix

### Option 1: Manual Restart (Easiest)

1. Go to Railway dashboard
2. Click on your service
3. Click the **"Deploy"** tab (or find the restart button)
4. Click **"Redeploy"** or **"Restart"**

This will restart the service and load the new `ADMIN_TOKEN`.

### Option 2: Trigger Redeploy

1. Make a small code change (add a comment)
2. Commit and push to GitHub
3. Railway will auto-redeploy and pick up the new variable

### Option 3: Wait for Auto-Redeploy

Sometimes Railway auto-redeploys when variables change, but it's not guaranteed. Manual restart is more reliable.

## Verify It's Working

After restart, test the debug endpoint:

```bash
curl https://your-railway-url.com/debug/api-keys
```

Look for:
```json
{
  "ADMIN_TOKEN_configured": true,
  "ADMIN_TOKEN_length": 10,
  "ADMIN_TOKEN_preview": "toke..."
}
```

If `ADMIN_TOKEN_configured` is `true`, you're good to go!

## Then Try Creating a Key

In the dashboard:
1. Enter your admin token: `token_4466`
2. Click "Enable" (Admin Mode)
3. Click "+ Create Key"
4. Enter a name
5. Should work now! ✅

---

## Quick Checklist

- [ ] Set `ADMIN_TOKEN` in Railway ✅ (You did this)
- [ ] Restart Railway service ⚠️ (Do this now)
- [ ] Verify with `/debug/api-keys` endpoint
- [ ] Try creating a key in the GUI

