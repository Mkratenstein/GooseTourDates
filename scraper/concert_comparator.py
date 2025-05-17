"""
Concert Comparator for Goose Tour Dates

This module compares newly scraped concert data with previously stored data to detect new concerts.
- Used by the Discord bot to identify and post only new concerts.
- Handles all comparison logic and error handling.
- No test/dev code remains in this production version.
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Optional
from scraper.goose_scraper import GooseTourScraper
from scraper.reporting import ScraperReporter

class ConcertComparator:
    def __init__(self, data_dir: str = "scraper/data", test_mode: bool = False):
        """Initialize the ConcertComparator with the data directory path."""
        self.data_dir = Path(data_dir)
        self.scraped_concerts_dir = self.data_dir / "scraped_concerts"
        self.new_concerts_dir = self.data_dir / "new_concerts"
        self.new_concerts_dir.mkdir(exist_ok=True)
        self.scraped_concerts_dir.mkdir(exist_ok=True)
        self.test_mode = test_mode
        self.reporter = ScraperReporter()
        print(f"[DEBUG] Initialized ConcertComparator with data directory: {self.data_dir}")
        if test_mode:
            print("[DEBUG] Running in TEST MODE - will skip scraper")
        
    def load_previous_concerts(self) -> List[Dict]:
        """Load the second most recent concerts from JSON file."""
        json_files = sorted(list(self.scraped_concerts_dir.glob("tour_dates_*.json")))
        if len(json_files) < 2:
            print("[DEBUG] Not enough previous concert files found.")
            return []
        # Get the second most recent file
        previous_file = json_files[-2]
        print(f"[DEBUG] Loading previous concerts from: {previous_file}")
        with open(previous_file, 'r') as f:
            concerts = json.load(f)
            print(f"[DEBUG] Loaded {len(concerts)} previous concerts")
            return concerts
            
    def load_current_concerts(self, current_file: str) -> List[Dict]:
        """Load the current concerts from a JSON file."""
        print(f"[DEBUG] Loading current concerts from: {current_file}")
        with open(current_file, 'r') as f:
            concerts = json.load(f)
            print(f"[DEBUG] Loaded {len(concerts)} current concerts")
            return concerts
            
    def find_new_concerts(self, current_concerts: List[Dict], previous_concerts: List[Dict]) -> List[Dict]:
        """Find concerts that are in current_concerts but not in previous_concerts."""
        # Create sets of event IDs for quick comparison
        previous_ids = {concert['event_id'] for concert in previous_concerts}
        print(f"[DEBUG] Found {len(previous_ids)} previous event IDs")
        
        # Find new concerts
        new_concerts = [
            concert for concert in current_concerts 
            if concert['event_id'] not in previous_ids
        ]
        
        if new_concerts:
            print("[DEBUG] New concerts found:")
            for concert in new_concerts:
                print(f"  - {concert['venue']} on {concert['start_date']}")
        else:
            print("[DEBUG] No new concerts found")
            
        return new_concerts
        
    def save_new_concerts(self, new_concerts: List[Dict], timestamp: Optional[str] = None) -> None:
        """Save new concerts to JSON and CSV files with timestamp."""
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # Save as JSON
        json_path = self.new_concerts_dir / f"new_concerts_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(new_concerts, f, indent=2)
        print(f"[DEBUG] Saved new concerts to JSON: {json_path}")
            
        # Save as CSV
        csv_path = self.new_concerts_dir / f"new_concerts_{timestamp}.csv"
        if new_concerts:
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=new_concerts[0].keys())
                writer.writeheader()
                writer.writerows(new_concerts)
            print(f"[DEBUG] Saved new concerts to CSV: {csv_path}")
                
    def cleanup_old_files(self):
        """Keep only the 2 most recent JSON and CSV files in scraped_concerts directory."""
        # Get all JSON and CSV files
        json_files = sorted(list(self.scraped_concerts_dir.glob("tour_dates_*.json")))
        csv_files = sorted(list(self.scraped_concerts_dir.glob("tour_dates_*.csv")))
        
        print(f"[DEBUG] Found {len(json_files)} JSON files and {len(csv_files)} CSV files")
        
        # Delete all but the 2 most recent files
        for files in [json_files[:-2], csv_files[:-2]]:
            for file in files:
                print(f"[DEBUG] Deleting old file: {file}")
                file.unlink()
                
    def process_new_concerts(self) -> List[Dict]:
        """Process and save new concerts between current and previous scrape."""
        self.reporter.log_scrape_start()
        try:
            if not self.test_mode:
                print("[DEBUG] Running scraper to get latest concerts...")
                scraper = GooseTourScraper()
                concerts = scraper.scrape_tour_dates()
                scraper.save_tour_dates(concerts)
            else:
                print("[DEBUG] Test mode: Skipping scraper")
            json_files = sorted(list(self.scraped_concerts_dir.glob("tour_dates_*.json")))
            if not json_files:
                print("[DEBUG] No concert files found.")
                return []
            current_file = json_files[-1]
            print(f"[DEBUG] Processing with current file: {current_file}")
            current_concerts = self.load_current_concerts(str(current_file))
            previous_concerts = self.load_previous_concerts()
            new_concerts = self.find_new_concerts(current_concerts, previous_concerts)
            if new_concerts:
                self.save_new_concerts(new_concerts)
                self.reporter.log_new_concerts(new_concerts)
            self.cleanup_old_files()
            self.reporter.log_scrape_end(len(current_concerts))
            return new_concerts
        except Exception as e:
            self.reporter.log_error(e, "comparator process_new_concerts")
            print(f"[ERROR] Error in comparator: {e}")
            return [] 