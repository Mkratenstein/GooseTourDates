from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime
import os
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def scrape_goose_tour_dates():
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Navigate to tour page
            logger.info("Navigating to Goose tour page...")
            page.goto("https://www.goosetheband.com/tour")
            
            # Wait for the tour data to load
            page.wait_for_selector('.tour-dates-container')
            
            # Extract tour data using JavaScript in the page context
            logger.info("Extracting tour dates...")
            tour_dates = page.evaluate('''
                () => {
                    const dates = [];
                    // Select all event containers
                    document.querySelectorAll('.tour-dates-container .touring-event').forEach(el => {
                        // Check if it's not a past event (some sites gray out or mark past events)
                        if (!el.classList.contains('past-event')) {
                            // Extract date info
                            const dateElement = el.querySelector('.date-text');
                            const dateStr = dateElement ? dateElement.innerText.trim() : '';
                            
                            // Extract venue info
                            const venueElement = el.querySelector('.event-venue');
                            const venue = venueElement ? venueElement.innerText.trim() : '';
                            
                            // Extract location info
                            const locationElement = el.querySelector('.event-location');
                            const location = locationElement ? locationElement.innerText.trim() : '';
                            
                            // Extract ticket link
                            const ticketElement = el.querySelector('a.tickets-button');
                            const ticketLink = ticketElement ? ticketElement.href : '';
                            
                            // Extract any additional info (like festival name, support acts)
                            const infoElement = el.querySelector('.event-info');
                            const additionalInfo = infoElement ? infoElement.innerText.trim() : '';
                            
                            dates.push({
                                date: dateStr,
                                venue: venue,
                                location: location,
                                ticketLink: ticketLink,
                                additionalInfo: additionalInfo
                            });
                        }
                    });
                    return dates;
                }
            ''')
            
            # Process dates to ensure consistent format if needed
            processed_dates = []
            for event in tour_dates:
                # Try to parse and standardize the date format
                try:
                    date_str = event['date']
                    # Handle various date formats that might be used
                    date_obj = None
                    
                    # Try common formats
                    for fmt in ['%b %d, %Y', '%B %d, %Y', '%m/%d/%Y']:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if date_obj:
                        # Use a standard date format for the output
                        event['date'] = date_obj.strftime('%Y-%m-%d')
                    
                except Exception as e:
                    logger.warning(f"Could not parse date '{event['date']}': {e}")
                
                processed_dates.append(event)
            
            return processed_dates
            
        except Exception as e:
            logger.error(f"Error scraping tour dates: {e}")
            return None
        finally:
            browser.close()

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
                # Create a DataFrame
                df = pd.DataFrame(tour_dates)
                
                # Generate timestamp for the filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Use Railway's data directory if available, otherwise use current directory
                data_dir = os.getenv('RAILWAY_DATA_DIR', '.')
                csv_filename = os.path.join(data_dir, f'goose_tour_dates_{timestamp}.csv')
                
                # Export to CSV
                df.to_csv(csv_filename, index=False)
                logger.info(f"Exported {len(tour_dates)} tour dates to {csv_filename}")
            
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