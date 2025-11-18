"""Migration script to convert environment variable API keys to database"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal, ApiKey, init_db
from app.security import hash_api_key, _load_key_map

def migrate_env_keys_to_db():
    """Migrate API keys from environment variables to database"""
    print("Starting API key migration...")
    
    # Initialize database (creates tables if needed)
    init_db()
    
    # Load keys from environment
    key_map = _load_key_map()
    
    if not key_map:
        print("No API keys found in environment variables.")
        return
    
    print(f"Found {len(key_map)} API keys in environment variables.")
    
    with SessionLocal() as db:
        migrated = 0
        skipped = 0
        
        for api_key, tenant_id in key_map.items():
            # Check if key already exists (by hash)
            key_hash = hash_api_key(api_key)
            existing = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
            
            if existing:
                print(f"  ✓ Key for tenant '{tenant_id}' already exists in database (skipping)")
                skipped += 1
                continue
            
            # Create new API key record
            # Note: We can't store the original key, so we'll create a placeholder
            # In production, users should create new keys via the API
            db_key = ApiKey(
                key_hash=key_hash,
                tenant_id=tenant_id,
                name=f"Migrated from env (tenant: {tenant_id})",
                is_active="active",
                rate_limit_per_minute=60,
                rate_limit_per_hour=1000,
                created_by="migration_script"
            )
            db.add(db_key)
            migrated += 1
            print(f"  ✓ Migrated key for tenant '{tenant_id}'")
        
        db.commit()
        print(f"\nMigration complete:")
        print(f"  - Migrated: {migrated}")
        print(f"  - Skipped (already exists): {skipped}")
        print(f"\n⚠️  IMPORTANT: Environment variable keys cannot be fully migrated")
        print(f"   because we don't store the original key. Users should:")
        print(f"   1. Create new keys via POST /v1/api-keys/")
        print(f"   2. Update their applications with the new keys")
        print(f"   3. Revoke old keys once migration is complete")

if __name__ == "__main__":
    migrate_env_keys_to_db()

