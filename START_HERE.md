# 🚀 Start Here - Quick Setup Guide

## ✅ What You Already Have

Your `docker-compose.yml` is already configured with:
- ✅ **PostgreSQL** (`postgres:15-alpine`) - Port 55432
- ✅ **Redis** (`redis:7-alpine`) - Port 6379  
- ✅ **MinIO** (`minio/minio:latest`) - Ports 9000, 9001
- ✅ **Environment file** (`api/.env`) - Already created

## 📋 Simple 3-Step Setup

### Step 1: Install Docker (one-time setup)

```bash
cd /home/vncuser/apps/docparser
./install_docker.sh
```

**Then log out and log back in** (or run `newgrp docker`)

### Step 2: Start Your Docker Containers

```bash
docker-compose up -d db redis minio
```

This will automatically:
- Download the Docker images (if not already downloaded)
- Create and start the containers
- Set up PostgreSQL with database `docdb`, user `docuser`, password `docpass`

### Step 3: Import Your Database

```bash
./import_docker_db.sh your_database_dump.sql
```

## ✅ Verify Everything Works

```bash
# Check containers are running
docker-compose ps

# Test database connection
python3 test_db_connection.py

# View logs if needed
docker-compose logs db
```

## 🎯 That's It!

Once Docker is installed, you're ready to go. The `docker-compose.yml` handles everything else automatically.

## 📝 Useful Commands

```bash
# Start all services
docker-compose up -d

# Stop all services  
docker-compose down

# View logs
docker-compose logs -f

# Restart database
docker-compose restart db
```

## 🆘 Troubleshooting

**Docker not installed?**
```bash
./install_docker.sh
```

**Permission denied?**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Containers won't start?**
```bash
docker-compose logs db
docker-compose down
docker-compose up -d db redis minio
```

