from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime
import os
import time
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_chrome_version():
    """Get the installed Chrome version."""
    try:
        # Try different commands to get Chrome version
        for cmd in ['google-chrome --version', 'google-chrome-stable --version']:
            try:
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    logger.info(f"Found Chrome version: {version}")
                    return version
            except:
                continue
        return None
    except Exception as e:
        logger.error(f"Error getting Chrome version: {e}")
        return None

def setup_driver():
    """Set up and return a Chrome WebDriver instance."""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Get Chrome version
        chrome_version = get_chrome_version()
        if not chrome_version:
            raise Exception("Could not determine Chrome version")
        
        # Use the system Chrome binary
        chrome_options.binary_location = '/usr/bin/google-chrome'
        
        # Use specific ChromeDriver path
        service = Service('/usr/local/bin/chromedriver')
        
        # Create driver with service and options
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set window size
        driver.set_window_size(1920, 1080)
        
        return driver
    except Exception as e:
        logger.error(f"Error setting up Chrome driver: {e}")
        raise

def process_date(date_str):
    """Process a date string and return a standardized format."""
    try:
        # Check if it's a date range
        if " - " in date_str:
            start_date, end_date = date_str.split(" - ")
            # Process both dates
            start_obj = None
            end_obj = None
            
            # Try common formats for both dates
            for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"]:
                try:
                    start_obj = datetime.strptime(start_date.strip(), fmt)
                    end_obj = datetime.strptime(end_date.strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if start_obj and end_obj:
                return f"{start_obj.strftime('%Y-%m-%d')} to {end_obj.strftime('%Y-%m-%d')}"
        
        # Single date processing
        for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"]:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return date_str  # Return original if no format matches
    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
        return date_str

def scrape_goose_tour_dates():
    driver = None
    try:
        # Set up the driver
        logger.info("Setting up Chrome driver...")
        driver = setup_driver()
        
        # Navigate to tour page
        logger.info("Navigating to Goose tour page...")
        driver.get("https://www.goosetheband.com/tour")
        
        # Wait for the page to load completely
        logger.info("Waiting for page to load...")
        wait = WebDriverWait(driver, 30)
        
        # First wait for the body to be present
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Then wait for the tour container with a longer timeout
        logger.info("Waiting for tour dates to load...")
        try:
            tour_container = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "seated-event-row"))
            )
        except Exception as e:
            logger.error(f"Timeout waiting for tour container: {e}")
            # Try to get the page source for debugging
            logger.info("Page source:")
            logger.info(driver.page_source)
            return None
        
        # Add a small delay to ensure dynamic content is loaded
        time.sleep(5)
        
        # Extract tour data
        logger.info("Extracting tour dates...")
        tour_dates = []
        
        # Find all event containers
        event_elements = driver.find_elements(By.CSS_SELECTOR, ".seated-event-row")
        logger.info(f"Found {len(event_elements)} event elements")
        
        # Track processed dates to prevent duplicates
        processed_dates = set()
        
        for event in event_elements:
            try:
                # Skip past events
                if "past-event" in event.get_attribute("class"):
                    continue
                
                # Extract all information first before processing
                date_element = event.find_element(By.CSS_SELECTOR, ".seated-event-date-cell")
                venue_element = event.find_element(By.CSS_SELECTOR, ".seated-event-venue-name")
                location_element = event.find_element(By.CSS_SELECTOR, ".seated-event-venue-location")
                
                # Get the text values
                date_str = date_element.text.strip() if date_element else ""
                venue = venue_element.text.strip() if venue_element else ""
                location = location_element.text.strip() if location_element else ""
                
                # Skip if we're missing essential information
                if not all([date_str, venue, location]):
                    continue
                
                # Create a unique identifier for the event
                event_id = f"{date_str}_{venue}_{location}"
                
                # Skip if we've already processed this event
                if event_id in processed_dates:
                    continue
                
                processed_dates.add(event_id)
                
                # Extract details info if present
                try:
                    details_element = event.find_element(By.CSS_SELECTOR, ".seated-event-details-cell")
                    details = details_element.text.strip()
                except:
                    details = ""
                
                # Extract ticket links
                ticket_links = []
                ticket_elements = event.find_elements(By.CSS_SELECTOR, ".seated-event-link")
                for ticket_element in ticket_elements:
                    ticket_link = ticket_element.get_attribute("href")
                    ticket_text = ticket_element.text.strip()
                    if ticket_link and ticket_text:
                        ticket_links.append(f"{ticket_text}: {ticket_link}")
                
                # Join ticket links with semicolons
                ticket_links_str = "; ".join(ticket_links)
                
                tour_dates.append({
                    "date": date_str,
                    "venue": venue,
                    "location": location,
                    "ticketLinks": ticket_links_str,
                    "additionalInfo": details if details else ""  # Only include details if they exist
                })
                
            except Exception as e:
                logger.warning(f"Error processing event: {e}")
                continue
        
        if not tour_dates:
            logger.warning("No tour dates found in the page")
            # Log the page source for debugging
            logger.info("Page source:")
            logger.info(driver.page_source)
        
        # Process dates to ensure consistent format
        processed_dates = []
        for event in tour_dates:
            event["date"] = process_date(event["date"])
            processed_dates.append(event)
        
        return processed_dates
        
    except Exception as e:
        logger.error(f"Error scraping tour dates: {e}")
        # Log the page source for debugging
        if driver:
            logger.info("Page source:")
            logger.info(driver.page_source)
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

