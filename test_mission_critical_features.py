#!/usr/bin/env python3
"""
Test script for Mission-Critical Features:
1. Rate Limiting + API Key Middleware
2. File Type Validation
3. Better Error Messages

Usage:
    python test_mission_critical_features.py

Make sure your API is running and set these env vars:
- USE_API_KEY_MIDDLEWARE=true (optional, for rate limiting test)
- DOCPARSER_API_KEY=your-test-key (optional, for rate limiting test)
"""

import requests
import time
import json
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000"  # Change if your API runs on different port
TEST_API_KEY = "test-key-123"  # Change to match your DOCPARSER_API_KEY if testing middleware
# Note: If middleware is enabled, use DOCPARSER_API_KEY value
# If middleware is disabled, use dev_123 (default development key)

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_test(name, passed=True):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")

def test_1_rate_limiting():
    """Test 1: Rate Limiting + API Key Middleware"""
    print_section("TEST 1: Rate Limiting + API Key Middleware")
    
    # Check if middleware is enabled
    print("\nNote: This test requires USE_API_KEY_MIDDLEWARE=true and DOCPARSER_API_KEY set")
    print("If middleware is disabled, some tests will be skipped.\n")
    
    # Test 1.1: Public paths should work without API key
    print("\n1.1 Testing public paths (should work without API key):")
    public_paths = ["/health", "/docs", "/openapi.json"]
    for path in public_paths:
        try:
            resp = requests.get(f"{API_BASE}{path}", timeout=5)
            if resp.status_code == 200:
                print_test(f"Public path {path} accessible", True)
            else:
                print_test(f"Public path {path} accessible (status {resp.status_code})", False)
        except Exception as e:
            print_test(f"Public path {path} accessible", False)
            print(f"   Error: {e}")
    
    # Test 1.2: API endpoints should require API key (if middleware enabled)
    print("\n1.2 Testing API key requirement:")
    try:
        resp = requests.get(f"{API_BASE}/v1/jobs", timeout=5)
        if resp.status_code == 401:
            print_test("API endpoint requires authentication", True)
            print(f"   Response: {resp.json()}")
        elif resp.status_code == 200:
            print_test("API endpoint requires authentication (middleware may be disabled)", False)
            print("   Note: Middleware might not be enabled")
        else:
            print_test(f"API endpoint requires authentication (unexpected status {resp.status_code})", False)
    except Exception as e:
        print_test("API endpoint requires authentication", False)
        print(f"   Error: {e}")
    
    # Test 1.3: Rate limiting (if middleware enabled)
    print("\n1.3 Testing rate limiting (sending 70 requests, limit should be 60/min):")
    try:
        headers = {"x-api-key": TEST_API_KEY}
        success_count = 0
        rate_limited_count = 0
        
        for i in range(70):
            resp = requests.get(f"{API_BASE}/v1/jobs", headers=headers, timeout=2)
            if resp.status_code == 200:
                success_count += 1
            elif resp.status_code == 429:
                rate_limited_count += 1
                if rate_limited_count == 1:
                    print(f"   Got rate limited at request #{i+1}")
            elif resp.status_code == 401:
                print(f"   Got 401 (invalid API key) - middleware may be using different key")
                break
            time.sleep(0.1)  # Small delay between requests
        
        if rate_limited_count > 0:
            print_test(f"Rate limiting works ({rate_limited_count} requests rate limited)", True)
        elif success_count == 70:
            print_test("Rate limiting works (middleware may be disabled or limits not reached)", False)
            print("   Note: All requests succeeded - middleware might not be enabled")
        else:
            print_test("Rate limiting works", False)
    except Exception as e:
        print_test("Rate limiting works", False)
        print(f"   Error: {e}")

def test_2_file_type_validation():
    """Test 2: File Type Validation"""
    print_section("TEST 2: File Type Validation")
    
    # Test 2.1: Valid file types should be accepted
    print("\n2.1 Testing valid file types:")
    valid_files = [
        ("test.pdf", "application/pdf", True),
        ("test.json", "application/json", True),
        ("test.csv", "text/csv", True),
        ("test.jpg", "image/jpeg", True),
        ("test.png", "image/png", True),
    ]
    
    for filename, content_type, should_accept in valid_files:
        # Create a dummy file
        test_file = Path("/tmp") / filename
        test_file.write_bytes(b"dummy content")
        
        try:
            with open(test_file, "rb") as f:
                files = {"file": (filename, f, content_type)}
                # Note: This will fail without auth, but we're testing file validation
                resp = requests.post(
                    f"{API_BASE}/v1/parse",
                    files=files,
                    timeout=5
                )
            
            if resp.status_code == 401:
                print_test(f"Valid file {filename} accepted (got 401 auth error, but file validation passed)", True)
            elif resp.status_code == 400:
                error_detail = resp.json().get("detail", {})
                if isinstance(error_detail, dict) and "invalid_file_type" in error_detail.get("error", ""):
                    print_test(f"Valid file {filename} accepted", False)
                else:
                    print_test(f"Valid file {filename} accepted (other 400 error)", True)
            else:
                print_test(f"Valid file {filename} accepted (status {resp.status_code})", True)
        except Exception as e:
            print_test(f"Valid file {filename} accepted", False)
            print(f"   Error: {e}")
        finally:
            if test_file.exists():
                test_file.unlink()
    
    # Test 2.2: Invalid file types should be rejected
    print("\n2.2 Testing invalid file types (should be rejected):")
    invalid_files = [
        ("test.exe", "application/x-msdownload", False),
        ("test.zip", "application/zip", False),
        ("test.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", False),
        ("test.sh", "text/x-shellscript", False),
    ]
    
    for filename, content_type, should_accept in invalid_files:
        test_file = Path("/tmp") / filename
        test_file.write_bytes(b"dummy content")
        
        try:
            with open(test_file, "rb") as f:
                files = {"file": (filename, f, content_type)}
                resp = requests.post(
                    f"{API_BASE}/v1/parse",
                    files=files,
                    timeout=5
                )
            
            if resp.status_code == 400:
                error_detail = resp.json().get("detail", {})
                if isinstance(error_detail, dict):
                    error_code = error_detail.get("error", "")
                    if "invalid_file_type" in error_code or "invalid_mime_type" in error_code:
                        print_test(f"Invalid file {filename} rejected", True)
                        print(f"   Error message: {error_detail.get('message', 'N/A')}")
                    else:
                        print_test(f"Invalid file {filename} rejected (wrong error type)", False)
                else:
                    print_test(f"Invalid file {filename} rejected (unstructured error)", False)
            elif resp.status_code == 401:
                print_test(f"Invalid file {filename} rejected (got 401, but validation should happen first)", False)
            else:
                print_test(f"Invalid file {filename} rejected (unexpected status {resp.status_code})", False)
        except Exception as e:
            print_test(f"Invalid file {filename} rejected", False)
            print(f"   Error: {e}")
        finally:
            if test_file.exists():
                test_file.unlink()

