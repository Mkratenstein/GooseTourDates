from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

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
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use environment variables for Chrome and ChromeDriver paths
        chrome_bin = os.getenv('CHROME_BIN', '/usr/bin/google-chrome')
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
        
        chrome_options.binary_location = chrome_bin
        service = Service(chromedriver_path)
        
        # Create driver with service and options
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set window size
        driver.set_window_size(1920, 1080)
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        return driver
    except Exception as e:
        logger.error(f"Error setting up Chrome driver: {e}")
        raise

def scrape_goose_tour_dates():
    """Scrape tour dates from Goose's website."""
    driver = None
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Set up the driver
            logger.info(f"Setting up Chrome driver (attempt {attempt + 1}/{max_retries})...")
            driver = setup_driver()
            
            # Navigate to tour page
            logger.info("Navigating to Goose tour page...")
            driver.get("https://www.goosetheband.com/tour")
            
            # Wait for the page to load completely
            logger.info("Waiting for page to load...")
            wait = WebDriverWait(driver, 30)
            
            # First wait for the body to be present
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Try different selectors for the tour container
            selectors = [
                ".seated-event-row",
                ".tour-date-row",
                ".event-row",
                "[class*='event']",
                "[class*='tour']"
            ]
            
            tour_container = None
            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    tour_container = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if tour_container:
                        logger.info(f"Found tour container with selector: {selector}")
                        break
                except Exception as e:
                    logger.warning(f"Selector {selector} not found: {e}")
                    continue
            
            if not tour_container:
                logger.error("Could not find tour container with any selector")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
            
            # Add a longer delay to ensure dynamic content is loaded
            time.sleep(10)
            
            # Extract tour data
            logger.info("Extracting tour dates...")
            tour_dates = []
            
            # Try different selectors for event elements
            event_selectors = [
                ".seated-event-row",
                ".tour-date-row",
                ".event-row",
                "[class*='event']",
                "[class*='tour']"
            ]
            
            event_elements = []
            for selector in event_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        event_elements = elements
                        logger.info(f"Found {len(elements)} event elements with selector: {selector}")
                        break
                except Exception as e:
                    logger.warning(f"Selector {selector} not found: {e}")
                    continue
            
            if not event_elements:
                logger.error("Could not find any event elements")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
            
            # Track processed dates to prevent duplicates
            processed_dates = set()
            
            for event in event_elements:
                try:
                    # Skip past events
                    if "past-event" in event.get_attribute("class"):
                        continue
                    
                    # Try different selectors for date, venue, and location
                    date_selectors = [".seated-event-date-cell", ".date-cell", "[class*='date']"]
                    venue_selectors = [".seated-event-venue-name", ".venue-name", "[class*='venue']"]
                    location_selectors = [".seated-event-venue-location", ".venue-location", "[class*='location']"]
                    
                    # Find elements using multiple selectors
                    date_element = None
                    venue_element = None
                    location_element = None
                    
                    for selector in date_selectors:
                        try:
                            date_element = event.find_element(By.CSS_SELECTOR, selector)
                            if date_element:
                                break
                        except:
                            continue
                    
                    for selector in venue_selectors:
                        try:
                            venue_element = event.find_element(By.CSS_SELECTOR, selector)
                            if venue_element:
                                break
                        except:
                            continue
                    
                    for selector in location_selectors:
                        try:
                            location_element = event.find_element(By.CSS_SELECTOR, selector)
                            if location_element:
                                break
                        except:
                            continue
                    
                    # Get the text values
                    date_str = date_element.text.strip() if date_element else ""
                    venue = venue_element.text.strip() if venue_element else ""
                    location = location_element.text.strip() if location_element else ""
                    
                    # Skip if we're missing essential information
                    if not all([date_str, venue, location]):
                        logger.warning(f"Skipping event due to missing information: date={date_str}, venue={venue}, location={location}")
                        continue
                    
                    # Create a unique identifier for the event
                    event_id = f"{date_str}_{venue}_{location}"
                    
                    # Skip if we've already processed this event
                    if event_id in processed_dates:
                        continue
                    
                    processed_dates.add(event_id)
                    
                    # Extract details info if present
                    details = ""
                    for selector in [".seated-event-details-cell", ".details-cell", "[class*='details']"]:
                        try:
                            details_element = event.find_element(By.CSS_SELECTOR, selector)
                            details = details_element.text.strip()
                            if details:
                                break
                        except:
                            continue
                    
                    # Extract ticket links
                    ticket_links = []
                    for selector in [".seated-event-link", ".ticket-link", "[class*='ticket']"]:
                        try:
                            ticket_elements = event.find_elements(By.CSS_SELECTOR, selector)
                            for ticket_element in ticket_elements:
                                ticket_link = ticket_element.get_attribute("href")
                                ticket_text = ticket_element.text.strip()
                                if ticket_link and ticket_text:
                                    ticket_links.append(f"{ticket_text}: {ticket_link}")
                            if ticket_links:
                                break
                        except:
                            continue
                    
                    # Join ticket links with semicolons
                    ticket_links_str = "; ".join(ticket_links)
                    
                    tour_dates.append({
                        "date": date_str,
                        "venue": venue,
                        "location": location,
                        "ticketLinks": ticket_links_str,
                        "additionalInfo": details if details else ""
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing event: {e}")
                    continue
            
            if not tour_dates:
                logger.warning("No tour dates found in the page")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
            
            return tour_dates
            
        except Exception as e:
            logger.error(f"Error scraping tour dates (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.error(f"Error closing browser: {e}")
    
    return None 