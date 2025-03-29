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
            'Referer': 'https://www.goosetheband.com/',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
            'sec-ch-ua-mobile': '?0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        logger.info(f"Response status code: {response.status_code}")
        
        # Log the first part of the response for debugging
        logger.debug(f"Response content preview: {response.text[:500]}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Successfully parsed HTML")
        
        # Look for the Seated widget container
        seated_widget = soup.find('div', id='seated-55fdf2c0')
        if seated_widget:
            logger.info("Found Seated widget container")
            artist_id = seated_widget.get('data-artist-id')
            logger.info(f"Artist ID: {artist_id}")
            
            # Try to fetch from Seated API directly
            seated_url = f"https://widget.seated.com/api/v1/artists/{artist_id}/events"
            seated_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://www.goosetheband.com',
                'Referer': 'https://www.goosetheband.com/tour',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            try:
                logger.info(f"Fetching Seated API from: {seated_url}")
                seated_response = requests.get(seated_url, headers=seated_headers)
                seated_response.raise_for_status()
                logger.info(f"Seated API response status: {seated_response.status_code}")
                logger.info(f"Seated API response headers: {dict(seated_response.headers)}")
                logger.info(f"Seated API response content: {seated_response.text[:1000]}")  # Log first 1000 chars
                
                # Try to parse the response as JSON
                try:
                    seated_data = seated_response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Seated API response as JSON: {e}")
                    logger.error(f"Raw response content: {seated_response.text}")
                    seated_data = None
                
                if seated_data:
                    tour_dates = []
                    
                    for event in seated_data.get('events', []):
                        try:
                            # Parse the date from the event data
                            date_text = event.get('date', '')
                            if not date_text:
                                start_time = event.get('start_time')
                                if start_time:
                                    try:
                                        date = datetime.fromtimestamp(start_time)
                                        date_text = date.strftime('%B %d, %Y')
                                    except:
                                        date_text = "Date TBA"
                            
                            venue_text = event.get('venue', {}).get('name', 'Venue TBA')
                            city = event.get('venue', {}).get('city', '')
                            state = event.get('venue', {}).get('state', '')
                            location_text = f"{city}, {state}" if city and state else "Location TBA"
                            
                            if date_text and venue_text and location_text:
                                logger.info(f"Found tour date from Seated: {date_text} at {venue_text} in {location_text}")
                                tour_dates.append({
                                    'date': date_text,
                                    'venue': venue_text,
                                    'location': location_text
                                })
                        except Exception as e:
                            logger.error(f"Error processing Seated event: {e}")
                            continue
                    
                    if tour_dates:
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
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching Seated data: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Seated response status: {e.response.status_code}")
                    logger.error(f"Seated response headers: {e.response.headers}")
                    logger.error(f"Seated response content: {e.response.text}")
            except Exception as e:
                logger.error(f"Unexpected error with Seated API: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # If we couldn't get data from the Seated API, try parsing the HTML directly
        logger.info("Attempting to parse HTML directly...")
        
        # Find all potential event containers
        event_containers = soup.find_all(['div', 'section'], class_=['seated-event-row', 'tour-date', 'event'])
        logger.info(f"Found {len(event_containers)} potential event containers")
        
        # Log all div classes for debugging
        all_divs = soup.find_all('div', class_=True)
        logger.info("All div classes found:")
        for div in all_divs:
            logger.info(f"Div class: {div.get('class')}")
        
        tour_dates = []
        for container in event_containers:
            try:
                # Try to find date, venue, and location in various ways
                date_elem = (
                    container.find(['div', 'span'], class_=['seated-event-date', 'date', 'event-date']) or
                    container.find('time')
                )
                date_text = date_elem.text.strip() if date_elem else "Date TBA"
                
                venue_elem = container.find(['div', 'span'], class_=['seated-event-venue', 'venue', 'event-venue'])
                venue_text = venue_elem.text.strip() if venue_elem else "Venue TBA"
                
                location_elem = container.find(['div', 'span'], class_=['seated-event-location', 'location', 'event-location'])
                location_text = location_elem.text.strip() if location_elem else "Location TBA"
                
                # Clean up the text
                date_text = ' '.join(date_text.split())
                venue_text = ' '.join(venue_text.split())
                location_text = ' '.join(location_text.split())
                
                # Skip if this looks like a header or marquee
                if any(term in date_text.lower() for term in ['on tour', 'goose', 'tour dates']):
                    continue
                
                logger.info(f"Found tour date: {date_text} at {venue_text} in {location_text}")
                
                tour_dates.append({
                    'date': date_text,
                    'venue': venue_text,
                    'location': location_text
                })
                
            except Exception as e:
                logger.error(f"Error processing event container: {e}")
                continue
        
        if not tour_dates:
            logger.warning("No tour dates found in HTML")
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
