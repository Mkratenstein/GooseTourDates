import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
import time
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_tour_dates():
    url = "https://www.goosetheband.com/tour"
    try:
        logger.info("Fetching tour dates from website...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://www.goosetheband.com/'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info(f"Response status code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Successfully parsed HTML")
        
        # Find all seated event rows
        seated_rows = soup.find_all('div', class_='seated-event-row')
        logger.info(f"Found {len(seated_rows)} seated event rows")
        
        tour_dates = []
        for row in seated_rows:
            try:
                # Extract date
                date_elem = row.find('div', class_='seated-event-date')
                date_text = date_elem.text.strip() if date_elem else "Date TBA"
                
                # Extract venue
                venue_elem = row.find('div', class_='seated-event-venue')
                venue_text = venue_elem.text.strip() if venue_elem else "Venue TBA"
                
                # Extract location
                location_elem = row.find('div', class_='seated-event-location')
                location_text = location_elem.text.strip() if location_elem else "Location TBA"
                
                # Clean up the text
                date_text = ' '.join(date_text.split())
                venue_text = ' '.join(venue_text.split())
                location_text = ' '.join(location_text.split())
                
                # Log each event as it's found
                logger.info(f"Event Found: Date: {date_text}, Venue: {venue_text}, Location: {location_text}")
                
                tour_dates.append({
                    'date': date_text,
                    'venue': venue_text,
                    'location': location_text
                })
                
            except Exception as e:
                logger.error(f"Error processing seated event row: {e}")
                continue
        
        if not tour_dates:
            logger.warning("No tour dates found in seated event rows")
            logger.debug("Full HTML content: %s", soup.prettify())
            return None
            
        logger.info(f"Successfully found {len(tour_dates)} tour dates")
        
        # Save to JSON file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'tour_dates_{timestamp}.json'
        
        # Use Railway's data directory if available, otherwise use current directory
        data_dir = os.getenv('RAILWAY_DATA_DIR', '.')
        filepath = os.path.join(data_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(tour_dates, f, indent=4)
        logger.info(f"Tour dates saved to {filepath}")
        
        return tour_dates
        
    except requests.RequestException as e:
        logger.error(f"Error fetching tour dates: {e}")
        logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_tour_dates: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def main():
    logger.info("Starting Goose Tour Date Scraper")
    logger.info("=" * 50)
    
    while True:
        try:
            tour_dates = get_tour_dates()
            if tour_dates:
                logger.info("Successfully retrieved tour dates")
            else:
                logger.warning("Failed to retrieve tour dates")
            
            # Wait for 24 hours before next check
            logger.info("Waiting 24 hours before next check...")
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
