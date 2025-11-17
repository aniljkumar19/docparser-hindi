import os
import boto3
from botocore.client import Config

STORAGE_KIND = os.getenv("STORAGE_KIND","local")
LOCAL_STORAGE_PATH = os.getenv("LOCAL_STORAGE_PATH","/data")

AWS_REGION = os.getenv("AWS_REGION","ap-south-1")
S3_BUCKET = os.getenv("S3_BUCKET","")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID","")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY","")

_s3 = None
if STORAGE_KIND == "s3":
    _s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
        config=Config(s3={"addressing_style": "virtual"}),
    )

def put_bytes(key: str, data: bytes) -> str:
    """Store data and return storage key (path or s3 key)."""
    if STORAGE_KIND == "s3":
        _s3.put_object(Bucket=S3_BUCKET, Key=key, Body=data)
        return key
    os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)
    path = os.path.join(LOCAL_STORAGE_PATH, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path

def get_bytes(storage_key: str) -> bytes:
    if STORAGE_KIND == "s3":
        resp = _s3.get_object(Bucket=S3_BUCKET, Key=storage_key)
        return resp["Body"].read()
    with open(storage_key, "rb") as f:
        return f.read()
