"""
Goose Tour Dates Scraper
Scrapes tour dates from goosetheband.com/tour
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
from typing import List, Dict, Optional
import logging
from logging.handlers import RotatingFileHandler
import time
import json
import csv
import os
import hashlib

# Set up logging
def setup_logging():
    """Configure logging with rotation"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create formatters
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Create and configure file handler with rotation
    file_handler = RotatingFileHandler(
        'logs/scraper.log',
        maxBytes=1024*1024,  # 1MB
        backupCount=5,       # Keep 5 backup files
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    
    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

class GooseTourScraper:
    """Scraper for Goose tour dates"""
    
    BASE_URL = "https://goosetheband.com/tour"
    
    def __init__(self):
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Initialize the Chrome driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
    
    def fetch_tour_page(self) -> Optional[str]:
        """Fetch the tour page content using Selenium"""
        try:
            logger.info("Loading tour page with Selenium...")
            self.driver.get(self.BASE_URL)
            
            # Wait for the event rows to be loaded
            logger.info("Waiting for event rows to load...")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "seated-event-row"))
            )
            
            # Get the page source after JavaScript has loaded
            return self.driver.page_source
            
        except Exception as e:
            logger.error(f"Error fetching tour page: {e}")
            return None
        finally:
            self.driver.quit()
    
    def parse_date_range(self, date_text: str) -> Optional[Dict[str, datetime]]:
        """Parse a date range string into start and end dates"""
        try:
            # Clean up the date text
            date_text = date_text.strip().replace('\n', ' ').replace('  ', ' ')
            
            if " - " in date_text:
                # Handle multi-day events
                start_str, end_str = date_text.split(" - ")
                # Clean up each date string
                start_str = start_str.strip()
                end_str = end_str.strip()
                
                # Parse the dates
                start_date = parser.parse(start_str)
                end_date = parser.parse(end_str)
                
                return {
                    'start_date': start_date,
                    'end_date': end_date
                }
            else:
                # Handle single-day events
                date = parser.parse(date_text)
                return {
                    'start_date': date,
                    'end_date': date
                }
        except Exception as e:
            logger.error(f"Error parsing date range '{date_text}': {e}")
            return None
    
    def generate_event_id(self, date: datetime, venue: str) -> str:
        """Generate a unique event ID based on date and venue"""
        # Create a string combining date and venue
        base_string = f"{date.strftime('%Y%m%d')}_{venue}"
        # Create a hash of the string to ensure uniqueness
        return hashlib.md5(base_string.encode()).hexdigest()[:12]

    def scrape_tour_dates(self) -> List[Dict]:
        """Scrape all tour dates and return as a list of dictionaries"""
        tour_dates = []
        
        try:
            # Fetch the tour page
            logger.info("Starting tour date scraping...")
            content = self.fetch_tour_page()
            if not content:
                logger.error("No content received from tour page")
                return tour_dates
            
            # Parse the HTML
            logger.info("Parsing HTML content...")
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all event rows
            logger.info("Looking for event rows...")
            event_rows = soup.find_all('div', class_='seated-event-row')
            logger.info(f"Found {len(event_rows)} event rows")
            
            for row in event_rows:
                try:
                    # Extract date
                    date_cell = row.find('div', class_='seated-event-date-cell')
                    if not date_cell:
                        logger.warning("Skipping row: No date cell found")
                        continue
                    date_text = date_cell.get_text(strip=True)
                    date_info = self.parse_date_range(date_text)
                    if not date_info:
                        logger.warning(f"Skipping row: Could not parse date: {date_text}")
                        continue
                    
                    # Extract venue and location
                    venue_cell = row.find('div', class_='seated-event-venue-cell')
                    if not venue_cell:
                        logger.warning("Skipping row: No venue cell found")
                        continue
                    
                    venue_name = venue_cell.find('div', class_='seated-event-venue-name')
                    venue_location = venue_cell.find('div', class_='seated-event-venue-location')
                    
                    if not venue_name:
                        logger.warning("Skipping row: No venue name found")
                        continue
                    if not venue_location:
                        logger.warning("Skipping row: No venue location found")
                        continue
                    
                    venue_name_text = venue_name.get_text(strip=True)
                    venue_location_text = venue_location.get_text(strip=True)
                    
                    if not venue_name_text or not venue_location_text:
                        logger.warning("Skipping row: Empty venue name or location")
                        continue
                    
                    # Generate event ID
                    event_id = self.generate_event_id(date_info['start_date'], venue_name_text)
                    
                    # Extract ticket links
                    ticket_links = row.find_all('a', class_='seated-event-link')
                    ticket_link = None
                    vip_link = None
                    
                    for link in ticket_links:
                        if 'vip' in link.text.lower():
                            vip_link = link.get('href')
                        elif 'ticket' in link.text.lower():
                            ticket_link = link.get('href')
                    
                    # Extract additional details
                    details_cell = row.find('div', class_='seated-event-details-cell')
                    additional_info = []
                    if details_cell:
                        details_text = details_cell.get_text(strip=True)
                        if details_text:
                            additional_info.append(details_text)
                    
                    # Create show dictionary
                    show = {
                        'event_id': event_id,
                        'start_date': date_info['start_date'],
                        'end_date': date_info['end_date'],
                        'venue': venue_name_text,
                        'location': venue_location_text,
                        'ticket_link': ticket_link,
                        'vip_link': vip_link,
                        'additional_info': additional_info
                    }
                    
                    tour_dates.append(show)
                    logger.info(f"Successfully processed show: {show['venue']} on {show['start_date'].strftime('%Y-%m-%d')}")
                    
                except Exception as e:
                    logger.error(f"Error processing event row: {e}")
                    continue
            
            logger.info(f"Finished processing {len(tour_dates)} shows")
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        
        return tour_dates

def main():
    """Main function to run the scraper"""
    scraper = GooseTourScraper()
    tour_dates = scraper.scrape_tour_dates()
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Save as JSON
    json_path = 'data/tour_dates.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        # Convert datetime objects to strings for JSON serialization
        json_data = []
        for show in tour_dates:
            show_copy = show.copy()
            show_copy['start_date'] = show_copy['start_date'].isoformat()
            show_copy['end_date'] = show_copy['end_date'].isoformat()
            json_data.append(show_copy)
        json.dump(json_data, f, indent=2)
    logger.info(f"Saved tour dates to {json_path}")
    
    # Save as CSV
    csv_path = 'data/tour_dates.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'event_id', 'start_date', 'end_date', 'venue', 'location', 
            'ticket_link', 'vip_link', 'additional_info'
        ])
        writer.writeheader()
        for show in tour_dates:
            show_copy = show.copy()
            show_copy['start_date'] = show_copy['start_date'].strftime('%Y-%m-%d')
            show_copy['end_date'] = show_copy['end_date'].strftime('%Y-%m-%d')
            show_copy['additional_info'] = ' | '.join(show_copy['additional_info'])
            writer.writerow(show_copy)
    logger.info(f"Saved tour dates to {csv_path}")
    
    # Log results summary
    logger.info("\nScraped Tour Dates Summary:")
    logger.info("=" * 50)
    for show in tour_dates:
        logger.info(f"\nShow Details:")
        for key, value in show.items():
            logger.info(f"{key}: {value}")

if __name__ == "__main__":
    main() 