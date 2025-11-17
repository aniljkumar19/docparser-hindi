#!/usr/bin/env python3
"""
Test script for bulk processing functionality
"""

import requests
import json
import time
import os

# Configuration
API_BASE = "http://localhost:8000"
API_KEY = "dev_123"

def test_bulk_upload():
    """Test bulk document upload"""
    
    # Prepare test files (using existing sample files)
    test_files = [
        ("api/samples/sample_invoice.txt", "invoice1.txt"),
        ("api/samples/sample_indian_invoice.txt", "invoice2.txt"),
        ("api/samples/sample_eway_bill.txt", "eway_bill.txt")
    ]
    
    # Create form data
    files = []
    for file_path, filename in test_files:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                files.append(('files', (filename, f.read(), 'text/plain')))
    
    if not files:
        print("❌ No test files found")
        return None
    
    # Add metadata
    data = {
        'client_id': 'client_test123',
        'batch_name': 'Test Batch - January 2024'
    }
    
    print(f"🚀 Uploading {len(files)} files...")
    
    # Upload files
    response = requests.post(
        f"{API_BASE}/v1/bulk-parse",
        headers={"Authorization": f"Bearer {API_KEY}"},
        files=files,
        data=data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   Batch ID: {result['batch_id']}")
        print(f"   Total files: {result['total_files']}")
        print(f"   Job IDs: {len(result['job_ids'])}")
        return result['batch_id']
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def poll_batch_status(batch_id):
    """Poll batch status until completion"""
    
    print(f"📊 Polling batch status for {batch_id}...")
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        response = requests.get(
            f"{API_BASE}/v1/batches/{batch_id}",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        
        if response.status_code == 200:
            status = response.json()
            
            progress = status['progress']
            print(f"   Progress: {progress['completed']}/{progress['total']} completed, "
                  f"{progress['failed']} failed, {progress['processing']} processing")
            
            if status['status'] == 'completed':
                print("✅ Batch processing completed!")
                return status
            elif status['status'] == 'failed':
                print("❌ Batch processing failed!")
                return status
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return None
        
        attempt += 1
        time.sleep(2)
    
    print("⏰ Timeout waiting for batch completion")
    return None

def export_batch_results(batch_id, format_type="json"):
    """Export batch results"""
    
    print(f"📤 Exporting batch results in {format_type} format...")
    
    response = requests.get(
        f"{API_BASE}/v1/batches/{batch_id}/export",
        params={"format": format_type},
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Export successful!")
        
        if format_type == "json":
            print(f"   Total documents: {result.get('total_documents', 0)}")
            print(f"   Successful: {result.get('successful_documents', 0)}")
            
            # Show sample results
            results = result.get('results', [])
            if results:
                print(f"   Sample result keys: {list(results[0].keys())}")
        
        return result
    else:
        print(f"❌ Export failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def main():
    """Main test function"""
    
    print("🧪 Testing Bulk Processing Functionality")
    print("=" * 50)
    
    # Test 1: Bulk upload
    batch_id = test_bulk_upload()
    if not batch_id:
        return
    
    # Test 2: Poll status
    status = poll_batch_status(batch_id)
    if not status:
        return
    
    # Test 3: Export results
    export_batch_results(batch_id, "json")
    export_batch_results(batch_id, "csv")
    
    print("\n🎉 Bulk processing test completed!")

if __name__ == "__main__":
    main()

