import schedule
import time
import sys
from scraper.concert_comparator import ConcertComparator
from scraper.reporting import ScraperReporter

def run_comparator(test_mode: bool = False):
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