# Docker Setup Summary

## ✅ What's Updated

Since you're using **Docker-based PostgreSQL and Redis**, I've updated everything accordingly:

1. **Created Docker-specific scripts:**
   - `setup_docker_db.sh` - Setup Docker PostgreSQL
   - `import_docker_db.sh` - Import database into Docker PostgreSQL
   - `export_docker_db.sh` - Export database from Docker PostgreSQL

2. **Updated test script:**
   - `test_db_connection.py` - Now defaults to Docker port 55432

3. **Created Docker documentation:**
   - `DOCKER_SETUP.md` - Complete Docker setup guide

## 🚀 Quick Start

### 1. Install Docker (if needed)

```bash
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker  # or log out/in
```

### 2. Start Docker Containers

```bash
cd /home/vncuser/apps/docparser
docker-compose up -d db redis minio
```

### 3. Create Environment File

Create `api/.env`:

```bash
DB_URL=postgresql://docuser:docpass@localhost:55432/docdb
REDIS_URL=redis://localhost:6379
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_REGION=us-east-1
S3_BUCKET=docparser
S3_SECURE=false
API_KEYS=dev_123:tenant_demo
MAX_FILE_MB=15
```

### 4. Test Connection

```bash
python3 test_db_connection.py
```

### 5. Import Your Database

```bash
./import_docker_db.sh your_database_dump.sql
```

## 📝 Important Notes

- **PostgreSQL Port:** `55432` (not 5432) - this is the Docker mapped port
- **Redis Port:** `6379` (standard)
- **MinIO Ports:** `9000` (API), `9001` (Console)
- Database credentials are already configured in `docker-compose.yml`

## 🔍 Verify Everything

```bash
# Check containers
docker-compose ps

# Test database
export PGPASSWORD=docpass
psql -h localhost -p 55432 -U docuser -d docdb -c "SELECT version();"
unset PGPASSWORD
```

## 📚 More Information

See `DOCKER_SETUP.md` for detailed instructions and troubleshooting.

