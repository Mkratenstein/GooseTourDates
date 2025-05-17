"""
Pytest configuration file
"""

import pytest
import os
import sys

# Add the scraper directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure pytest
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    ) 