# DocParser Local Database Setup Instructions

## Current Status

✅ PostgreSQL 16.10 is installed  
⚠️  Database needs to be created  
⚠️  Environment configuration needed  

## Step-by-Step Setup

### Step 1: Create PostgreSQL Database and User

You need to run these commands with sudo access. Choose one method:

**Method A: Using psql (Recommended)**
```bash
sudo -u postgres psql <<EOF
CREATE USER docuser WITH PASSWORD 'docpass';
CREATE DATABASE docdb OWNER docuser;
GRANT ALL PRIVILEGES ON DATABASE docdb TO docuser;
\q
EOF
```

**Method B: Using command line tools**
```bash
sudo -u postgres createuser -P docuser
# When prompted, enter password: docpass

sudo -u postgres createdb -O docuser docdb
```

**Method C: If you have passwordless sudo**
```bash
cd /home/vncuser/apps/docparser
./setup_postgres.sh
```

### Step 2: Verify Database Connection

```bash
export PGPASSWORD=docpass
psql -h localhost -U docuser -d docdb -c "SELECT version();"
unset PGPASSWORD
```

### Step 3: Create Environment File

Create `api/.env` file:

```bash
cd /home/vncuser/apps/docparser/api
cat > .env <<EOF
# Database Configuration
DB_URL=postgresql://docuser:docpass@localhost:5432/docdb

# Redis Configuration
REDIS_URL=redis://localhost:6379

# S3/MinIO Configuration
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_REGION=us-east-1
S3_BUCKET=docparser
S3_SECURE=false

# API Keys
API_KEYS=dev_123:tenant_demo

# File Upload Limits
MAX_FILE_MB=15
EOF
```

### Step 4: Test Database Connection

```bash
cd /home/vncuser/apps/docparser
python3 test_db_connection.py
```

This will:
- Test the database connection
- Show existing tables
- Initialize schema if tables are missing

### Step 5: Import Your Database Dump

Once the database is set up, import your exported database:

```bash
# If you have a SQL dump file
./import_db.sh your_database_dump.sql

# Or manually:
export PGPASSWORD=docpass
psql -h localhost -U docuser -d docdb < your_database_dump.sql
unset PGPASSWORD
```

### Step 6: Verify Import

```bash
export PGPASSWORD=docpass
psql -h localhost -U docuser -d docdb -c "\dt"
psql -h localhost -U docuser -d docdb -c "SELECT COUNT(*) FROM jobs;"
unset PGPASSWORD
```

## Quick Reference

**Database Details:**
- Host: localhost
- Port: 5432
- Database: docdb
- User: docuser
- Password: docpass
- Connection String: `postgresql://docuser:docpass@localhost:5432/docdb`

**Useful Commands:**

```bash
# Connect to database
psql -h localhost -U docuser -d docdb

# List tables
psql -h localhost -U docuser -d docdb -c "\dt"

# Check table structure
psql -h localhost -U docuser -d docdb -c "\d jobs"

# Count records
psql -h localhost -U docuser -d docdb -c "SELECT COUNT(*) FROM jobs;"

# Export database
./export_db.sh backup.sql

# Import database
./import_db.sh backup.sql
```

## Troubleshooting

### Issue: "Peer authentication failed"

**Solution:** Use host-based connection:
```bash
psql -h localhost -U docuser -d docdb
```

### Issue: "Database does not exist"

**Solution:** Create the database:
```bash
sudo -u postgres createdb -O docuser docdb
```

### Issue: "Permission denied"

**Solution:** Grant privileges:
```bash
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE docdb TO docuser;"
```

### Issue: PostgreSQL not running

**Solution:** Start PostgreSQL:
```bash
sudo systemctl start postgresql
# or
sudo service postgresql start
```

## Next Steps After Setup

1. ✅ Database created and configured
2. ✅ Environment file created
3. ✅ Database imported
4. ✅ Test application: `cd api && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Questions?

If you encounter any issues, check:
- PostgreSQL service status
- Database user permissions
- Environment variables
- Network connectivity (if using remote database)

