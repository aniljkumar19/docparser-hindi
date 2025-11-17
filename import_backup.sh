#!/bin/bash
# Import backup.sql into Docker PostgreSQL

set -e

BACKUP_FILE="${1:-backup.sql}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file '$BACKUP_FILE' not found"
    echo ""
    echo "Usage: $0 [backup_file.sql]"
    exit 1
fi

echo "=== Importing Database Backup ==="
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo ""
    echo "Please install Docker first:"
    echo "  ./install_docker.sh"
    exit 1
fi

# Determine docker-compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose not found"
    exit 1
fi

# Start containers if not running
cd "$(dirname "$0")"
echo "Checking Docker containers..."
if ! $DOCKER_COMPOSE ps db 2>&1 | grep -q "Up"; then
    echo "Starting Docker containers..."
    $DOCKER_COMPOSE up -d db redis minio
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
else
    echo "✅ Containers are running"
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to accept connections..."
for i in {1..30}; do
    if PGPASSWORD=docpass psql -h localhost -p 55432 -U docuser -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL did not become ready in time"
        echo "   Check logs: $DOCKER_COMPOSE logs db"
        exit 1
    fi
    sleep 1
done

# Check if database exists, create if not
echo ""
echo "Checking database..."
export PGPASSWORD=docpass
if ! psql -h localhost -p 55432 -U docuser -d postgres -c "\l docdb" 2>&1 | grep -q "docdb"; then
    echo "Creating database 'docdb'..."
    psql -h localhost -p 55432 -U docuser -d postgres -c "CREATE DATABASE docdb;"
fi

# Import the backup
echo ""
echo "Importing backup..."
echo "This may take a moment..."

if psql -h localhost -p 55432 -U docuser -d docdb -f "$BACKUP_FILE" 2>&1; then
    echo ""
    echo "✅ Database import completed successfully!"
else
    echo ""
    echo "⚠️  Import completed with warnings (this is usually okay)"
fi

unset PGPASSWORD

# Verify import
echo ""
echo "Verifying import..."
export PGPASSWORD=docpass
echo "Tables in database:"
psql -h localhost -p 55432 -U docuser -d docdb -c "\dt" || true

echo ""
echo "Record counts:"
psql -h localhost -p 55432 -U docuser -d docdb -c "SELECT 'jobs' as table_name, COUNT(*) as count FROM jobs UNION ALL SELECT 'batches', COUNT(*) FROM batches UNION ALL SELECT 'clients', COUNT(*) FROM clients;" 2>/dev/null || echo "Could not count records (tables may not exist yet)"
unset PGPASSWORD

echo ""
echo "=== Import Complete ==="
echo ""
echo "Next steps:"
echo "1. Test connection: python3 test_db_connection.py"
echo "2. Start API: docker-compose up -d"
echo "3. View logs: docker-compose logs -f"
echo ""

