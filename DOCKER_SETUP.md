# Docker-Based Database Setup Guide

This project uses **Docker-based PostgreSQL and Redis** (not local installations).

## Quick Start

### Step 1: Install Docker (if not already installed)

```bash
# Install Docker
sudo apt install docker.io docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker
```

### Step 2: Start Docker Containers

```bash
cd /home/vncuser/apps/docparser

# Start PostgreSQL, Redis, and MinIO
docker-compose up -d db redis minio

# Or start all services
docker-compose up -d
```

### Step 3: Verify Containers are Running

```bash
docker-compose ps
# or
docker ps
```

You should see:
- `docparser-db-1` (PostgreSQL on port 55432)
- `docparser-redis-1` (Redis on port 6379)
- `docparser-minio-1` (MinIO on ports 9000, 9001)

### Step 4: Setup Database Connection

Create `api/.env` file:

```bash
cd /home/vncuser/apps/docparser/api
cat > .env <<'EOF'
# Docker PostgreSQL (port 55432)
DB_URL=postgresql://docuser:docpass@localhost:55432/docdb

# Docker Redis
REDIS_URL=redis://localhost:6379

# Docker MinIO
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

### Step 5: Test Database Connection

```bash
cd /home/vncuser/apps/docparser
python3 test_db_connection.py
```

### Step 6: Import Your Database

```bash
# Using the import script
./import_docker_db.sh your_database_dump.sql

# Or manually
export PGPASSWORD=docpass
psql -h localhost -p 55432 -U docuser -d docdb < your_database_dump.sql
unset PGPASSWORD
```

## Docker Configuration

**PostgreSQL Container:**
- Image: `postgres:15-alpine`
- Port: `55432` (host) → `5432` (container)
- Database: `docdb`
- User: `docuser`
- Password: `docpass`
- Volume: `pgdata` (persistent storage)

**Redis Container:**
- Image: `redis:7-alpine`
- Port: `6379`
- No password required

**MinIO Container:**
- Image: `minio/minio:latest`
- Ports: `9000` (API), `9001` (Console)
- User: `minio`
- Password: `minio123`
- Volume: `minio` (persistent storage)

## Useful Docker Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs db
docker-compose logs redis
docker-compose logs api

# Restart a service
docker-compose restart db

# Access PostgreSQL container
docker-compose exec db psql -U docuser -d docdb

# Backup database (from inside container)
docker-compose exec db pg_dump -U docuser docdb > backup.sql

# Restore database (from inside container)
docker-compose exec -T db psql -U docuser docdb < backup.sql
```

## Database Connection Details

**From Host Machine:**
- Host: `localhost`
- Port: `55432`
- Database: `docdb`
- User: `docuser`
- Password: `docpass`
- Connection String: `postgresql://docuser:docpass@localhost:55432/docdb`

**From Docker Container:**
- Host: `db` (service name)
- Port: `5432`
- Database: `docdb`
- User: `docuser`
- Password: `docpass`
- Connection String: `postgresql://docuser:docpass@db:5432/docdb`

## Troubleshooting

### Docker not installed
```bash
sudo apt install docker.io docker-compose
sudo systemctl start docker
```

### Permission denied
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Container won't start
```bash
# Check logs
docker-compose logs db

# Remove and recreate
docker-compose down -v
docker-compose up -d db
```

### Port already in use
If port 55432 is already in use, you can change it in `docker-compose.yml`:
```yaml
ports:
  - "55433:5432"  # Change 55432 to another port
```

### Database connection fails
1. Check container is running: `docker-compose ps`
2. Check port is correct: `netstat -tlnp | grep 55432`
3. Test connection: `psql -h localhost -p 55432 -U docuser -d docdb`

## Next Steps

1. ✅ Docker installed and running
2. ✅ Containers started
3. ✅ `.env` file created
4. ✅ Database imported
5. ✅ Start application: `docker-compose up -d`

