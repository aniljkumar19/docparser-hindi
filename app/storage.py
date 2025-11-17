import os, uuid, io, boto3
from botocore.exceptions import BotoCoreError, ClientError

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION") or "ap-south-1"
S3_BUCKET = os.getenv("S3_BUCKET")

LOCAL_DIR = os.path.abspath("./uploads")
os.makedirs(LOCAL_DIR, exist_ok=True)

def save_file(api_key: str, filename: str, data: bytes) -> str:
    # If S3 configured, upload there
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET:
        s3 = boto3.client("s3", region_name=AWS_REGION,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        key = f"uploads/{api_key}/{uuid.uuid4().hex}_{filename}"
        try:
            s3.put_object(Bucket=S3_BUCKET, Key=key, Body=data)
            return f"s3://{S3_BUCKET}/{key}"
        except (BotoCoreError, ClientError) as e:
            # Fallback to local if S3 fails
            pass
    # Local save
    outname = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(LOCAL_DIR, outname)
    with open(path, "wb") as f:
        f.write(data)
    return f"file://{path}"

def load_file(storage_uri: str) -> bytes:
    if storage_uri.startswith("file://"):
        path = storage_uri.replace("file://","",1)
        with open(path, "rb") as f:
            return f.read()
    if storage_uri.startswith("s3://"):
        import boto3
        _, rest = storage_uri.split("s3://",1)
        bucket, key = rest.split("/",1)
        s3 = boto3.client("s3", region_name=AWS_REGION,
                          aws_access_key_id=AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
    raise ValueError("Unsupported storage uri")
