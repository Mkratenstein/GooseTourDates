"""
Scheduler module for the Goose Tour Scraper.

This module provides functionality for:
- Running the scraper and comparator on a schedule
- One-time execution mode
- Test mode for development
- Error handling and logging

The scheduler can run in three modes:
1. Continuous mode: Runs every 6 hours
2. Once mode: Runs once and exits
3. Test mode: Skips the scraper and uses existing files
"""

import schedule
import time
import sys
from scraper.concert_comparator import ConcertComparator
from scraper.reporting import ScraperReporter

def run_comparator(test_mode: bool = False):
    """
    Run a single comparison cycle.
    
    This function:
    1. Initializes the reporter for logging
    2. Creates a ConcertComparator instance
    3. Processes new concerts
    4. Logs results and any errors
    
    Args:
        test_mode (bool): If True, skips the scraper and uses existing files
    """
    reporter = ScraperReporter()
    reporter.log_scrape_start()
    print("[DEBUG] ==========================================")
    print("[DEBUG] Starting new comparison cycle...")
    print("[DEBUG] Creating ConcertComparator instance...")
    try:
        comparator = ConcertComparator(test_mode=test_mode)
        print("[DEBUG] Calling process_new_concerts()...")
        new_concerts = comparator.process_new_concerts()
        print(f"[DEBUG] Comparison cycle complete. Found {len(new_concerts)} new concerts.")
        reporter.log_new_concerts(new_concerts)
        reporter.log_scrape_end(len(new_concerts))
    except Exception as e:
        reporter.log_error(e, "scheduler run_comparator")
        print(f"[ERROR] Error in scheduler: {e}")
    print("[DEBUG] ==========================================")

def main():
    """
    Main entry point for the scheduler.
    
    Handles command line arguments and sets up the appropriate mode:
    - --once: Run once and exit
    - --test: Run in test mode (skip scraper)
    
    If no arguments are provided, runs in continuous mode (every 6 hours).
    """
    print("[DEBUG] Scheduler started.")
    test_mode = "--test" in sys.argv
    if test_mode:
        print("[DEBUG] Running in TEST MODE - will skip scraper")
    
    if "--once" in sys.argv:
        print("[DEBUG] Running in 'once' mode - will exit after one run")
        run_comparator(test_mode=test_mode)
        print("[DEBUG] One-time run complete. Exiting.")
        return
        
    print("[DEBUG] Running in continuous mode - will check every 6 hours")
    schedule.every(6).hours.do(run_comparator, test_mode=test_mode)
    run_comparator(test_mode=test_mode)  # Run immediately on startup

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 