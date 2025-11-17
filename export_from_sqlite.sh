#!/bin/bash
# Export SQLite database to PostgreSQL-compatible SQL

set -e

SQLITE_DB="api/data.db"
OUTPUT_FILE="${1:-docparser_sqlite_export_$(date +%Y%m%d_%H%M%S).sql}"

if [ ! -f "$SQLITE_DB" ]; then
    echo "❌ SQLite database not found: $SQLITE_DB"
    exit 1
fi

echo "=== Exporting SQLite Database ==="
echo ""
echo "Source: $SQLITE_DB"
echo "Output: $OUTPUT_FILE"
echo ""

# Check if sqlite3 is installed
if ! command -v sqlite3 &> /dev/null; then
    echo "Installing sqlite3..."
    sudo apt install -y sqlite3
fi

# Export schema and data
echo "Exporting database..."
sqlite3 "$SQLITE_DB" .dump > "$OUTPUT_FILE"

# Basic PostgreSQL compatibility fixes
echo "Converting to PostgreSQL-compatible format..."
sed -i 's/INTEGER PRIMARY KEY AUTOINCREMENT/SERIAL PRIMARY KEY/g' "$OUTPUT_FILE"
sed -i 's/INTEGER PRIMARY KEY/SERIAL PRIMARY KEY/g' "$OUTPUT_FILE"
sed -i 's/INTEGER/SERIAL/g' "$OUTPUT_FILE"
sed -i '/^PRAGMA/d' "$OUTPUT_FILE"
sed -i '/^BEGIN TRANSACTION/d' "$OUTPUT_FILE"
sed -i '/^COMMIT/d' "$OUTPUT_FILE"

echo ""
echo "✅ Export completed!"
echo ""
echo "File: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo ""
echo "⚠️  Note: This is a basic conversion. You may need to review and adjust:"
echo "   - Data types"
echo "   - Constraints"
echo "   - Indexes"
echo ""
echo "To import:"
echo "  ./import_docker_db.sh $OUTPUT_FILE"
echo ""

