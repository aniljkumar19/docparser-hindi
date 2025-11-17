#!/bin/bash
# Import database dump into PostgreSQL

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <database_dump_file.sql>"
    echo ""
    echo "This script will import your database dump into the local PostgreSQL database."
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

# Database configuration
DB_NAME="docdb"
DB_USER="docuser"
DB_PASSWORD="docpass"
DB_HOST="localhost"
DB_PORT="5432"

echo "=== Database Import ==="
echo ""
echo "Dump file: $DUMP_FILE"
echo "Database: $DB_NAME"
echo ""

# Check if database exists
export PGPASSWORD=$DB_PASSWORD
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "\l $DB_NAME" | grep -q "$DB_NAME"; then
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

