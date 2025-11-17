#!/bin/bash
# Export database from PostgreSQL

set -e

# Database configuration
DB_NAME="docdb"
DB_USER="docuser"
DB_PASSWORD="docpass"
DB_HOST="localhost"
DB_PORT="5432"

OUTPUT_FILE="${1:-docparser_backup_$(date +%Y%m%d_%H%M%S).sql}"

echo "=== Database Export ==="
echo ""
echo "Database: $DB_NAME"
echo "Output file: $OUTPUT_FILE"
echo ""

export PGPASSWORD=$DB_PASSWORD

# Check if database exists
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "\l $DB_NAME" | grep -q "$DB_NAME"; then
    echo "❌ Error: Database '$DB_NAME' does not exist"
    exit 1
fi

# Export database
echo "Exporting database..."
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F p -f "$OUTPUT_FILE"

unset PGPASSWORD

echo ""
echo "✅ Database exported successfully!"
echo ""
echo "File: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "To import this file later, use:"
echo "  ./import_db.sh $OUTPUT_FILE"
echo ""

