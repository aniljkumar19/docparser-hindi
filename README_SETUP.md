# Database Setup Summary

## ✅ What I've Done

1. **Fixed Code Issues:**
   - Added missing `Integer` import to `api/app/db.py` (needed for Batch model)
   - Added missing `text` import for SQL queries
   - Fixed database query methods

2. **Created Setup Scripts:**
   - `setup_postgres.sh` - Automated PostgreSQL setup
   - `import_db.sh` - Import your database dump
   - `export_db.sh` - Export database for backup
   - `test_db_connection.py` - Test database connection and initialize schema

3. **Created Documentation:**
   - `SETUP_INSTRUCTIONS.md` - Step-by-step setup guide
   - `DATABASE_SETUP.md` - Detailed database setup guide

## 📋 What You Need to Do

### Step 1: Create PostgreSQL Database

Run this command (requires sudo):

```bash
sudo -u postgres psql <<EOF
CREATE USER docuser WITH PASSWORD 'docpass';
CREATE DATABASE docdb OWNER docuser;
GRANT ALL PRIVILEGES ON DATABASE docdb TO docuser;
\q
EOF
```

**OR** use the automated script:
```bash
cd /home/vncuser/apps/docparser
./setup_postgres.sh
```

### Step 2: Create Environment File

Create `api/.env` file with database configuration:

```bash
cd /home/vncuser/apps/docparser/api
cat > .env <<'EOF'
DB_URL=postgresql://docuser:docpass@localhost:5432/docdb
REDIS_URL=redis://localhost:6379
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_REGION=us-east-1
S3_BUCKET=docparser
S3_SECURE=false
API_KEYS=dev_123:tenant_demo
MAX_FILE_MB=15
EOF
```

### Step 3: Test Database Connection

```bash
cd /home/vncuser/apps/docparser
python3 test_db_connection.py
```

This will:
- Test the connection
- Show existing tables
- Create tables if they don't exist

### Step 4: Import Your Database

Once you have your database dump file:

```bash
./import_db.sh your_database_dump.sql
```

**OR** manually:
```bash
export PGPASSWORD=docpass
psql -h localhost -U docuser -d docdb < your_database_dump.sql
unset PGPASSWORD
```

## 🔍 Verify Everything Works

```bash
# Test connection
export PGPASSWORD=docpass
psql -h localhost -U docuser -d docdb -c "SELECT COUNT(*) FROM jobs;"
unset PGPASSWORD

# Or use the test script
python3 test_db_connection.py
```

## 📝 Database Configuration

- **Host:** localhost
- **Port:** 5432
- **Database:** docdb
- **User:** docuser
- **Password:** docpass
- **Connection String:** `postgresql://docuser:docpass@localhost:5432/docdb`

## 🆘 Need Help?

Check `SETUP_INSTRUCTIONS.md` for detailed troubleshooting steps.

## 📦 Files Created

- `setup_postgres.sh` - Database setup script
- `import_db.sh` - Database import script
- `export_db.sh` - Database export script
- `test_db_connection.py` - Connection test script
- `SETUP_INSTRUCTIONS.md` - Detailed setup guide
- `DATABASE_SETUP.md` - Database setup documentation

## ✅ Ready to Import

Once you've completed steps 1-3 above, you're ready to import your database dump!

