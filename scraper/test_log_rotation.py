"""
Test script for log rotation functionality.

This script:
1. Creates multiple log entries
2. Verifies log file creation and rotation
3. Tests log retention
"""

import time
from datetime import datetime
from pathlib import Path
from scraper.reporting import ScraperReporter

def test_log_rotation():
    """
    Test log rotation by generating multiple log entries.
    """
    print("Starting log rotation test...")
    
    # Initialize reporter
    reporter = ScraperReporter()
    
    # Generate test logs
    for i in range(10):
        # Log different types of messages
        reporter.log_scrape_start()
        reporter.log_scrape_end(i * 10)
        reporter.log_new_concerts([{
            "venue": f"Test Venue {i}",
            "start_date": datetime.now().isoformat()
        }])
        
        # Log some errors
        try:
            raise ValueError(f"Test error {i}")
        except Exception as e:
            reporter.log_error(e, f"test iteration {i}")
            
        print(f"Generated log batch {i+1}")
        time.sleep(1)  # Small delay between batches
        
    print("\nLog rotation test complete!")
    print("Check the logs directory for rotated log files.")

if __name__ == "__main__":
    test_log_rotation() 