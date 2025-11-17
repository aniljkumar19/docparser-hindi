#!/usr/bin/env python3
"""
Generate SQL DDL from SQLAlchemy models.
This script generates CREATE TABLE statements for all DocParser tables.

Usage:
    cd /home/vncuser/apps/docparser
    python3 scripts/generate_schema.py [output_file]
"""
import os
import sys
from pathlib import Path

# Add api directory to path to import app modules and dependencies
project_root = Path(__file__).parent.parent
api_dir = project_root / "api"
sys.path.insert(0, str(api_dir))
sys.path.insert(0, str(project_root))

# Change to api directory to ensure imports work
os.chdir(str(api_dir))

from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable
from app.db import Base, Job, Batch, Client

def generate_schema(output_file=None):
    """Generate SQL DDL for all tables."""
    # Use a dummy database URL (we only need the schema, not a real connection)
    engine = create_engine("postgresql://dummy:dummy@localhost/dummy")
    
    tables = [Job, Batch, Client]
    ddl_statements = []
    
    for table_class in tables:
        table = table_class.__table__
        create_stmt = CreateTable(table).compile(engine)
        ddl_statements.append(str(create_stmt))
    
    sql = "\n\n".join(ddl_statements)
    
    # Add header comment
    header = """-- DocParser Database Schema
-- Generated from SQLAlchemy models
-- Tables: jobs, batches, clients
-- 
-- To apply this schema to Railway:
--   1. Set DATABASE_URL environment variable to your Railway DB
--   2. Run: python scripts/apply_schema_to_railway.py
--
-- Or manually:
--   psql $DATABASE_URL < schema.sql
"""
    
    full_sql = header + "\n" + sql
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(full_sql)
        print(f"✅ Schema written to {output_file}")
    else:
        print(full_sql)
    
    return full_sql

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "schema.sql"
    generate_schema(output)

