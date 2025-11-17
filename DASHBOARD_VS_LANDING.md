# Landing Page vs Dashboard - Explanation

## Two Different Things:

### 1. **Landing Page** (API Documentation Page)
- **URL**: `https://docparser-production-aa0e.up.railway.app/`
- **What it is**: The styled HTML page that shows API documentation, endpoints, and status
- **Purpose**: For developers to understand the API, see available endpoints, and check health
- **Location**: Served by FastAPI backend at the root `/` route
- **Status**: ✅ Already deployed on Railway

### 2. **Dashboard** (User Interface for Document Upload)
- **URL**: Currently only runs locally at `http://localhost:3000/dashboard`
- **What it is**: A React/Next.js web application for:
  - Uploading documents (PDFs, CSVs)
  - Viewing parsed results
  - Seeing reconciliations (GSTR-3B, GSTR-1)
  - Exporting data (CSV, JSON, Tally XML)
  - Viewing job history
- **Purpose**: For end users (CAs, accountants) to interact with the system
- **Location**: Separate Next.js application in `/dashboard` folder
- **Status**: ⚠️ Not yet deployed - only runs locally

## How to Access Dashboard Locally:

1. **Start the dashboard** (in a separate terminal):
   ```bash
   cd /home/vncuser/apps/docparser/dashboard
   npm run dev
   ```

2. **Access it**: Open `http://localhost:3000/dashboard` in your browser

3. **Make sure API is running**: The dashboard needs the API to be running at `http://localhost:8000` (or set `NEXT_PUBLIC_DOCPARSER_API_BASE` environment variable)

## Deploying the Dashboard:

The dashboard needs to be deployed separately. Options:

### Option 1: Deploy Dashboard on Railway (Recommended)
1. Create a new Railway service for the dashboard
2. Point it to the `dashboard/` folder
3. Set environment variable: `NEXT_PUBLIC_DOCPARSER_API_BASE=https://docparser-production-aa0e.up.railway.app`
4. Railway will give you a URL like: `https://docparser-dashboard.up.railway.app`
5. Set `FRONTEND_URL=https://docparser-dashboard.up.railway.app` in your API service

### Option 2: Deploy Dashboard on Vercel (Easiest for Next.js)
1. Push code to GitHub (already done)
2. Go to https://vercel.com
3. Import your GitHub repository
4. Set root directory to `dashboard`
5. Add environment variable: `NEXT_PUBLIC_DOCPARSER_API_BASE=https://docparser-production-aa0e.up.railway.app`
6. Deploy - Vercel will give you a URL
7. Set `FRONTEND_URL=<vercel-url>` in your Railway API service

### Option 3: Deploy Dashboard on Railway (Same Project)
1. In your Railway project, add a new service
2. Connect it to the same GitHub repo
3. Set root directory to `dashboard`
4. Railway will auto-detect it's a Next.js app
5. Set environment variable: `NEXT_PUBLIC_DOCPARSER_API_BASE=https://docparser-production-aa0e.up.railway.app`
6. Railway will give you a URL for the dashboard
7. Set `FRONTEND_URL=<dashboard-railway-url>` in your API service

## Summary:

- **Landing Page** = API documentation (already deployed) ✅
- **Dashboard** = User interface for uploading/viewing documents (needs deployment) ⚠️
- **FRONTEND_URL** = The URL where you deploy the dashboard (not the landing page)

## Current Status:

✅ **Landing Page**: Deployed at `https://docparser-production-aa0e.up.railway.app/`
⚠️ **Dashboard**: Only runs locally at `http://localhost:3000/dashboard` (needs deployment)

