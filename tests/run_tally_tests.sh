#!/bin/bash
# Quick test runner for Tally export tests
# Usage: ./run_tally_tests.sh

set -e

echo "🧪 Running Tally Export Tests..."
echo ""

cd "$(dirname "$0")"

echo "1️⃣  Running GST Auto-Fix Tests..."
python3 test_gst_auto_fix.py

echo ""
echo "2️⃣  Showing XML Output..."
python3 show_xml_output.py 2>&1 | grep -A 10 "Purchase\|LEDGERNAME\|CGST\|SGST\|IGST" | head -30

echo ""
echo "✅ All Tally tests completed!"
echo ""
echo "💡 Tip: Run these tests anytime you modify Tally export logic"

