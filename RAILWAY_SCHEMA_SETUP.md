# How to Create Schema and Tables in Railway PostgreSQL

This guide shows you exactly how to create the `docparser` schema and tables in your Railway PostgreSQL database.

## Step 1: Get Your Railway Database URL

1. Go to [Railway Dashboard](https://railway.app)
2. Select your project
3. Click on your **PostgreSQL service** (the one you're sharing with Competetracker)
4. Go to the **"Variables"** tab
5. Find `DATABASE_URL` and copy its value

   It should look like:
   ```
   postgresql://postgres:qUtrIDbaOXGSRsOPhFLTRORMSOZkXXNk@shuttle.proxy.rlwy.net:20893/railway
   ```

## Step 2: Set Environment Variable

On your local machine, set the `DATABASE_URL`:

```bash
export DATABASE_URL="postgresql://postgres:qUtrIDbaOXGSRsOPhFLTRORMSOZkXXNk@shuttle.proxy.rlwy.net:20893/railway"
```

**⚠️ Security Note:** Don't commit this URL to git! It contains your password.

## Step 3: Install Dependencies (if needed)

Make sure you have the Python dependencies installed:

```bash
cd /home/vncuser/apps/docparser/api
pip install -r requirements.txt
```

Or if you're using a virtual environment:

```bash
cd /home/vncuser/apps/docparser/api
source venv/bin/activate  # if you have one
pip install -r requirements.txt
```

## Step 4: Test Connection (Optional)

Verify you can connect to Railway:

```bash
cd /home/vncuser/apps/docparser
python3 -c "
import os
from sqlalchemy import create_engine, text
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print('❌ DATABASE_URL not set')
    exit(1)
engine = create_engine(db_url)
with engine.connect() as conn:
    result = conn.execute(text('SELECT version();'))
    print('✅ Connected to Railway PostgreSQL')
    print('   Version:', result.fetchone()[0].split(',')[0])
"
```

## Step 5: Create Schema and Tables

### Option A: Using the Script (Recommended)

**Dry run first** (see what will be created without actually doing it):

```bash
cd /home/vncuser/apps/docparser
python3 scripts/apply_schema_to_railway.py --dry-run
```

You should see:
```
🔗 Connecting to database...
📦 Using schema: docparser
   ⚠️  Schema 'docparser' does not exist
📋 Checking tables in schema 'docparser'...
   ⚠️  jobs - missing
   ⚠️  batches - missing
   ⚠️  clients - missing
```

**Actually create the schema and tables:**

```bash
python3 scripts/apply_schema_to_railway.py
```

You should see:
```
🔗 Connecting to database...
📦 Using schema: docparser
   Creating schema 'docparser'...
   ✅ Schema 'docparser' created
📋 Checking tables in schema 'docparser'...
   Creating jobs...
   ✅ jobs created successfully
   Creating batches...
   ✅ batches created successfully
   Creating clients...
   ✅ clients created successfully

✅ Schema applied successfully!

📊 Current tables in schema 'docparser':
   ✅ batches
   ✅ clients
   ✅ jobs
```

### Option B: Using psql Directly

If you prefer using `psql` directly:

```bash
# Connect to Railway
psql $DATABASE_URL

# Then run these SQL commands:
CREATE SCHEMA IF NOT EXISTS docparser;

-- Exit psql
\q
```

Then generate and apply the schema:

```bash
# Generate SQL
python3 scripts/generate_schema.py schema.sql

# Apply it
psql $DATABASE_URL < schema.sql
```

## Step 6: Verify Tables Were Created

Check that everything is set up correctly:

```bash
python3 scripts/apply_schema_to_railway.py --dry-run
```

You should see all tables marked as ✅ existing.

Or use psql:

```bash
psql $DATABASE_URL -c "\dt docparser.*"
```

Should show:
```
            List of relations
 Schema   |  Name   | Type  |  Owner   
----------+---------+-------+----------
 docparser| batches | table | postgres
 docparser| clients | table | postgres
 docparser| jobs    | table | postgres
```

## Step 7: Verify Isolation

Verify that Competetracker tables are separate:

```bash
psql $DATABASE_URL -c "\dt public.*"
```

This will show Competetracker tables in the `public` schema (they won't conflict with DocParser).

## Troubleshooting

### "ModuleNotFoundError: No module named 'sqlalchemy'"

Install dependencies:
```bash
cd /home/vncuser/apps/docparser/api
pip install -r requirements.txt
```

### "Connection refused" or "Could not connect"

- Check that your Railway PostgreSQL service is running
- Verify the `DATABASE_URL` is correct
- Check if Railway has paused your database (free tier pauses after inactivity)

### "Schema already exists"

That's fine! The script will skip creating it and just create missing tables.

### "Permission denied"

Make sure your database user has permission to create schemas. Railway's default `postgres` user should have all permissions.

## What Gets Created

After running the script, you'll have:

**Schema:**
- `docparser` - Isolated schema for DocParser tables

**Tables in `docparser` schema:**
- `jobs` - Document parsing jobs
- `batches` - Batch uploads  
- `clients` - CA's clients

**Competetracker tables remain untouched** in the `public` schema.

## Next Steps

Once the schema and tables are created:

1. **Set DATABASE_URL in Railway** (for your app):
   - Go to Railway → Your DocParser service → Variables
   - Add `DATABASE_URL` with the same value
   - The app will automatically use the `docparser` schema

2. **Test the app** - It should now connect and use the tables in the `docparser` schema

3. **For future schema changes** - Use `scripts/sync_schema.py` to compare and `scripts/apply_schema_to_railway.py` to apply updates

