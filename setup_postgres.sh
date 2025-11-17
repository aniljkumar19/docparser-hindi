#!/bin/bash
# Setup script for PostgreSQL database for DocParser

set -e

echo "=== DocParser PostgreSQL Setup ==="
echo ""

# Database configuration (matching docker-compose.yml)
DB_NAME="docdb"
DB_USER="docuser"
DB_PASSWORD="docpass"
DB_HOST="localhost"
DB_PORT="5432"

# Check if PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "❌ PostgreSQL is not running. Starting PostgreSQL..."
    sudo systemctl start postgresql || service postgresql start
    sleep 2
fi

echo "✅ PostgreSQL is running"
echo ""

# Check if we can connect as postgres user
echo "Setting up database and user..."

# Create a temporary SQL script
SQL_FILE=$(mktemp)
cat > "$SQL_FILE" <<EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
        RAISE NOTICE 'User $DB_USER created';
    ELSE
        RAISE NOTICE 'User $DB_USER already exists';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER DATABASE $DB_NAME OWNER TO $DB_USER;
EOF

# Try to execute as postgres user (requires sudo)
echo "Creating database and user..."
if sudo -u postgres psql -f "$SQL_FILE" 2>&1; then
    echo "✅ Database and user created successfully"
else
    echo "⚠️  Could not create database as postgres user. Trying alternative method..."
    # Alternative: try to connect directly
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ Database connection works"
    else
        echo "⚠️  Please run the following commands manually as postgres user:"
        echo ""
        echo "sudo -u postgres psql <<EOF"
        echo "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
        echo "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
        echo "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
        echo "EOF"
        echo ""
    fi
fi

rm -f "$SQL_FILE"

# Test connection
echo ""
echo "Testing database connection..."
export PGPASSWORD=$DB_PASSWORD
if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ Database connection successful!"
    echo ""
    echo "Database Details:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo ""
    echo "Connection string: postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
else
    echo "❌ Database connection failed. Please check PostgreSQL setup."
    exit 1
fi

unset PGPASSWORD

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Update your .env file with: DB_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
echo "2. Import your database dump using: ./import_db.sh <your_dump_file.sql>"
echo ""

