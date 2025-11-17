#!/bin/bash
# Fix API key configuration

echo "=== Fixing API Keys ==="
echo ""

cd "$(dirname "$0")/api"

# Check current .env
if [ -f ".env" ]; then
    echo "Current .env file:"
    grep API_KEYS .env || echo "  API_KEYS not found"
else
    echo "⚠️  .env file not found"
fi

echo ""
echo "Adding API_KEYS to .env file..."

# Add API_KEYS if not present
if ! grep -q "^API_KEYS=" .env 2>/dev/null; then
    echo "" >> .env
    echo "# API Keys (format: key1:tenant1,key2:tenant2)" >> .env
    echo "API_KEYS=dev_123:tenant_demo" >> .env
    echo "✅ Added API_KEYS to .env"
else
    # Update existing
    sed -i 's/^API_KEYS=.*/API_KEYS=dev_123:tenant_demo/' .env
    echo "✅ Updated API_KEYS in .env"
fi

echo ""
echo "Current API_KEYS configuration:"
grep API_KEYS .env

echo ""
echo "⚠️  You need to restart the API for this to take effect:"
echo "   sudo docker-compose restart api"
echo ""
echo "Or the API will reload keys on next request (if reload_api_keys is called)"