def format_date_for_display(date_str):
    """Format date string for display in Month Day, YYYY format."""
    try:
        if " to " in date_str:
            start_date, end_date = date_str.split(" to ")
            start_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_obj = datetime.strptime(end_date, "%Y-%m-%d")
            return f"{start_obj.strftime('%B %d, %Y')} to {end_obj.strftime('%B %d, %Y')}"
        else:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%B %d, %Y")
    except Exception as e:
        logger.warning(f"Could not format date '{date_str}': {e}")
        return date_str

def main():
    logger.info("Starting Goose Tour Date Scraper")
    logger.info("=" * 50)
    
    while True:
        try:
            # Scrape the tour dates
            tour_dates = scrape_goose_tour_dates()
            
            if not tour_dates:
                logger.warning("No tour dates found. The page structure may have changed.")
            else:
                # Sort dates chronologically using the first date for date ranges
                tour_dates.sort(key=lambda x: x['date'].split(" to ")[0])
                
                # Print tour dates in a readable format
                logger.info(f"\nFound {len(tour_dates)} tour dates:")
                logger.info("=" * 50)
                
                # Group events by month for better readability
                events_by_month = {}
                
                # First, group events by month
                for date in tour_dates:
                    try:
                        # Get the month from the date
                        date_obj = datetime.strptime(date['date'].split(" to ")[0], "%Y-%m-%d")
                        month = date_obj.strftime("%B %Y")
                        
                        if month not in events_by_month:
                            events_by_month[month] = []
                        events_by_month[month].append(date)
                        
                    except Exception as e:
                        logger.error(f"Error processing date: {e}")
                        continue
                
                # Then print events grouped by month
                for month in sorted(events_by_month.keys()):
                    logger.info(f"\n{month}")
                    logger.info("-" * len(month))
                    
                    # Sort events within each month by date
                    month_events = sorted(events_by_month[month], 
                                       key=lambda x: x['date'].split(" to ")[0])
                    
                    for date in month_events:
                        try:
                            # Print event details in a consistent order
                            logger.info(f"Date: {format_date_for_display(date['date'])}")
                            logger.info(f"Venue: {date['venue']}")
                            logger.info(f"Location: {date['location']}")
                            
                            # Only print ticket links if they exist
                            if date['ticketLinks']:
                                logger.info(f"Ticket Links: {date['ticketLinks']}")
                            
                            # Only print additional info if it exists
                            if date['additionalInfo']:
                                logger.info(f"Additional Info: {date['additionalInfo']}")
                            
                            # Add separator between events
                            logger.info("-" * 30)
                            
                        except Exception as e:
                            logger.error(f"Error formatting event: {e}")
                            continue
                
                # Add a final separator after all events
                logger.info("\n" + "=" * 50)
            
            # Wait for 24 hours before next check
            logger.info("\nWaiting 24 hours before next check...")
            time.sleep(24 * 60 * 60)  # 24 hours in seconds
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal, stopping...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            # Wait 5 minutes before retrying on error
            logger.info("Waiting 5 minutes before retry...")
            time.sleep(5 * 60)  # 5 minutes in seconds

if __name__ == "__main__":
    main()