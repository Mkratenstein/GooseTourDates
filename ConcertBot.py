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
        
        # Create a session to maintain cookies
        session = requests.Session()
        
        # First visit the main page to get any necessary cookies
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
        
        response = session.get(url, headers=headers)
        response.raise_for_status()
        logger.info(f"Response status code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Successfully parsed HTML")
        
        # First try to find the Seated widget
        seated_widget = soup.find('div', {'data-artist-id': True})
        if seated_widget:
            artist_id = seated_widget.get('data-artist-id')
            logger.info(f"Found Seated widget with artist ID: {artist_id}")
            
            # Try to fetch from Seated widget's API
            seated_url = f"https://widget.seated.com/api/v1/artists/{artist_id}/events"
            seated_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://www.goosetheband.com',
                'Referer': 'https://www.goosetheband.com/tour',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Authorization': 'Bearer null',  # The widget uses this
                'X-Seated-Widget-Version': '3',  # From the widget's data-css-version
                'X-Seated-Environment': 'development'  # From the widget's data-dev-env
            }
            
            try:
                logger.info(f"Fetching Seated API from: {seated_url}")
                seated_response = session.get(seated_url, headers=seated_headers)
                seated_response.raise_for_status()
                
                # Log response details for debugging
                logger.info(f"Seated API response status: {seated_response.status_code}")
                logger.info(f"Seated API response headers: {dict(seated_response.headers)}")
                logger.info(f"Seated API response content: {seated_response.text[:1000]}")  # Log first 1000 chars
                
                # Try to parse the response as JSON
                try:
                    seated_data = seated_response.json()
                    
                    if isinstance(seated_data, list):
                        tour_dates = []
                        for event in seated_data:
                            try:
                                # Extract date
                                date_text = event.get('date', '')
                                if not date_text and event.get('start_time'):
                                    date = datetime.fromtimestamp(int(event['start_time']))
                                    date_text = date.strftime('%B %d, %Y')
                                
                                # Extract venue and location
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
                            return tour_dates
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Seated API response as JSON: {e}")
                    logger.error(f"Raw response content: {seated_response.text}")
                    
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
        
        # If Seated API fails, try parsing the HTML directly
        logger.info("Attempting to parse HTML directly...")
        
        # Look for any div that might contain tour dates
        tour_dates = []
        
        # First, try to find the main content area
        main_content = soup.find('div', class_='Content-inner')
        if not main_content:
            main_content = soup.find('div', class_='Main-content')
        
        if main_content:
            logger.info("Found main content area")
            
            # Look for any divs that might contain tour dates
            potential_containers = main_content.find_all(['div', 'section'], recursive=True)
            logger.info(f"Found {len(potential_containers)} potential containers")
            
            # Log all div classes for debugging
            all_divs = main_content.find_all('div', class_=True)
            logger.info("All div classes found in main content:")
            for div in all_divs:
                logger.info(f"Div class: {div.get('class')}")
            
            for container in potential_containers:
                try:
                    # Skip containers that are likely not tour dates
                    if any(term in str(container).lower() for term in ['header', 'footer', 'nav', 'menu', 'social']):
                        continue
                    
                    # Look for text that might be a date
                    text = container.get_text()
                    if not text:
                        continue
                    
                    # Check if the text contains a year (2024 or 2025)
                    if not any(year in text for year in ['2024', '2025']):
                        continue
                    
                    # Try to extract date, venue, and location
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    for i, line in enumerate(lines):
                        # Look for a line that contains a date
                        if any(year in line for year in ['2024', '2025']):
                            date_text = line
                            venue_text = "Venue TBA"
                            location_text = "Location TBA"
                            
                            # Look for venue and location in nearby lines
                            for j in range(max(0, i-2), min(len(lines), i+3)):
                                if j != i:  # Skip the date line
                                    if not any(year in lines[j] for year in ['2024', '2025']):
                                        if venue_text == "Venue TBA":
                                            venue_text = lines[j]
                                        elif location_text == "Location TBA":
                                            location_text = lines[j]
                            
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
                            break
                            
                except Exception as e:
                    logger.error(f"Error processing container: {e}")
                    continue
        
        if not tour_dates:
            logger.warning("No tour dates found in HTML")
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
