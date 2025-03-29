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
            
            # Then wait for the tour container with a longer timeout
            logger.info("Waiting for tour dates to load...")
            try:
                tour_container = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "seated-event-row"))
                )
            except Exception as e:
                logger.error(f"Timeout waiting for tour container: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
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