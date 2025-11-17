#!/bin/bash
# Find and export database from various sources

set -e

echo "=== Database Finder & Exporter ==="
echo ""

# Check SQLite database
if [ -f "api/data.db" ]; then
    echo "✅ Found SQLite database: api/data.db"
    echo "   Size: $(du -h api/data.db | cut -f1)"
    echo "   Last modified: $(stat -c %y api/data.db | cut -d' ' -f1)"
    echo ""
    echo "To export from SQLite:"
    echo "  ./export_from_sqlite.sh"
    echo ""
fi

# Check local PostgreSQL
echo "Checking local PostgreSQL..."
if pg_isready -h localhost > /dev/null 2>&1; then
    echo "✅ PostgreSQL is running locally"
    echo ""
    echo "To list databases, run:"
    echo "  psql -h localhost -U postgres -d postgres -c '\l'"
    echo ""
    echo "To export from local PostgreSQL:"
    echo "  ./export_from_local_postgres.sh [database_name] [user] [host] [port] [password]"
    echo "  Example: ./export_from_local_postgres.sh docdb docuser localhost 5432 docpass"
    echo ""
else
    echo "⚠️  PostgreSQL is not running locally"
    echo ""
fi

# Check Docker containers
if command -v docker &> /dev/null; then
    echo "Checking Docker containers..."
    if docker ps -a | grep -q postgres; then
        echo "✅ Found PostgreSQL Docker containers"
        docker ps -a | grep postgres
        echo ""
        echo "To export from Docker container:"
        echo "  docker exec <container_name> pg_dump -U docuser docdb > dump.sql"
        echo ""
    else
        echo "⚠️  No PostgreSQL Docker containers found"
        echo ""
    fi
else
    echo "⚠️  Docker not installed (containers might exist but can't check)"
    echo ""
fi

echo "=== Summary ==="
echo ""
echo "You have these options:"
echo ""
echo "1. SQLite database (api/data.db):"
echo "   ./export_from_sqlite.sh"
echo ""
echo "2. Local PostgreSQL:"
echo "   ./export_from_local_postgres.sh docdb docuser localhost 5432 docpass"
echo ""
echo "3. Docker PostgreSQL (if containers exist):"
echo "   docker exec <container_name> pg_dump -U docuser docdb > dump.sql"
echo ""
echo "After exporting, import with:"
echo "   ./import_docker_db.sh <your_dump_file.sql>"
echo ""