def test_3_error_messages():
    """Test 3: Better Error Messages"""
    print_section("TEST 3: Better Error Messages")
    
    # Test 3.1: Structured error format
    print("\n3.1 Testing structured error format:")
    
    # Test with invalid request (should get 422 with structured error)
    try:
        resp = requests.post(
            f"{API_BASE}/v1/parse",
            json={"invalid": "data"},  # Missing file
            timeout=5
        )
        if resp.status_code == 422:
            error_data = resp.json()
            if "error" in error_data and "message" in error_data:
                print_test("Validation errors have structured format", True)
                print(f"   Error: {error_data.get('error')}")
                print(f"   Message: {error_data.get('message')}")
            else:
                print_test("Validation errors have structured format", False)
        else:
            print_test(f"Validation errors have structured format (status {resp.status_code})", False)
    except Exception as e:
        print_test("Validation errors have structured format", False)
        print(f"   Error: {e}")
    
    # Test 3.2: 404 errors have structured format
    print("\n3.2 Testing 404 error format:")
    try:
        resp = requests.get(f"{API_BASE}/v1/jobs/nonexistent-job-id", timeout=5)
        if resp.status_code == 404:
            error_data = resp.json()
            if isinstance(error_data, dict) and "error" in error_data and "message" in error_data:
                print_test("404 errors have structured format", True)
                print(f"   Error: {error_data.get('error')}")
                print(f"   Message: {error_data.get('message')}")
            else:
                print_test("404 errors have structured format", False)
        elif resp.status_code == 401:
            print_test("404 errors have structured format (got 401, need auth)", False)
        else:
            print_test(f"404 errors have structured format (status {resp.status_code})", False)
    except Exception as e:
        print_test("404 errors have structured format", False)
        print(f"   Error: {e}")
    
    # Test 3.3: File type errors have helpful messages
    print("\n3.3 Testing file type error messages:")
    test_file = Path("/tmp") / "test.exe"
    test_file.write_bytes(b"dummy executable")
    
    try:
        with open(test_file, "rb") as f:
            files = {"file": ("test.exe", f, "application/x-msdownload")}
            resp = requests.post(f"{API_BASE}/v1/parse", files=files, timeout=5)
        
        if resp.status_code == 400:
            error_data = resp.json().get("detail", {})
            if isinstance(error_data, dict):
                message = error_data.get("message", "")
                if "Unsupported file type" in message or "Allowed:" in message:
                    print_test("File type errors have helpful messages", True)
                    print(f"   Message: {message}")
                else:
                    print_test("File type errors have helpful messages", False)
            else:
                print_test("File type errors have helpful messages", False)
        elif resp.status_code == 401:
            print_test("File type errors have helpful messages (got 401, need auth)", False)
        else:
            print_test(f"File type errors have helpful messages (status {resp.status_code})", False)
    except Exception as e:
        print_test("File type errors have helpful messages", False)
        print(f"   Error: {e}")
    finally:
        if test_file.exists():
            test_file.unlink()
    
    # Test 3.4: Health endpoint should work (no errors)
    print("\n3.4 Testing health endpoint (should return 200):")
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code == 200:
            print_test("Health endpoint accessible", True)
            print(f"   Response: {resp.json()}")
        else:
            print_test(f"Health endpoint accessible (status {resp.status_code})", False)
    except Exception as e:
        print_test("Health endpoint accessible", False)
        print(f"   Error: {e}")

def main():
    print("\n" + "=" * 70)
    print("  Mission-Critical Features Test Suite")
    print("=" * 70)
    print(f"\nTesting API at: {API_BASE}")
    print(f"Test API Key: {TEST_API_KEY}")
    print("\nNote: Some tests may fail if middleware is disabled or API key is different")
    
    try:
        # Test all three features
        test_1_rate_limiting()
        test_2_file_type_validation()
        test_3_error_messages()
        
        print_section("Test Summary")
        print("\n✅ All tests completed!")
        print("\nNext steps:")
        print("1. Review any failed tests above")
        print("2. If rate limiting tests failed, check:")
        print("   - USE_API_KEY_MIDDLEWARE=true is set")
        print("   - DOCPARSER_API_KEY matches TEST_API_KEY in this script")
        print("3. Verify file type validation is working in production")
        print("4. Check error messages are user-friendly in the dashboard")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

