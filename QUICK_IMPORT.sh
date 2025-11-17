#!/bin/bash
# Quick import script - run this with sudo if needed

set -e

echo "=== Quick Database Import ==="
echo ""

# Determine if we need sudo
if docker ps > /dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
    DOCKER="docker"
else
    DOCKER_COMPOSE="sudo docker-compose"
    DOCKER="sudo docker"
fi

echo "Starting containers..."
$DOCKER_COMPOSE up -d db redis minio

echo "Waiting for PostgreSQL (10 seconds)..."
sleep 10

echo "Creating database (if needed)..."
export PGPASSWORD=docpass
psql -h localhost -p 55432 -U docuser -d postgres -c "CREATE DATABASE docdb;" 2>/dev/null || echo "Database may already exist"

echo "Importing backup.sql..."
psql -h localhost -p 55432 -U docuser -d docdb -f backup.sql

echo ""
echo "✅ Import complete!"
echo ""
echo "Verifying..."
psql -h localhost -p 55432 -U docuser -d docdb -c "\dt"

unset PGPASSWORD

echo ""
echo "Done! Test with: python3 test_db_connection.py"

