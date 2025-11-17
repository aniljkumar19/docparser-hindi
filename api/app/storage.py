import os, uuid, boto3, re
from pathlib import Path

# Storage type: "local" or "s3" (defaults to "local" if S3 not configured)
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "").lower()
USE_S3 = STORAGE_TYPE == "s3" or (os.getenv("S3_ENDPOINT") and os.getenv("S3_ENDPOINT") != "http://localhost:9000")

# Local storage directory
LOCAL_STORAGE_DIR = Path(os.getenv("LOCAL_STORAGE_DIR", "/app/uploads"))
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# S3 configuration (only used if USE_S3 is True)
S3_ENDPOINT = os.getenv("S3_ENDPOINT","http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY","minio")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY","minio123")
S3_REGION = os.getenv("S3_REGION","us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET","docparser")
S3_SECURE = os.getenv("S3_SECURE","false").lower() == "true"

# Initialize S3 client only if using S3
s3 = None
if USE_S3:
    try:
        session = boto3.session.Session()
        s3 = session.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION,
            use_ssl=S3_SECURE,
        )
    except Exception as e:
        import logging
        logging.warning(f"Failed to initialize S3 client: {e}, falling back to local storage")
        USE_S3 = False

def get_object_key(filename: str) -> str:
    """Generate a unique object key for a file."""
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', os.path.basename(filename))[:80]
    return f"uploads/{uuid.uuid4().hex}/{safe}"

def save_file_to_s3(key: str, data: bytes):
    """Save file to storage (S3 or local filesystem)."""
    if USE_S3 and s3:
        try:
            s3.put_object(Bucket=S3_BUCKET, Key=key, Body=data)
            return
        except Exception as e:
            import logging
            logging.error(f"S3 upload failed: {e}, falling back to local storage")
    
    # Fallback to local storage
    file_path = LOCAL_STORAGE_DIR / key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(data)

def get_file_from_s3(key: str) -> bytes:
    """Get file from storage (S3 or local filesystem)."""
    if USE_S3 and s3:
        try:
            obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
            return obj["Body"].read()
        except Exception as e:
            import logging
            logging.warning(f"S3 download failed: {e}, trying local storage")
    
    # Fallback to local storage
    file_path = LOCAL_STORAGE_DIR / key
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {key}")
    with open(file_path, 'rb') as f:
        return f.read()
    
# add near the bottom of storage.py
def ensure_bucket():
    """Ensure storage is ready (S3 bucket or local directory). Returns True if successful."""
    if USE_S3 and s3:
        # Ensure S3 bucket exists
        try:
            s3.head_bucket(Bucket=S3_BUCKET)
            return True
        except Exception as e:
            import logging
            logging.debug(f"Bucket check failed: {e}")
        
        # Create if missing (AWS needs region config unless us-east-1)
        try:
            from urllib.parse import urlparse
            host = (urlparse(S3_ENDPOINT).hostname or "").lower()
            if "amazonaws.com" in host and S3_REGION and S3_REGION != "us-east-1":
                s3.create_bucket(
                    Bucket=S3_BUCKET,
                    CreateBucketConfiguration={"LocationConstraint": S3_REGION}
                )
            else:
                s3.create_bucket(Bucket=S3_BUCKET)
            return True
        except Exception as e:
            import logging
            logging.warning(f"Could not create S3 bucket '{S3_BUCKET}': {e}")
            logging.warning(f"S3_ENDPOINT: {S3_ENDPOINT}")
            return False
    else:
        # Ensure local storage directory exists
        try:
            LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            import logging
            logging.info(f"Using local file storage at: {LOCAL_STORAGE_DIR}")
            return True
        except Exception as e:
            import logging
            logging.error(f"Could not create local storage directory: {e}")
            return False

