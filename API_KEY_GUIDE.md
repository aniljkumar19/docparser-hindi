# API Key Setup Guide

## DOCPARSER_API_KEY Configuration

### What is it?
This is the **master API key** that clients must use to authenticate with your API when `USE_API_KEY_MIDDLEWARE=true`.

### Can I use any value?
**Yes!** You can use any string value you want. However, for security, use a **strong, random key**.

### Best Practices

#### ✅ DO:
- Use a long, random string (at least 32 characters)
- Use a mix of letters, numbers, and optionally special characters
- Keep it secret (never commit to git, never share publicly)
- Use different keys for different environments (dev/staging/prod)

#### ❌ DON'T:
- Use simple values like `test123` or `password`
- Use predictable patterns like `docparser123`
- Commit the key to git (it's in `.env` which is gitignored)
- Share it in public channels

### Examples

**Good keys:**
```
docparser_prod_a7k9m2p5q8r1s4t6v0w3x7y9z2b5c8d1
DP_PROD_7K9M2P5Q8R1S4T6V0W3X7Y9Z2B5C8D1F4G7H0
a7k9m2p5q8r1s4t6v0w3x7y9z2b5c8d1f4g7h0j3k6m9
```

**Bad keys:**
```
test
docparser
123456
dev_123  # (this is fine for local dev, but not production!)
```

### How to Generate a Secure Key

**Option 1: Python (recommended)**
```python
import secrets
import string

alphabet = string.ascii_letters + string.digits
key = ''.join(secrets.choice(alphabet) for i in range(32))
print(key)
```

**Option 2: OpenSSL**
```bash
openssl rand -hex 32
```

**Option 3: Online generator**
- Use a reputable password generator
- Generate at least 32 characters

### Setting in Railway

1. Go to your Railway project
2. Click on "Variables" tab
3. Add new variable:
   - **Name:** `DOCPARSER_API_KEY`
   - **Value:** Your generated secure key (e.g., `docparser_prod_a7k9m2p5q8r1s4t6v0w3x7y9z2b5c8d1`)
4. Save

### Using the API Key

Once set, clients must include it in requests:

```bash
# Using header
curl -H "x-api-key: docparser_prod_a7k9m2p5q8r1s4t6v0w3x7y9z2b5c8d1" \
  https://your-app.railway.app/v1/jobs

# Using query parameter
curl "https://your-app.railway.app/v1/jobs?api_key=docparser_prod_a7k9m2p5q8r1s4t6v0w3x7y9z2b5c8d1"
```

### Security Notes

1. **Rotate regularly:** Change the key periodically (e.g., every 90 days)
2. **Monitor usage:** Check logs for unauthorized access attempts
3. **Different environments:** Use different keys for dev/staging/prod
4. **Access control:** Only share with authorized clients/developers

### Testing

After setting the key in Railway, test it:

```bash
# Should work
curl -H "x-api-key: YOUR_KEY" https://your-app.railway.app/health

# Should fail (401)
curl https://your-app.railway.app/v1/jobs
```

---

**Quick Start:**
1. Generate a secure key (use Python script above)
2. Set it in Railway as `DOCPARSER_API_KEY`
3. Share with your clients/team (securely!)
4. Test that it works

