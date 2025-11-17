#!/bin/bash
# Quick start script for DocParser with Docker

set -e

echo "=== DocParser Quick Start ==="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo ""
    echo "Please run: ./install_docker.sh"
    echo "Then log out and back in, or run: newgrp docker"
    exit 1
fi

# Check if user is in docker group
if ! groups | grep -q docker; then
    echo "⚠️  You are not in the docker group."
    echo "   Run: sudo usermod -aG docker $USER"
    echo "   Then log out and back in, or run: newgrp docker"
    echo ""
    echo "Trying to continue anyway (may require sudo)..."
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

echo "✅ Using: $DOCKER_COMPOSE"
echo ""

# Start containers
echo "Starting Docker containers..."
cd "$(dirname "$0")"

if $DOCKER_COMPOSE up -d db redis minio; then
    echo "✅ Containers started successfully!"
else
    echo "❌ Failed to start containers"
    echo "   Trying with sudo..."
    sudo $DOCKER_COMPOSE up -d db redis minio
fi

# Wait for PostgreSQL to be ready
echo ""
echo "Waiting for PostgreSQL to be ready..."
sleep 5

for i in {1..30}; do
    if PGPASSWORD=docpass psql -h localhost -p 55432 -U docuser -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  PostgreSQL did not become ready in time"
        echo "   Check logs with: docker-compose logs db"
    fi
    sleep 1
done

# Test connection
echo ""
echo "Testing database connection..."
if python3 test_db_connection.py; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Import your database: ./import_docker_db.sh <your_dump.sql>"
    echo "2. Start all services: docker-compose up -d"
    echo "3. View logs: docker-compose logs -f"
else
    echo ""
    echo "⚠️  Database connection test failed"
    echo "   But containers are running. You can still import your database."
fi

echo ""
echo "=== Quick Start Complete ==="

