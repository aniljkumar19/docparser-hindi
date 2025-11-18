"""
Pytest configuration for DocParser tests.

This file helps pytest find and import the application modules.
"""

import sys
import os

# Add api directory to Python path so we can import app modules
api_path = os.path.join(os.path.dirname(__file__), '..', 'api')
if api_path not in sys.path:
    sys.path.insert(0, api_path)

