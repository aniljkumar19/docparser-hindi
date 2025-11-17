# Import backup.sql - Instructions

You have `backup.sql` ready to import. Here's how:

## Option 1: Fix Docker Permissions (Recommended)

Add yourself to docker group (then log out/in):

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Then run:
```bash
./import_backup.sh backup.sql
```

## Option 2: Use Sudo (Quick Fix)

Run the import with sudo:

```bash
# Start containers
sudo docker-compose up -d db redis minio

# Wait a few seconds for PostgreSQL to start
sleep 10

# Import the backup
export PGPASSWORD=docpass
psql -h localhost -p 55432 -U docuser -d postgres -c "CREATE DATABASE docdb;" 2>/dev/null || true
psql -h localhost -p 55432 -U docuser -d docdb -f backup.sql
unset PGPASSWORD

# Verify
psql -h localhost -p 55432 -U docuser -d docdb -c "\dt"
```

## Option 3: Use the Fixed Script

I created a script that handles sudo automatically:

```bash
./import_backup_fixed.sh backup.sql
```

(You'll need to enter your sudo password)

## Quick Manual Import

If you prefer to do it step by step:

```bash
# 1. Start containers (with sudo if needed)
sudo docker-compose up -d db redis minio

# 2. Wait for PostgreSQL (about 10 seconds)
sleep 10

# 3. Create database (if needed)
export PGPASSWORD=docpass
psql -h localhost -p 55432 -U docuser -d postgres -c "CREATE DATABASE docdb;"

# 4. Import backup
psql -h localhost -p 55432 -U docuser -d docdb -f backup.sql

# 5. Verify
psql -h localhost -p 55432 -U docuser -d docdb -c "\dt"
unset PGPASSWORD
```

## After Import

Test the connection:
```bash
python3 test_db_connection.py
```

Start all services:
```bash
docker-compose up -d
```

