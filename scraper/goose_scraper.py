"""
Goose Tour Scraper - Scrapes tour dates from goosetheband.com/tour
"""

import os
import json
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

print('[DEBUG] Starting goose_scraper.py')

class GooseTourScraper:
    def __init__(self):
        print('[DEBUG] Initializing GooseTourScraper...')
        """Initialize the scraper with Chrome options."""
        self.url = "https://goosetheband.com/tour"
        self.chrome_options = Options()
        # self.chrome_options.add_argument("--headless")  # Commented out for debugging
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
    def generate_event_id(self, date: datetime, venue: str) -> str:
        """Generate a unique event ID based on date and venue."""
        unique_string = f"{date.strftime('%Y%m%d')}_{venue}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
        
    def parse_date_range(self, date_text: str) -> Optional[Dict[str, datetime]]:
        """Parse a date range string into start and end dates."""
        print(f"[DEBUG] Parsing date text: {date_text}")
        try:
            if " - " in date_text:
                start_str, end_str = date_text.split(" - ")
                start_date = datetime.strptime(start_str.strip(), "%b %d, %Y")
                end_date = datetime.strptime(end_str.strip(), "%b %d, %Y")
            else:
                start_date = datetime.strptime(date_text.strip(), "%b %d, %Y")
                end_date = start_date
            print(f"[DEBUG] Parsed dates: start={start_date}, end={end_date}")
            return {"start_date": start_date, "end_date": end_date}
        except ValueError as e:
            print(f"[ERROR] Failed to parse date: {e}")
            return None
            
    def extract_ticket_link(self, show_element) -> Optional[str]:
        """Extract the ticket link from a show element."""
        try:
            ticket_link = show_element.find_element(By.CSS_SELECTOR, "a[href*='seated.com']")
            return ticket_link.get_attribute("href")
        except:
            return None
            
    def extract_vip_link(self, show_element) -> Optional[str]:
        """Extract the VIP link from a show element."""
        try:
            vip_link = show_element.find_element(By.CSS_SELECTOR, "a[href*='vip']")
            return vip_link.get_attribute("href")
        except:
            return None
            
    def extract_additional_info(self, show_element) -> List[str]:
        """Extract additional information from a show element."""
        info = []
        try:
            # Look for supporting acts
            supporting = show_element.find_element(By.CSS_SELECTOR, ".supporting")
            if supporting:
                info.append(f"w/ {supporting.text}")
        except:
            pass
            
        try:
            # Look for VIP availability
            vip_text = show_element.find_element(By.CSS_SELECTOR, ".vip-text")
            if vip_text:
                info.append("VIP Available")
        except:
            pass
            
        return info
        
    def scrape_tour_dates(self) -> List[Dict]:
        """Scrape tour dates from the website."""
        print("[DEBUG] Starting to scrape tour dates...")
        driver = webdriver.Chrome(options=self.chrome_options)
        shows = []
        
        try:
            driver.get(self.url)
            print("[DEBUG] Page loaded.")
            time.sleep(2)  # Wait for the page to load
            print("[DEBUG] Waiting for shows to load...")
            show_elements = driver.find_elements(By.CSS_SELECTOR, ".seated-event-row")
            print(f"[DEBUG] Found {len(show_elements)} shows.")
            
            for show in show_elements:
                try:
                    date_text = show.find_element(By.CSS_SELECTOR, ".seated-event-date-cell").text
                    date_text = date_text.replace("\n", " ").replace("  ", " ").strip()
                    date_range = self.parse_date_range(date_text)
                    
                    if date_range:
                        venue = show.find_element(By.CSS_SELECTOR, ".seated-event-venue-name").text
                        location = show.find_element(By.CSS_SELECTOR, ".seated-event-venue-location").text
                        ticket_link = None
                        for a in show.find_elements(By.TAG_NAME, "a"):
                            href = a.get_attribute("href")
                            if href and "seated.com" in href:
                                ticket_link = href
                                break
                        vip_link = None
                        for a in show.find_elements(By.TAG_NAME, "a"):
                            href = a.get_attribute("href")
                            if href and "vip" in href:
                                vip_link = href
                                break
                        additional_info = []
                        details_cell = show.find_elements(By.CSS_SELECTOR, ".seated-event-details-cell")
                        if details_cell:
                            details_text = details_cell[0].text.strip()
                            if details_text:
                                additional_info.append(details_text)
                        event_id = self.generate_event_id(date_range['start_date'], venue)
                        shows.append({
                            "event_id": event_id,
                            "start_date": date_range['start_date'].isoformat(),
                            "end_date": date_range['end_date'].isoformat(),
                            "venue": venue,
                            "location": location,
                            "ticket_link": ticket_link,
                            "vip_link": vip_link,
                            "additional_info": additional_info
                        })
                        print(f"[DEBUG] Added concert: {venue}")
                except Exception as e:
                    print(f"[ERROR] Error processing show: {e}")
                    continue
        except Exception as e:
            print(f"[ERROR] Error scraping tour dates: {e}")
        finally:
            driver.quit()
            
        print(f"[DEBUG] Scraped {len(shows)} concerts.")
        return shows
        
    def save_tour_dates(self, shows: List[Dict]) -> None:
        """Save tour dates to CSV and JSON files with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scraped_concerts_dir = Path("data/scraped_concerts")
        scraped_concerts_dir.mkdir(exist_ok=True)
        
        # Save as JSON
        json_path = scraped_concerts_dir / f"tour_dates_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(shows, f, indent=2)
        print(f"[DEBUG] Saved JSON file to: {json_path}")
            
        # Save as CSV
        csv_path = scraped_concerts_dir / f"tour_dates_{timestamp}.csv"
        if shows:
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=shows[0].keys())
                writer.writeheader()
                writer.writerows(shows)
            print(f"[DEBUG] Saved CSV file to: {csv_path}")
                
def main():
    print('[DEBUG] Entered main()')
    print("[DEBUG] Starting the scraper...")
    scraper = GooseTourScraper()
    print("[DEBUG] Scraper initialized.")
    concerts = scraper.scrape_tour_dates()
    print(f"[DEBUG] Scraped {len(concerts)} concerts.")
    scraper.save_tour_dates(concerts)
    print("[DEBUG] Concerts saved successfully.")
    
if __name__ == "__main__":
    main() 