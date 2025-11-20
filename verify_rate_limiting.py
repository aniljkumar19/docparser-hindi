#!/usr/bin/env python3
"""
Quick verification script for rate limiting.
Run this after restarting your API server.
"""

import requests
import time

API_BASE = "http://localhost:8000"
API_KEY = "test-key-123"

print("=" * 60)
print("Rate Limiting Verification Test")
print("=" * 60)
print(f"\nAPI: {API_BASE}")
print(f"API Key: {API_KEY}")
print(f"Expected limit: 10 requests/minute\n")

# Test 1: Health check (should work without key)
print("1. Testing /health (public path, no auth needed)...")
try:
    resp = requests.get(f"{API_BASE}/health", timeout=2)
    if resp.status_code == 200:
        print(f"   ✅ Health check: {resp.json()}")
    else:
        print(f"   ❌ Health check failed: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    print("   ⚠️  Make sure API is running on port 8000")
    exit(1)

# Test 2: API endpoint without key (should get 401)
print("\n2. Testing /v1/jobs without API key (should get 401)...")
try:
    resp = requests.get(f"{API_BASE}/v1/jobs", timeout=2)
    if resp.status_code == 401:
        print(f"   ✅ Auth required: {resp.json()}")
    else:
        print(f"   ⚠️  Unexpected status: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: API endpoint with key (should work)
print("\n3. Testing /v1/jobs with API key...")
try:
    resp = requests.get(f"{API_BASE}/v1/jobs", headers={"x-api-key": API_KEY}, timeout=2)
    if resp.status_code == 200:
        print(f"   ✅ Authenticated request: {resp.status_code}")
    elif resp.status_code == 401:
        print(f"   ❌ Auth failed: {resp.json()}")
        print(f"   ⚠️  Check that DOCPARSER_API_KEY in .env matches: {API_KEY}")
    else:
        print(f"   ⚠️  Unexpected status: {resp.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Rate limiting (send 12 requests, should get 429 after 10)
print("\n4. Testing rate limiting (sending 12 requests, limit is 10)...")
success_count = 0
rate_limited = False
for i in range(1, 13):
    try:
        resp = requests.get(
            f"{API_BASE}/v1/jobs?limit=1",
            headers={"x-api-key": API_KEY},
            timeout=2
        )
        status = resp.status_code
        if status == 200:
            success_count += 1
            print(f"   Request {i:2d}: ✅ {status}")
        elif status == 429:
            rate_limited = True
            error_data = resp.json()
            print(f"   Request {i:2d}: 🚫 {status} - {error_data.get('message', 'Rate limited')}")
            print(f"   ✅ Rate limiting is working! Got 429 at request {i}")
            break
        elif status == 401:
            print(f"   Request {i:2d}: ❌ {status} - Auth failed (check API key)")
            break
        else:
            print(f"   Request {i:2d}: ⚠️  {status}")
        time.sleep(0.1)
    except Exception as e:
        print(f"   Request {i:2d}: ❌ Error: {e}")
        break

if not rate_limited:
    print(f"\n   ⚠️  Rate limiting not triggered (got {success_count} successful requests)")
    print("   This could mean:")
    print("   - Middleware is not enabled (check USE_API_KEY_MIDDLEWARE=true)")
    print("   - Rate limit is higher than expected")
    print("   - Using legacy auth system instead of middleware")

print("\n" + "=" * 60)
print("Test Complete!")
print("=" * 60)

