#!/usr/bin/env python3
"""
Apply DocParser schema to Railway PostgreSQL database.
This script safely creates tables if they don't exist.

Usage:
    cd /home/vncuser/apps/docparser
    export DATABASE_URL="postgresql://..."
    python3 scripts/apply_schema_to_railway.py
"""
import os
import sys
from pathlib import Path

# Add api directory to path
project_root = Path(__file__).parent.parent
api_dir = project_root / "api"
sys.path.insert(0, str(api_dir))
sys.path.insert(0, str(project_root))

# Change to api directory
os.chdir(str(api_dir))

from sqlalchemy import create_engine, inspect, text
from app.db import Base, Job, Batch, Client, DOCPARSER_SCHEMA

def table_exists(engine, table_name):
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def apply_schema(database_url=None, dry_run=False):
    """
    Apply schema to database.
    
    Args:
        database_url: PostgreSQL connection string (or use DATABASE_URL env var)
        dry_run: If True, only print what would be done without executing
    """
    # Get database URL
    db_url = database_url or os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL or DB_URL environment variable not set")
        print("   Set it to your Railway PostgreSQL connection string")
        print("   Example: postgresql://user:pass@host:port/dbname")
        sys.exit(1)
    
    print(f"🔗 Connecting to database...")
    if dry_run:
        print("   [DRY RUN] Would connect to:", db_url.split("@")[1] if "@" in db_url else db_url)
    else:
        engine = create_engine(db_url)
    
    # Check if schema exists
    schema_name = DOCPARSER_SCHEMA
    print(f"\n📦 Using schema: {schema_name}")
    
    if not dry_run:
        with engine.connect() as conn:
            # Check if schema exists
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = :schema
            """), {"schema": schema_name})
            schema_exists = result.fetchone() is not None
            
            if not schema_exists:
                print(f"   ⚠️  Schema '{schema_name}' does not exist")
                if not dry_run:
                    print(f"   Creating schema '{schema_name}'...")
                    conn.execute(text(f"CREATE SCHEMA {schema_name}"))
                    conn.commit()
                    print(f"   ✅ Schema '{schema_name}' created")
            else:
                print(f"   ✅ Schema '{schema_name}' exists")
    
    tables_to_create = {
        "jobs": Job,
        "batches": Batch,
        "clients": Client,
    }
    
    print(f"\n📋 Checking tables in schema '{schema_name}'...")
    existing_tables = []
    missing_tables = []
    
    if not dry_run:
        inspector = inspect(engine)
        # Get tables in the specific schema
        existing = inspector.get_table_names(schema=schema_name)
    else:
        existing = []
    
    for table_name, table_class in tables_to_create.items():
        if table_name in existing:
            existing_tables.append(table_name)
            print(f"   ✅ {table_name} - already exists")
        else:
            missing_tables.append((table_name, table_class))
            print(f"   ⚠️  {table_name} - missing")
    
    if not missing_tables:
        print("\n✅ All tables already exist. Schema is up to date!")
        return
    
    print(f"\n🔨 Creating {len(missing_tables)} missing table(s)...")
    
    if dry_run:
        print("\n[DRY RUN] Would create:")
        for table_name, _ in missing_tables:
            print(f"   - {table_name}")
        print("\nRun without --dry-run to actually create tables.")
        return
    
    # Create missing tables
    for table_name, table_class in missing_tables:
        try:
            print(f"   Creating {table_name}...")
            table_class.__table__.create(engine, checkfirst=True)
            print(f"   ✅ {table_name} created successfully")
        except Exception as e:
            print(f"   ❌ Error creating {table_name}: {e}")
            sys.exit(1)
    
    print("\n✅ Schema applied successfully!")
    print(f"\n📊 Current tables in schema '{schema_name}':")
    inspector = inspect(engine)
    for table_name in sorted(inspector.get_table_names(schema=schema_name)):
        if table_name in tables_to_create:
            print(f"   ✅ {table_name}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Apply DocParser schema to Railway database")
    parser.add_argument("--database-url", help="Database connection string (or use DATABASE_URL env var)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")
    args = parser.parse_args()
    
    apply_schema(database_url=args.database_url, dry_run=args.dry_run)

