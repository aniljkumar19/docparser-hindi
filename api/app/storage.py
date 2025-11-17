import os, uuid, boto3, re

S3_ENDPOINT = os.getenv("S3_ENDPOINT","http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY","minio")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY","minio123")
S3_REGION = os.getenv("S3_REGION","us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET","docparser")
S3_SECURE = os.getenv("S3_SECURE","false").lower() == "true"

session = boto3.session.Session()
s3 = session.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name=S3_REGION,
    use_ssl=S3_SECURE,
)

def get_object_key(filename: str) -> str:
    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', os.path.basename(filename))[:80]
    return f"uploads/{uuid.uuid4().hex}/{safe}"

def save_file_to_s3(key: str, data: bytes):
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=data)

def get_file_from_s3(key: str) -> bytes:
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return obj["Body"].read()
    
# add near the bottom of storage.py
def ensure_bucket():
    """Ensure S3 bucket exists. Returns True if successful, False otherwise."""
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

