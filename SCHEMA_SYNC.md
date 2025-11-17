# Database Schema Sync Guide

This guide explains how to sync DocParser database schema from development to Railway production.

## Overview

DocParser uses these tables:
- `jobs` - Document parsing jobs
- `batches` - Batch uploads
- `clients` - CA's clients

## Prerequisites

Make sure you have the dependencies installed:

```bash
cd /home/vncuser/apps/docparser/api
pip install -r requirements.txt
```

Or if using a virtual environment:

```bash
cd /home/vncuser/apps/docparser/api
source venv/bin/activate  # if you have a venv
pip install -r requirements.txt
```

## Quick Start

### 1. Generate Schema SQL

Generate SQL DDL from your models:

```bash
cd /home/vncuser/apps/docparser
python3 scripts/generate_schema.py schema.sql
```

This creates `schema.sql` with CREATE TABLE statements.

**Note:** The script will automatically use the `api` directory for imports and dependencies.

### 2. Apply Schema to Railway

**Option A: Using the script (recommended)**

```bash
# Set your Railway database URL
export DATABASE_URL="postgresql://user:pass@host:port/dbname"

# Dry run first (see what would be created)
python scripts/apply_schema_to_railway.py --dry-run

# Actually apply
python scripts/apply_schema_to_railway.py
```

**Option B: Using psql directly**

```bash
# Get DATABASE_URL from Railway dashboard
export DATABASE_URL="postgresql://..."

# Apply schema
psql $DATABASE_URL < schema.sql
```

### 3. Verify Schema

Check that tables exist:

```bash
python scripts/apply_schema_to_railway.py --dry-run
```

## Syncing Schema Changes

When you modify table structures in development:

### Step 1: Update Models

Edit `api/app/db.py` to modify your SQLAlchemy models.

### Step 2: Test Locally

```bash
# Your local DB will auto-update via init_db()
# Or manually:
python -c "from api.app.db import init_db; init_db()"
```

### Step 3: Compare Schemas

```bash
# Set both database URLs
export DB_URL="postgresql://docuser:docpass@localhost:55432/docdb"  # Local
export DATABASE_URL="postgresql://..."  # Railway

# Compare
python scripts/sync_schema.py
```

### Step 4: Generate Migration SQL

For simple additions (new tables, new columns), the script will show what's missing.

For complex changes (column type changes, constraints), you may need to write manual migration SQL.

### Step 5: Apply to Railway

```bash
# Apply missing tables/columns
python scripts/apply_schema_to_railway.py
```

## Getting Railway Database URL

1. Go to Railway dashboard
2. Select your PostgreSQL service
3. Go to "Variables" tab
4. Copy the `DATABASE_URL` value

Or use Railway CLI:

```bash
railway variables
```

## Safety Features

- The `apply_schema_to_railway.py` script:
  - ✅ Only creates tables that don't exist (won't drop existing tables)
  - ✅ Uses `checkfirst=True` to avoid errors
  - ✅ Shows what will be created before doing it

- The `sync_schema.py` script:
  - ✅ Only compares, never modifies
  - ✅ Shows differences clearly

## Example Workflow

```bash
# 1. Make changes to api/app/db.py (e.g., add a new column)

# 2. Test locally
python -c "from api.app.db import init_db; init_db()"

# 3. Compare with production
export DATABASE_URL="postgresql://..."  # Railway DB
python scripts/sync_schema.py

# 4. If new tables/columns are needed, apply
python scripts/apply_schema_to_railway.py

# 5. Verify
python scripts/apply_schema_to_railway.py --dry-run
```

## Troubleshooting

### "Table already exists" errors

The script uses `checkfirst=True`, so this shouldn't happen. If it does, the table structure might differ. Use `sync_schema.py` to compare.

### Column type changes

SQLAlchemy's `create_all()` won't modify existing columns. You'll need to write manual ALTER TABLE statements:

```sql
ALTER TABLE jobs ADD COLUMN new_column VARCHAR;
-- or
ALTER TABLE jobs ALTER COLUMN existing_column TYPE new_type;
```

### Shared database concerns

Since you're sharing the Railway database with another app:
- ✅ DocParser tables use unique names (`jobs`, `batches`, `clients`)
- ✅ The scripts only create DocParser tables
- ✅ No risk of affecting other app's tables

## Files

- `scripts/generate_schema.py` - Generate SQL DDL
- `scripts/apply_schema_to_railway.py` - Apply schema to Railway
- `scripts/sync_schema.py` - Compare dev vs prod schemas
- `schema.sql` - Generated SQL file (gitignored)

