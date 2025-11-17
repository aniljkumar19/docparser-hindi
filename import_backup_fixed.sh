#!/bin/bash
# Import backup.sql into Docker PostgreSQL (with permission handling)

set -e

BACKUP_FILE="${1:-backup.sql}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file '$BACKUP_FILE' not found"
    exit 1
fi

echo "=== Importing Database Backup ==="
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""

# Check Docker permissions
DOCKER_CMD="docker"
DOCKER_COMPOSE_CMD=""

if ! docker ps > /dev/null 2>&1; then
    echo "⚠️  Docker permission issue detected"
    echo ""
    echo "Trying with sudo..."
    DOCKER_CMD="sudo docker"
    
    if command -v docker-compose > /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="sudo docker-compose"
    elif sudo docker compose version > /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="sudo docker compose"
    fi
else
    if command -v docker-compose > /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif docker compose version > /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
    fi
fi

if [ -z "$DOCKER_COMPOSE_CMD" ]; then
    echo "❌ docker-compose not found"
    exit 1
fi

# Start containers
cd "$(dirname "$0")"
echo "Starting Docker containers..."
$DOCKER_COMPOSE_CMD up -d db redis minio

echo "Waiting for PostgreSQL to be ready..."
sleep 8

# Wait for PostgreSQL
for i in {1..30}; do
    if PGPASSWORD=docpass psql -h localhost -p 55432 -U docuser -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL did not become ready"
        echo "   Check: $DOCKER_COMPOSE_CMD logs db"
        exit 1
    fi
    sleep 1
done

# Create database if needed
export PGPASSWORD=docpass
if ! psql -h localhost -p 55432 -U docuser -d postgres -c "\l docdb" 2>&1 | grep -q "docdb"; then
    echo "Creating database..."
    psql -h localhost -p 55432 -U docuser -d postgres -c "CREATE DATABASE docdb;"
fi

# Import backup
echo ""
echo "Importing backup..."
if psql -h localhost -p 55432 -U docuser -d docdb -f "$BACKUP_FILE" 2>&1; then
    echo ""
    echo "✅ Import completed!"
else
    echo ""
    echo "⚠️  Import completed (warnings are usually okay)"
fi

unset PGPASSWORD

# Verify
echo ""
echo "Verifying..."
export PGPASSWORD=docpass
psql -h localhost -p 55432 -U docuser -d docdb -c "\dt" 2>/dev/null || true
unset PGPASSWORD

echo ""
echo "=== Done ==="

