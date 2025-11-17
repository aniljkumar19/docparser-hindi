# How to Export Your Database

You need to export your database from wherever it currently exists. Here are the options:

## Option 1: Export from Local PostgreSQL (if you have one running)

If you have PostgreSQL running locally with your data:

```bash
# Export the database
pg_dump -h localhost -U docuser -d docdb > my_database_dump.sql

# Or if you used different credentials
pg_dump -h localhost -U your_username -d your_database > my_database_dump.sql
```

## Option 2: Export from Docker Container (if your DB was in Docker before)

If your database was running in Docker containers:

```bash
# First, find your container
docker ps -a | grep postgres

# Export from the container
docker exec <container_name> pg_dump -U docuser docdb > my_database_dump.sql

# Or if containers are stopped, start them first
docker-compose up -d db
docker exec docparser-db-1 pg_dump -U docuser docdb > my_database_dump.sql
```

## Option 3: Convert SQLite to PostgreSQL (if you have SQLite database)

I noticed you have `api/data.db` - if that's a SQLite database, you can convert it:

```bash
# Install sqlite3 if needed
sudo apt install sqlite3

# Export SQLite to SQL format
sqlite3 api/data.db .dump > sqlite_dump.sql

# Then you'll need to convert it for PostgreSQL (manual editing may be needed)
# Or use a conversion tool
```

## Option 4: Export from Cloud Database

If your database is on a cloud service (AWS RDS, DigitalOcean, etc.):

```bash
# Use pg_dump with connection string
pg_dump "postgresql://user:password@host:port/database" > my_database_dump.sql
```

## Option 5: Check for Existing Backups

You might already have a backup somewhere:

```bash
# Search for backup files
find ~ -name "*.sql" -o -name "*backup*" -o -name "*dump*" 2>/dev/null

# Check common backup locations
ls -lh ~/backups/ 2>/dev/null
ls -lh ~/Documents/ 2>/dev/null
```

## Quick Export Script

I can create a script to help you export. What database are you currently using?

1. **Local PostgreSQL** (running on your machine)
2. **Docker PostgreSQL** (in containers)
3. **SQLite** (the data.db file)
4. **Cloud database** (AWS, DigitalOcean, etc.)
5. **Don't have the database** (need to start fresh)

Let me know which one, and I'll create the appropriate export script!

## After Export

Once you have the SQL dump file:

```bash
# Import into Docker PostgreSQL
./import_docker_db.sh my_database_dump.sql
```

