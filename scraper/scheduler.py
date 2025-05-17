"""
Scheduler module for the Goose Tour Scraper.

This module provides functionality for:
- Running the scraper and comparator on a schedule
- One-time execution mode
- Test mode for development
- Error handling and logging
- Discord bot integration

The scheduler can run in three modes:
1. Continuous mode: Runs every 6 hours
2. Once mode: Runs once and exits
3. Test mode: Skips the scraper and uses existing files
"""

import schedule
import time
import sys
import asyncio
import logging
import traceback
from pathlib import Path
from scraper.concert_comparator import ConcertComparator
from scraper.reporting import ScraperReporter
from scraper.discord_bot import GooseTourBot, run_bot, BotError
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('scheduler')

class SchedulerError(Exception):
    """Base exception for scheduler-related errors."""
    pass

def ensure_directories():
    """Ensure all required directories exist."""
    try:
        # Create data directories
        Path("data/scraped_concerts").mkdir(parents=True, exist_ok=True)
        Path("data/new_concerts").mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        logger.info("Required directories verified/created")
    except Exception as e:
        logger.error(f"Failed to create required directories: {e}")
        raise SchedulerError(f"Directory setup failed: {e}")

def run_comparator(test_mode: bool = False):
    """
    Run a single comparison cycle.
    
    This function:
    1. Initializes the reporter for logging
    2. Creates a ConcertComparator instance
    3. Processes new concerts
    4. Logs results and any errors
    5. Posts new concerts to Discord
    
    Args:
        test_mode (bool): If True, skips the scraper and uses existing files
    """
    reporter = ScraperReporter()
    reporter.log_scrape_start()
    logger.info("Starting new comparison cycle...")
    
    try:
        logger.debug("Creating ConcertComparator instance...")
        comparator = ConcertComparator(test_mode=test_mode)
        
        logger.debug("Calling process_new_concerts()...")
        new_concerts = comparator.process_new_concerts()
        
        logger.info(f"Comparison cycle complete. Found {len(new_concerts)} new concerts.")
        reporter.log_new_concerts(new_concerts)
        reporter.log_scrape_end(len(new_concerts))
        
        # Post new concerts to Discord if any found
        if new_concerts:
            try:
                asyncio.run(goose_bot.post_new_concerts(new_concerts))
                logger.info(f"Posted {len(new_concerts)} new concerts to Discord")
            except Exception as e:
                logger.error(f"Failed to post concerts to Discord: {e}")
                reporter.log_error(e, "Discord posting")
                
    except Exception as e:
        error_msg = f"Error in scheduler: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        reporter.log_error(e, "scheduler run_comparator")
        raise SchedulerError(error_msg)

def main():
    """
    Main entry point for the scheduler.
    
    Handles command line arguments and sets up the appropriate mode:
    - --once: Run once and exit
    - --test: Run in test mode (skip scraper)
    
    If no arguments are provided, runs in continuous mode (every 6 hours).
    """
    try:
        logger.info("Scheduler starting...")
        ensure_directories()
        
        test_mode = "--test" in sys.argv
        if test_mode:
            logger.info("Running in TEST MODE - will skip scraper")
        
        if "--once" in sys.argv:
            logger.info("Running in 'once' mode - will exit after one run")
            try:
                run_comparator(test_mode=test_mode)
                logger.info("One-time run complete. Exiting.")
            except SchedulerError as e:
                logger.error(f"One-time run failed: {e}")
                sys.exit(1)
            return
            
        logger.info("Running in continuous mode - will check every 6 hours")
        schedule.every(6).hours.do(run_comparator, test_mode=test_mode)
        
        # Run immediately on startup
        try:
            run_comparator(test_mode=test_mode)
        except SchedulerError as e:
            logger.error(f"Initial run failed: {e}")
            # Don't exit, continue with scheduled runs
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}\n{traceback.format_exc()}")
                time.sleep(300)  # Wait 5 minutes before retrying
                
    except Exception as e:
        logger.error(f"Fatal scheduler error: {e}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Start the Discord bot
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        logger.info("Discord bot thread started")
        
        # Run the scheduler
        main()
    except Exception as e:
        logger.error(f"Fatal error in main thread: {e}\n{traceback.format_exc()}")
        sys.exit(1) 