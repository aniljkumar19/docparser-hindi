#!/bin/bash
# Import database dump into Docker-based PostgreSQL

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <database_dump_file.sql>"
    echo ""
    echo "This script will import your database dump into the Docker PostgreSQL database."
    echo ""
    echo "Supported formats:"
    echo "  - SQL dump files (.sql)"
    echo "  - Custom format dumps (.dump) - use pg_restore"
    echo ""
    exit 1
fi

DUMP_FILE="$1"

if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ Error: File '$DUMP_FILE' not found"
    exit 1
fi

# Database configuration (Docker-based)
DB_NAME="docdb"
DB_USER="docuser"
DB_PASSWORD="docpass"
DB_HOST="localhost"
DB_PORT="55432"  # Docker PostgreSQL port

echo "=== Database Import (Docker PostgreSQL) ==="
echo ""
echo "Dump file: $DUMP_FILE"
echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo ""

# Check if Docker container is running
if ! docker ps | grep -q "docparser.*postgres"; then
    echo "⚠️  PostgreSQL container is not running."
    echo "Starting Docker containers..."
    cd "$(dirname "$0")"
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d db
    elif docker compose version &> /dev/null; then
        docker compose up -d db
    else
        echo "❌ docker-compose not found"
        exit 1
    fi
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to accept connections..."
for i in {1..30}; do
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL did not become ready in time"
        exit 1
    fi
    sleep 1
done

# Check if database exists
export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "\l $DB_NAME" 2>&1 | grep -q "$DB_NAME"; then
    echo "⚠️  Database '$DB_NAME' does not exist. Creating it..."
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;"
fi

# Determine file type and import accordingly
if [[ "$DUMP_FILE" == *.dump ]] || [[ "$DUMP_FILE" == *.custom ]]; then
    echo "Detected custom format dump. Using pg_restore..."
    pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -v "$DUMP_FILE"
else
    echo "Detected SQL dump. Using psql..."
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$DUMP_FILE"
fi

unset PGPASSWORD

echo ""
echo "✅ Database import completed!"
echo ""
echo "Verifying import..."
export PGPASSWORD=$DB_PASSWORD
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt" || true
unset PGPASSWORD

echo ""
echo "=== Import Complete ==="

