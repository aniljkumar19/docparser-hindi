# How to Get Your Database Dump

Based on what I found, here are your options:

## Option 1: Export from SQLite Database (Most Likely)

You have a SQLite database at `api/data.db` (40KB, last modified Sep 29).

**Export it:**
```bash
cd /home/vncuser/apps/docparser

# Install sqlite3 if needed
sudo apt install sqlite3

# Export the database
./export_from_sqlite.sh
```

This will create a PostgreSQL-compatible SQL file that you can import.

## Option 2: Export from Local PostgreSQL

You have PostgreSQL running locally. Check what databases exist:

```bash
# List databases (you'll need the postgres password)
psql -h localhost -U postgres -d postgres -c "\l"

# Or try with your user
psql -h localhost -U docuser -d postgres -c "\l"
```

**If you find your database, export it:**
```bash
./export_from_local_postgres.sh docdb docuser localhost 5432 docpass
```

## Option 3: Check Docker Containers

If you had Docker running before, your data might be in a Docker volume:

```bash
# Check if Docker is installed and containers exist
docker ps -a | grep postgres

# If containers exist, export from them
docker exec <container_name> pg_dump -U docuser docdb > dump.sql
```

## Quick Check Script

Run this to see all your options:

```bash
./find_and_export_db.sh
```

## Most Likely Scenario

Since you have `api/data.db` (SQLite), you probably used SQLite before. Export it:

```bash
# Install sqlite3
sudo apt install sqlite3

# Export
./export_from_sqlite.sh my_database.sql
```

## After Export

Once you have the SQL dump file:

```bash
# Start Docker containers (if not already running)
docker-compose up -d db redis minio

# Import the dump
./import_docker_db.sh my_database.sql
```

## Need Help?

Tell me which database you were using:
1. **SQLite** (the data.db file) ← Most likely
2. **Local PostgreSQL** (running on your machine)
3. **Docker PostgreSQL** (in containers)
4. **Don't remember** (we can check together)

