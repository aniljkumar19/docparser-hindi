#!/usr/bin/env python3
"""
Compare and sync schema between development and production.
This script compares table structures and generates migration SQL.

Usage:
    cd /home/vncuser/apps/docparser
    export DB_URL="postgresql://..."  # Dev
    export DATABASE_URL="postgresql://..."  # Prod
    python3 scripts/sync_schema.py
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

from sqlalchemy import create_engine, inspect, text, MetaData
from sqlalchemy.schema import CreateTable
from app.db import Base, Job, Batch, Client, DOCPARSER_SCHEMA

def get_table_schema(engine, table_name, schema_name):
    """Get the schema of a table as a dictionary."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names(schema=schema_name):
        return None
    
    columns = {}
    for col in inspector.get_columns(table_name, schema=schema_name):
        columns[col['name']] = {
            'type': str(col['type']),
            'nullable': col['nullable'],
            'default': col.get('default'),
        }
    
    return columns

def compare_schemas(dev_url, prod_url):
    """Compare schemas between dev and prod databases."""
    print("🔍 Comparing schemas...")
    
    dev_engine = create_engine(dev_url)
    prod_engine = create_engine(prod_url)
    
    schema_name = DOCPARSER_SCHEMA
    print(f"📦 Comparing schema: {schema_name}\n")
    
    dev_inspector = inspect(dev_engine)
    prod_inspector = inspect(prod_engine)
    
    # Get tables in the docparser schema
    dev_tables = set(dev_inspector.get_table_names(schema=schema_name))
    prod_tables = set(prod_inspector.get_table_names(schema=schema_name))
    
    docparser_tables = {"jobs", "batches", "clients"}
    
    # Filter to only DocParser tables
    dev_tables = dev_tables & docparser_tables
    prod_tables = prod_tables & docparser_tables
    
    print(f"\n📊 DocParser tables:")
    print(f"   Development: {sorted(dev_tables)}")
    print(f"   Production:  {sorted(prod_tables)}")
    
    # Check for missing tables
    missing_in_prod = dev_tables - prod_tables
    if missing_in_prod:
        print(f"\n⚠️  Tables missing in production: {sorted(missing_in_prod)}")
        print("   Run: python scripts/apply_schema_to_railway.py")
    
    # Check for extra tables in prod
    extra_in_prod = prod_tables - dev_tables
    if extra_in_prod:
        print(f"\n⚠️  Extra tables in production: {sorted(extra_in_prod)}")
    
    # Compare column structures
    common_tables = dev_tables & prod_tables
    if common_tables:
        print(f"\n🔍 Comparing columns in common tables...")
        differences = []
        
        for table_name in sorted(common_tables):
            dev_schema = get_table_schema(dev_engine, table_name, schema_name)
            prod_schema = get_table_schema(prod_engine, table_name, schema_name)
            
            if dev_schema != prod_schema:
                print(f"\n   ⚠️  {table_name} - schema differs")
                differences.append((table_name, dev_schema, prod_schema))
                
                # Show differences
                dev_cols = set(dev_schema.keys())
                prod_cols = set(prod_schema.keys())
                
                missing_cols = dev_cols - prod_cols
                extra_cols = prod_cols - dev_cols
                
                if missing_cols:
                    print(f"      Missing columns in prod: {sorted(missing_cols)}")
                if extra_cols:
                    print(f"      Extra columns in prod: {sorted(extra_cols)}")
            else:
                print(f"   ✅ {table_name} - schemas match")
        
        if differences:
            print(f"\n⚠️  Schema differences detected!")
            print("   Manual migration may be required for column changes.")
        else:
            print(f"\n✅ All common tables have matching schemas!")
    
    return {
        'missing_tables': missing_in_prod,
        'extra_tables': extra_in_prod,
        'differences': differences if 'differences' in locals() else []
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compare and sync schema between dev and prod")
    parser.add_argument("--dev-url", help="Development database URL (or use DB_URL env var)", 
                       default=os.getenv("DB_URL"))
    parser.add_argument("--prod-url", help="Production database URL (or use DATABASE_URL env var)",
                       default=os.getenv("DATABASE_URL"))
    
    args = parser.parse_args()
    
    if not args.dev_url:
        print("❌ Error: --dev-url or DB_URL environment variable required")
        sys.exit(1)
    
    if not args.prod_url:
        print("❌ Error: --prod-url or DATABASE_URL environment variable required")
        sys.exit(1)
    
    compare_schemas(args.dev_url, args.prod_url)

