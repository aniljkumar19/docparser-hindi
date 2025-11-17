#!/bin/bash
# Export from local PostgreSQL instance

set -e

# Default values - adjust if needed
DB_NAME="${1:-docdb}"
DB_USER="${2:-docuser}"
DB_HOST="${3:-localhost}"
DB_PORT="${4:-5432}"

OUTPUT_FILE="docparser_postgres_export_$(date +%Y%m%d_%H%M%S).sql"

echo "=== Exporting from Local PostgreSQL ==="
echo ""
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo "Output: $OUTPUT_FILE"
echo ""

# Check if database exists
export PGPASSWORD="${5:-docpass}"
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "\l $DB_NAME" 2>&1 | grep -q "$DB_NAME"; then
    echo "⚠️  Database '$DB_NAME' not found."
    echo ""
    echo "Available databases:"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "\l" || true
    echo ""
    echo "Usage: $0 [database_name] [user] [host] [port] [password]"
    exit 1
fi

# Export database
echo "Exporting database..."
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F p -f "$OUTPUT_FILE"

unset PGPASSWORD

echo ""
echo "✅ Export completed!"
echo ""
echo "File: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "To import into Docker PostgreSQL:"
echo "  ./import_docker_db.sh $OUTPUT_FILE"
echo ""

