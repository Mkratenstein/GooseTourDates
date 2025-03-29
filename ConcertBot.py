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
        
        for event in event_elements:
            try:
                # Skip past events
                if "past-event" in event.get_attribute("class"):
                    continue
                
                # Extract date info
                date_element = event.find_element(By.CSS_SELECTOR, ".seated-event-date-cell")
                date_str = date_element.text.strip() if date_element else ""
                
                # Extract venue info
                venue_element = event.find_element(By.CSS_SELECTOR, ".seated-event-venue-name")
                venue = venue_element.text.strip() if venue_element else ""
                
                # Extract location info
                location_element = event.find_element(By.CSS_SELECTOR, ".seated-event-venue-location")
                location = location_element.text.strip() if location_element else ""
                
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
                    "additionalInfo": ""  # No additional info in new structure
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
            try:
                date_str = event["date"]
                # Handle various date formats
                date_obj = None
                
                # Try common formats
                for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"]:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if date_obj:
                    # Use a standard date format for the output
                    event["date"] = date_obj.strftime("%Y-%m-%d")
                
            except Exception as e:
                logger.warning(f"Could not parse date '{event['date']}': {e}")
            
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
                # Print tour dates in a readable format
                logger.info(f"\nFound {len(tour_dates)} tour dates:")
                logger.info("=" * 50)
                for date in tour_dates:
                    logger.info(f"\nDate: {date['date']}")
                    logger.info(f"Venue: {date['venue']}")
                    logger.info(f"Location: {date['location']}")
                    logger.info(f"Ticket Links: {date['ticketLinks']}")
                    if date['additionalInfo']:
                        logger.info(f"Additional Info: {date['additionalInfo']}")
                    logger.info("-" * 30)
            
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