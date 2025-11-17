# Frontend Started! 🎉

## Frontend Dashboard

The Next.js frontend is now running!

### Access the Dashboard

**URL:** http://localhost:3000

### Features Available

1. **Single Document Upload** (`/`)
   - Upload and parse individual documents
   - View parsing results
   - See document type detection with confidence scores

2. **Bulk Upload** (`/bulk-upload`)
   - Upload multiple documents (up to 100 files)
   - Track batch processing progress
   - Export results (JSON, CSV, Tally CSV)

### API Proxy

The frontend automatically proxies API requests:
- Frontend: `http://localhost:3000/backend/*`
- Backend: `http://localhost:8000/*`

### Stop the Frontend

Press `Ctrl+C` in the terminal where it's running, or:

```bash
# Find and kill the process
pkill -f "next dev"
```

### Restart the Frontend

```bash
cd /home/vncuser/apps/docparser/dashboard
node_modules/.bin/next dev -p 3000
```

Or use the script:
```bash
./start_frontend.sh
```

### Troubleshooting

If the frontend doesn't load:
1. Check if it's running: `curl http://localhost:3000`
2. Check for errors in the terminal
3. Make sure the backend API is running: `curl http://localhost:8000/`

### Full Stack Status

✅ **Backend API**: http://localhost:8000  
✅ **Frontend Dashboard**: http://localhost:3000  
✅ **Database**: PostgreSQL (port 55432)  
✅ **Redis**: Port 6379  
✅ **MinIO**: Ports 9000, 9001  

Everything is running! 🚀

