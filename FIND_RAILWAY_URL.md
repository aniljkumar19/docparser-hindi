# How to Find Your Railway Deployment URL

## Steps to Find Your Public URL:

1. **Go to Railway Dashboard**
   - Visit https://railway.app
   - Log in to your account

2. **Select Your Project**
   - Click on your "docparser" project

3. **Find the Service**
   - You should see your service (likely named "docparser" or similar)
   - Click on the service

4. **Get the Public URL**
   - Look for a section called **"Settings"** or **"Networking"**
   - Or check the **"Deployments"** tab
   - You should see a **"Generate Domain"** button or a domain already generated
   - The URL will look like: `https://docparser-production.up.railway.app` or `https://your-app-name.up.railway.app`

5. **Alternative: Check the Deployments Tab**
   - Click on the **"Deployments"** tab
   - Click on the latest deployment
   - The URL should be visible there

## If You Don't See a URL:

1. **Check if the service is running**
   - Make sure the deployment status shows "Active" or "Running"
   - If it shows errors, check the logs

2. **Generate a Domain**
   - Go to **Settings** → **Networking**
   - Click **"Generate Domain"** if no domain exists
   - Railway will create a public URL for you

3. **Check Service Settings**
   - Make sure the service is set to be publicly accessible
   - Some services might be private by default

## Test Your Deployment:

Once you have the URL, test it:

1. **Health Check**: `https://your-app.up.railway.app/health`
   - Should return JSON: `{"ok": true, "service": "Doc Parser API PRO", "version": "0.2.0"}`

2. **Landing Page**: `https://your-app.up.railway.app/`
   - Should show the styled API landing page

3. **API Docs**: `https://your-app.up.railway.app/docs`
   - Should show FastAPI interactive docs (if enabled)

## Common Issues:

- **Service not running**: Check deployment logs for errors
- **No domain generated**: Click "Generate Domain" in Settings
- **502/503 errors**: Service might be crashing - check logs
- **Connection refused**: Service might not be listening on the correct port

