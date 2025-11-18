#!/usr/bin/env python3
"""
Test database connection and schema initialization
"""
import os
import sys

# Add api directory to path (tests/ is one level up from api/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from app.db import engine, init_db, Base
from sqlalchemy import inspect

def test_connection():
    """Test database connection"""
    # Default to Docker PostgreSQL port (55432)
    db_url = os.getenv("DB_URL", "postgresql://docuser:docpass@localhost:55432/docdb")
    print(f"Testing connection to: {db_url.split('@')[1] if '@' in db_url else db_url}")
    
    try:
        # Test connection
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"   PostgreSQL version: {version.split(',')[0]}")
        
        # Check existing tables
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print(f"\n📊 Existing tables: {len(existing_tables)}")
        for table in existing_tables:
            print(f"   - {table}")
        
        # Initialize schema if needed
        expected_tables = ['jobs', 'batches', 'clients']
        missing_tables = [t for t in expected_tables if t not in existing_tables]
        
        if missing_tables:
            print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
            print("   Initializing database schema...")
            init_db()
            print("   ✅ Schema initialized!")
            
            # Verify tables created
            inspector = inspect(engine)
            new_tables = inspector.get_table_names()
            print(f"\n📊 Tables after initialization: {len(new_tables)}")
            for table in new_tables:
                print(f"   - {table}")
        else:
            print("\n✅ All required tables exist!")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check PostgreSQL is running: sudo systemctl status postgresql")
        print("2. Verify database exists: psql -U docuser -d docdb -c 'SELECT 1;'")
        print("3. Check DB_URL environment variable")
        return False

if __name__ == "__main__":
    print("=== Database Connection Test ===\n")
    success = test_connection()
    sys.exit(0 if success else 1)

