"""
Goose Tour Dates Scraper

This module scrapes Goose's official website for tour dates and outputs structured concert data.
- Used by the Discord bot to provide up-to-date concert information.
- Handles all scraping, parsing, and error handling.
- No test/dev code remains in this production version.

This module provides functionality for:
- Scraping concert dates and details from goosetheband.com
- Generating unique event IDs for concerts
- Parsing date ranges and concert information
- Saving concert data to JSON and CSV formats
- Error handling and logging

The scraper uses Selenium WebDriver to handle dynamic content loading
and JavaScript execution on the tour page.
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
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
from scraper.reporting import ScraperReporter

print('[DEBUG] Starting goose_scraper.py')

class GooseTourScraper:
    """
    Scrapes tour dates and details from goosetheband.com/tour.
    
    This class handles:
    - Web scraping using Selenium WebDriver
    - Date parsing and validation
    - Event ID generation
    - Data storage in JSON and CSV formats
    - Error handling and logging
    
    Attributes:
        url (str): URL of the tour page to scrape
        chrome_options (Options): Chrome WebDriver options
        data_dir (Path): Directory for storing scraped data
        reporter (ScraperReporter): Reporter instance for logging
    """
    
    def __init__(self):
        """
        Initialize the scraper with Chrome options and directories.
        
        Sets up:
        - Chrome WebDriver options
        - Data directory structure
        - Reporter for logging
        """
        print('[DEBUG] Initializing GooseTourScraper...')
        self.url = "https://goosetheband.com/tour"
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-software-rasterizer")
        self.chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        self.chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        self.data_dir = Path("scraper/data")
        self.data_dir.mkdir(exist_ok=True)
        self.reporter = ScraperReporter()
        
    def generate_event_id(self, date: datetime, venue: str) -> str:
        """
        Generate a unique event ID based on date and venue.
        
        Args:
            date (datetime): Event date
            venue (str): Venue name
            
        Returns:
            str: 12-character hexadecimal event ID
        """
        unique_string = f"{date.strftime('%Y%m%d')}_{venue}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
        
    def parse_date_range(self, date_text: str) -> Optional[Dict[str, datetime]]:
        """
        Parse a date range string into start and end dates.
        
        Args:
            date_text (str): Date string in format "MMM DD, YYYY" or "MMM DD, YYYY - MMM DD, YYYY"
            
        Returns:
            Optional[Dict[str, datetime]]: Dictionary with start_date and end_date,
                                         or None if parsing fails
        """
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
        """
        Extract the ticket link from a show element.
        
        Args:
            show_element: Selenium WebElement containing show information
            
        Returns:
            Optional[str]: Ticket link URL or None if not found
        """
        try:
            ticket_link = show_element.find_element(By.CSS_SELECTOR, "a[href*='seated.com']")
            return ticket_link.get_attribute("href")
        except:
            return None
            
    def extract_vip_link(self, show_element) -> Optional[str]:
        """
        Extract the VIP link from a show element.
        
        Args:
            show_element: Selenium WebElement containing show information
            
        Returns:
            Optional[str]: VIP link URL or None if not found
        """
        try:
            vip_link = show_element.find_element(By.CSS_SELECTOR, "a[href*='vip']")
            return vip_link.get_attribute("href")
        except:
            return None
            
    def extract_additional_info(self, show_element) -> List[str]:
        """
        Extract additional information from a show element.
        
        Args:
            show_element: Selenium WebElement containing show information
            
        Returns:
            List[str]: List of additional information strings
        """
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
            
        try:
            # Look for additional details in seated-event-details-cell
            details_cell = show_element.find_element(By.CSS_SELECTOR, ".seated-event-details-cell")
            if details_cell:
                details_text = details_cell.text.strip()
                if details_text:
                    info.append(details_text)
        except:
            pass
            
        return info
        
    def scrape_tour_dates(self) -> List[Dict]:
        """
        Scrape tour dates from the website.
        
        Returns:
            List[Dict]: List of concert dictionaries containing:
                - event_id: Unique identifier
                - start_date: Event start date
                - end_date: Event end date
                - venue: Venue name
                - location: Venue location
                - ticket_link: Link to purchase tickets
                - vip_link: Link to VIP tickets (if available)
                - additional_info: List of additional information
        """
        print("[DEBUG] Starting to scrape tour dates...")
        self.reporter.log_scrape_start()
        
        # Set up Chrome service with webdriver-manager
        driver_path = ChromeDriverManager().install()
        # Handle the nested directory structure
        if 'chromedriver-linux64' in driver_path:
            driver_path = os.path.join(os.path.dirname(driver_path), 'chromedriver-linux64', 'chromedriver')
        print(f"[DEBUG] Using ChromeDriver path: {driver_path}")
        
        # Ensure the driver is executable
        os.chmod(driver_path, 0o755)
        
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=self.chrome_options)
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
                        ticket_link = self.extract_ticket_link(show)
                        vip_link = self.extract_vip_link(show)
                        additional_info = self.extract_additional_info(show)
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
                    self.reporter.log_error(e, "processing show")
                    continue
        except Exception as e:
            print(f"[ERROR] Error scraping tour dates: {e}")
            self.reporter.log_error(e, "scraping tour dates")
        finally:
            driver.quit()
            
        print(f"[DEBUG] Scraped {len(shows)} concerts.")
        self.reporter.log_scrape_end(len(shows))
        return shows
        
    def save_tour_dates(self, shows: List[Dict]) -> None:
        """
        Save tour dates to CSV and JSON files with timestamp.
        
        Args:
            shows (List[Dict]): List of concert dictionaries to save
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scraped_concerts_dir = Path("scraper/data/scraped_concerts")
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
    """
    Main entry point for the scraper.
    
    Initializes the scraper, runs it, and saves the results.
    """
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