# Database Setup Guide

This guide will help you set up PostgreSQL locally for the DocParser project.

## Prerequisites

- PostgreSQL 15+ installed (✅ Already installed: version 16.10)
- PostgreSQL service running

## Quick Setup

### Option 1: Automated Setup (Requires sudo access)

```bash
cd /home/vncuser/apps/docparser
./setup_postgres.sh
```

### Option 2: Manual Setup

If you don't have sudo access or prefer manual setup, run these commands:

```bash
# Connect to PostgreSQL as postgres user
sudo -u postgres psql

# Then run these SQL commands:
CREATE USER docuser WITH PASSWORD 'docpass';
CREATE DATABASE docdb OWNER docuser;
GRANT ALL PRIVILEGES ON DATABASE docdb TO docuser;
\q
```

### Option 3: Using psql directly (if you have postgres user access)

```bash
# Create user
sudo -u postgres createuser -P docuser
# Enter password when prompted: docpass

# Create database
sudo -u postgres createdb -O docuser docdb
```

## Verify Setup

Test the connection:

```bash
export PGPASSWORD=docpass
psql -h localhost -U docuser -d docdb -c "SELECT version();"
unset PGPASSWORD
```

## Environment Configuration

Create or update `api/.env` file with:

```bash
# Database Configuration
DB_URL=postgresql://docuser:docpass@localhost:5432/docdb

# Redis Configuration (if running locally)
REDIS_URL=redis://localhost:6379

# S3/MinIO Configuration
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_REGION=us-east-1
S3_BUCKET=docparser
S3_SECURE=false

# API Keys (format: key1:tenant1,key2:tenant2)
API_KEYS=dev_123:tenant_demo

# Stripe Configuration (optional)
STRIPE_API_KEY=
STRIPE_PRICE_ID=
STRIPE_SUBSCRIPTION_ITEMS=

# File Upload Limits
MAX_FILE_MB=15
```

## Import Your Database

Once the database is set up, import your exported database:

```bash
# If you have a SQL dump file
./import_db.sh your_database_dump.sql

# Or manually:
export PGPASSWORD=docpass
psql -h localhost -U docuser -d docdb < your_database_dump.sql
unset PGPASSWORD
```

## Export Database (for backup)

```bash
./export_db.sh [output_filename.sql]
```

## Database Schema

The application will automatically create tables on first run via SQLAlchemy:

- `jobs` - Document parsing jobs
- `batches` - Bulk processing batches
- `clients` - Client management (for CA firms)

## Troubleshooting

### Connection Issues

1. **Check PostgreSQL is running:**
   ```bash
   sudo systemctl status postgresql
   ```

2. **Check PostgreSQL port:**
   ```bash
   sudo netstat -tlnp | grep 5432
   ```

3. **Check pg_hba.conf for authentication:**
   ```bash
   sudo cat /etc/postgresql/*/main/pg_hba.conf | grep -v "^#"
   ```

### Permission Issues

If you get "Peer authentication failed":
- Use password authentication: `psql -h localhost -U docuser -d docdb`
- Or update pg_hba.conf to use md5 instead of peer

### Database Already Exists

If the database already exists, you can:
- Drop and recreate: `DROP DATABASE docdb; CREATE DATABASE docdb OWNER docuser;`
- Or just import your dump directly

## Next Steps

1. ✅ Set up PostgreSQL database
2. ✅ Create `.env` file with database URL
3. ✅ Import your database dump
4. ✅ Test the application: `cd api && python -m app.main` (or use docker-compose)

