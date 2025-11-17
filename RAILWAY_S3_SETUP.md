# Setting Up S3 Storage for Railway

Your app needs S3-compatible storage for file uploads. Currently it's trying to connect to `localhost:9000` (MinIO) which doesn't exist in Railway.

## Option 1: Use AWS S3 (Recommended for Production)

### Step 1: Create AWS S3 Bucket

1. Go to [AWS Console](https://console.aws.amazon.com/s3/)
2. Create a new bucket (e.g., `docparser-production`)
3. Note the region (e.g., `us-east-1`)

### Step 2: Create IAM User for S3 Access

1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. Create a new user (e.g., `docparser-s3-user`)
3. Attach policy: `AmazonS3FullAccess` (or create custom policy with read/write to your bucket)
4. Create access keys (Access Key ID and Secret Access Key)

### Step 3: Set Environment Variables in Railway

Go to Railway → Your DocParser service → Variables, and add:

```
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your_access_key_id
S3_SECRET_KEY=your_secret_access_key
S3_REGION=us-east-1
S3_BUCKET=docparser-production
S3_SECURE=true
```

## Option 2: Use Railway's Object Storage (if available)

Railway doesn't have built-in object storage, but you can use:

- **Upstash Redis** (for small files, not recommended for large PDFs)
- **Cloudflare R2** (S3-compatible, free tier available)
- **Backblaze B2** (S3-compatible, cheaper than AWS)

### Using Cloudflare R2 (S3-Compatible)

1. Sign up at [Cloudflare R2](https://developers.cloudflare.com/r2/)
2. Create a bucket
3. Get API credentials
4. Set in Railway:

```
S3_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
S3_ACCESS_KEY=your_r2_access_key
S3_SECRET_KEY=your_r2_secret_key
S3_REGION=auto
S3_BUCKET=docparser
S3_SECURE=true
```

## Option 3: Add MinIO to Railway (For Development/Testing)

You can add MinIO as a separate service in Railway:

1. In Railway, click "+ New" → "Database" → "Add MinIO" (if available)
2. Or use a MinIO Docker image as a service
3. Set environment variables:

```
S3_ENDPOINT=http://minio-service:9000  # Internal service name
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGION=us-east-1
S3_BUCKET=docparser
S3_SECURE=false
```

## Quick Setup: AWS S3 (5 minutes)

1. **Create S3 bucket:**
   ```bash
   # Using AWS CLI (or use web console)
   aws s3 mb s3://docparser-production --region us-east-1
   ```

2. **Create IAM user:**
   - AWS Console → IAM → Users → Create user
   - Attach policy: `AmazonS3FullAccess`
   - Create access key

3. **Set in Railway:**
   - `S3_ENDPOINT=https://s3.amazonaws.com`
   - `S3_ACCESS_KEY=<your-key>`
   - `S3_SECRET_KEY=<your-secret>`
   - `S3_REGION=us-east-1`
   - `S3_BUCKET=docparser-production`
   - `S3_SECURE=true`

## Verify It's Working

After setting environment variables, Railway will redeploy. Check logs to see:

```
✅ S3 bucket 'docparser-production' is accessible
```

If you see errors, check:
- S3 credentials are correct
- Bucket name matches `S3_BUCKET`
- Region matches `S3_REGION`
- Bucket exists and is accessible

## Cost Considerations

- **AWS S3**: ~$0.023/GB storage, $0.005/1000 requests
- **Cloudflare R2**: Free tier (10GB storage, 1M requests/month)
- **Backblaze B2**: $0.005/GB storage, free egress

For production with moderate usage, AWS S3 is reliable and cost-effective.

