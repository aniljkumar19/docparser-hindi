# Restart API to Fix Bulk Upload

The bulk-parse endpoint exists in the code but the API server needs to be restarted.

## Quick Fix

```bash
cd /home/vncuser/apps/docparser

# Restart the API container
sudo docker-compose restart api

# Wait a few seconds
sleep 5

# Test the endpoint
curl -X POST "http://localhost:8000/v1/bulk-parse" \
  -H "Authorization: Bearer dev_123" \
  -F "files=@api/samples/sample_invoice.txt"
```

## Or Restart All Services

```bash
sudo docker-compose restart
```

## Verify It's Working

After restart, check:
```bash
# Should show bulk-parse in the docs
curl -s http://localhost:8000/docs | grep bulk-parse

# Or test directly
curl -X POST "http://localhost:8000/v1/bulk-parse" \
  -H "Authorization: Bearer dev_123" \
  -F "files=@api/samples/sample_invoice.txt"
```

The endpoint should work after restart!

