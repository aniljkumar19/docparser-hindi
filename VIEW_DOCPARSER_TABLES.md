# How to View Tables in the docparser Schema

This guide shows you how to see and access tables in the `docparser` schema in PostgreSQL.

## Understanding PostgreSQL Schemas

In PostgreSQL, schemas are like "folders" or "namespaces" within a database:

```
Database: railway
├── Schema: public (default schema)
│   └── Competetracker tables here
└── Schema: docparser (our schema)
    └── DocParser tables here
```

## Method 1: Using psql Command Line

### List all tables in docparser schema:

```bash
# Set your DATABASE_URL first
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@shuttle.proxy.rlwy.net:20893/railway"

# List tables in docparser schema
psql $DATABASE_URL -c "\dt docparser.*"
```

Output will show:
```
            List of relations
 Schema   |  Name   | Type  |  Owner   
----------+---------+-------+----------
 docparser| batches | table | postgres
 docparser| clients | table | postgres
 docparser| jobs    | table | postgres
```

### List all schemas:

```bash
psql $DATABASE_URL -c "\dn"
```

### List tables in public schema (Competetracker):

```bash
psql $DATABASE_URL -c "\dt public.*"
```

### Interactive psql session:

```bash
psql $DATABASE_URL

# Inside psql:
\dn                    # List all schemas
\dt docparser.*        # List tables in docparser schema
\dt public.*           # List tables in public schema
\d docparser.jobs      # Describe jobs table structure
SELECT * FROM docparser.jobs LIMIT 5;  # Query data

\q                     # Exit
```

## Method 2: Using SQL Queries

### List tables in docparser schema:

```bash
psql $DATABASE_URL -c "
SELECT table_schema, table_name 
FROM information_schema.tables 
WHERE table_schema = 'docparser'
ORDER BY table_name;
"
```

### Count rows in each table:

```bash
psql $DATABASE_URL -c "
SELECT 
    'jobs' as table_name, 
    COUNT(*) as row_count 
FROM docparser.jobs
UNION ALL
SELECT 
    'batches', 
    COUNT(*) 
FROM docparser.batches
UNION ALL
SELECT 
    'clients', 
    COUNT(*) 
FROM docparser.clients;
"
```

### Show table structures:

```bash
# Show jobs table structure
psql $DATABASE_URL -c "\d docparser.jobs"

# Show batches table structure
psql $DATABASE_URL -c "\d docparser.batches"

# Show clients table structure
psql $DATABASE_URL -c "\d docparser.clients"
```

## Method 3: Using Python Script

Create a simple script to list tables:

```bash
cd /home/vncuser/apps/docparser
python3 << 'EOF'
import os
from sqlalchemy import create_engine, inspect, text

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("❌ DATABASE_URL not set")
    exit(1)

engine = create_engine(db_url)
inspector = inspect(engine)

# List all schemas
print("📦 Schemas in database:")
schemas = inspector.get_schema_names()
for schema in schemas:
    print(f"   - {schema}")

# List tables in docparser schema
print("\n📊 Tables in 'docparser' schema:")
tables = inspector.get_table_names(schema="docparser")
for table in sorted(tables):
    print(f"   ✅ {table}")

# List tables in public schema
print("\n📊 Tables in 'public' schema:")
public_tables = inspector.get_table_names(schema="public")
print(f"   Found {len(public_tables)} tables (Competetracker)")
if public_tables:
    for table in sorted(public_tables)[:10]:  # Show first 10
        print(f"   - {table}")
    if len(public_tables) > 10:
        print(f"   ... and {len(public_tables) - 10} more")
EOF
```

## Method 4: Using Railway Dashboard

1. Go to Railway Dashboard
2. Select your PostgreSQL service
3. Click "Query" tab (if available)
4. Run SQL:

```sql
-- List all schemas
SELECT schema_name 
FROM information_schema.schemata 
ORDER BY schema_name;

-- List tables in docparser schema
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'docparser'
ORDER BY table_name;

-- Show table details
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'docparser'
ORDER BY table_name, ordinal_position;
```

## Querying Data from docparser Schema

### Important: Always specify the schema name!

```sql
-- ✅ CORRECT - Specify schema
SELECT * FROM docparser.jobs;

-- ❌ WRONG - Will look in public schema (won't find DocParser tables)
SELECT * FROM jobs;
```

### Examples:

```bash
# Query jobs table
psql $DATABASE_URL -c "SELECT id, status, filename FROM docparser.jobs LIMIT 5;"

# Query batches table
psql $DATABASE_URL -c "SELECT * FROM docparser.batches;"

# Query clients table
psql $DATABASE_URL -c "SELECT * FROM docparser.clients;"
```

## Setting Default Schema (Optional)

If you want to avoid typing `docparser.` every time, you can set the search path:

```bash
psql $DATABASE_URL

-- Set search path to include docparser schema first
SET search_path TO docparser, public;

-- Now you can query without schema prefix
SELECT * FROM jobs;

-- Reset to default
SET search_path TO public, docparser;
```

## Verify Tables Exist

Quick verification script:

```bash
cd /home/vncuser/apps/docparser
python3 scripts/apply_schema_to_railway.py --dry-run
```

This will show:
```
📦 Using schema: docparser
   ✅ Schema 'docparser' exists
📋 Checking tables in schema 'docparser'...
   ✅ jobs - already exists
   ✅ batches - already exists
   ✅ clients - already exists
```

## Summary

**Tables are located at:**
- Full name: `docparser.jobs`, `docparser.batches`, `docparser.clients`
- Database: `railway` (your Railway database)
- Schema: `docparser` (isolated from `public` schema)

**To see them:**
```bash
psql $DATABASE_URL -c "\dt docparser.*"
```

**To query them:**
```sql
SELECT * FROM docparser.jobs;
```

**Your app automatically uses them** - SQLAlchemy knows to look in the `docparser` schema because of the `__table_args__ = {'schema': 'docparser'}` in the model definitions.

