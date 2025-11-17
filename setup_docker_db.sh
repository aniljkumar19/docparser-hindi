#!/bin/bash
# Setup script for Docker-based PostgreSQL database for DocParser

set -e

echo "=== DocParser Docker PostgreSQL Setup ==="
echo ""

# Database configuration (matching docker-compose.yml)
DB_NAME="docdb"
DB_USER="docuser"
DB_PASSWORD="docpass"
DB_HOST="localhost"
DB_PORT="55432"  # Docker PostgreSQL port

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo ""
    echo "Please install Docker first:"
    echo "  sudo apt install docker.io docker-compose"
    echo "  sudo systemctl start docker"
    echo "  sudo usermod -aG docker $USER"
    echo ""
    echo "Then log out and log back in, or run: newgrp docker"
    exit 1
fi

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ docker-compose is not available"
    exit 1
fi

echo "✅ Docker is installed"
echo ""

# Check if containers are running
cd "$(dirname "$0")"
if $DOCKER_COMPOSE ps db | grep -q "Up"; then
    echo "✅ PostgreSQL container is running"
else
    echo "⚠️  PostgreSQL container is not running"
    echo "Starting Docker containers..."
    $DOCKER_COMPOSE up -d db redis minio
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to accept connections..."
for i in {1..30}; do
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL did not become ready in time"
        exit 1
    fi
    sleep 1
done

# Test connection
echo ""
echo "Testing database connection..."
export PGPASSWORD=$DB_PASSWORD
if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ Database connection successful!"
    echo ""
    echo "Database Details:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT (Docker mapped port)"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo ""
    echo "Connection string: postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
else
    echo "⚠️  Database '$DB_NAME' might not exist yet. It will be created on first use."
fi

unset PGPASSWORD

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Update your api/.env file with: DB_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
echo "2. Import your database dump using: ./import_docker_db.sh <your_dump_file.sql>"
echo "3. Start all services: docker-compose up -d"
echo ""

