"""
Reporting module for the Goose Tour Scraper.
Handles console output, HTML reports, and logging.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import jinja2
from jinja2 import Environment, FileSystemLoader
from colorama import init, Fore, Style
import pandas as pd
from collections import Counter
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Initialize colorama
init()

class ScraperReporter:
    def __init__(self, data_dir: str = "data", log_dir: str = "logs"):
        """Initialize the reporter with data and log directories."""
        self.data_dir = Path(data_dir)
        self.log_dir = Path(log_dir)
        self.reports_dir = self.data_dir / "reports"
        self.templates_dir = Path(__file__).parent / "templates"
        
        # Create necessary directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging
        self.setup_logging()
        
        # Set up Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
        
        # Initialize geocoder
        self.geocoder = Nominatim(user_agent="goose_tour_scraper")
        
    def setup_logging(self):
        """Configure logging with rotation and formatting."""
        log_file = self.log_dir / "scraper.log"
        
        # Configure the root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        
    def log_scrape_start(self):
        """Log the start of a scraping session."""
        self.logger.info("Starting new scraping session")
        
    def log_scrape_end(self, shows_count: int):
        """Log the end of a scraping session."""
        self.logger.info(f"Scraping completed. Found {shows_count} shows")
        
    def log_new_concerts(self, new_concerts: List[Dict]):
        """Log newly found concerts."""
        for concert in new_concerts:
            self.logger.info(
                f"New concert found: {concert['venue']} on {concert['start_date']}"
            )
            
    def log_error(self, error: Exception, context: str = ""):
        """Log an error with context."""
        self.logger.error(f"Error in {context}: {str(error)}", exc_info=True)
        
    def generate_console_report(self, shows: List[Dict], new_concerts: List[Dict]):
        """Generate a detailed console report with color coding."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}=== Goose Tour Scraper Report ==={Style.RESET_ALL}\n")
        
        # Summary Statistics
        print(f"{Fore.GREEN}Summary Statistics:{Style.RESET_ALL}")
        print(f"Total concerts found: {len(shows)}")
        print(f"New concerts: {len(new_concerts)}")
        
        # Date Range
        if shows:
            dates = [datetime.fromisoformat(show['start_date']) for show in shows]
            date_range = f"{min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}"
            print(f"Date range: {date_range}")
            
        # Venue Distribution
        venues = Counter(show['venue'] for show in shows)
        print(f"\n{Fore.GREEN}Venue Distribution:{Style.RESET_ALL}")
        for venue, count in venues.most_common():
            print(f"- {venue}: {count} shows")
            
        # New Concerts
        if new_concerts:
            print(f"\n{Fore.YELLOW}New Concerts Found:{Style.RESET_ALL}")
            for concert in new_concerts:
                print(f"- {concert['venue']} on {concert['start_date']}")
                if concert['additional_info']:
                    print(f"  Additional Info: {', '.join(concert['additional_info'])}")
                    
        print(f"\n{Fore.CYAN}Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}\n")
        
    def _get_venue_location(self, venue: str, location: str) -> Optional[Dict]:
        """Get coordinates for a venue using geocoding."""
        try:
            # Combine venue and location for better geocoding results
            query = f"{venue}, {location}"
            location = self.geocoder.geocode(query)
            if location:
                return {
                    'venue': venue,
                    'lat': location.latitude,
                    'lng': location.longitude,
                    'shows': 1
                }
        except GeocoderTimedOut:
            self.logger.warning(f"Geocoding timed out for venue: {venue}")
        except Exception as e:
            self.logger.error(f"Error geocoding venue {venue}: {str(e)}")
        return None
        
    def _calculate_monthly_stats(self, shows: List[Dict]) -> Dict:
        """Calculate monthly concert statistics."""
        monthly_counts = Counter()
        for show in shows:
            date = datetime.fromisoformat(show['start_date'])
            month_key = date.strftime('%Y-%m')
            monthly_counts[month_key] += 1
            
        return {
            'labels': list(monthly_counts.keys()),
            'values': list(monthly_counts.values())
        }
        
    def _calculate_venue_locations(self, shows: List[Dict]) -> List[Dict]:
        """Calculate venue locations for the map."""
        venue_locations = {}
        for show in shows:
            venue = show['venue']
            if venue not in venue_locations:
                location = self._get_venue_location(venue, show['location'])
                if location:
                    venue_locations[venue] = location
            else:
                venue_locations[venue]['shows'] += 1
                
        return list(venue_locations.values())
        
    def generate_html_report(self, shows: List[Dict], new_concerts: List[Dict], timestamp: str):
        """Generate an HTML report with interactive features."""
        # Prepare data for the template
        report_data = {
            'timestamp': timestamp,
            'total_concerts': len(shows),
            'new_concerts': len(new_concerts),
            'shows': shows,
            'new_concerts_list': new_concerts,
            'venue_stats': self._calculate_venue_stats(shows),
            'date_range': self._calculate_date_range(shows),
            'monthly_stats': self._calculate_monthly_stats(shows),
            'venue_locations': self._calculate_venue_locations(shows)
        }
        
        # Load and render template
        template = self.env.get_template('report_template.html')
        html_content = template.render(**report_data)
        
        # Save the report
        report_path = self.reports_dir / f"report_{timestamp}.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        self.logger.info(f"HTML report generated: {report_path}")
        return report_path
        
    def _calculate_venue_stats(self, shows: List[Dict]) -> Dict:
        """Calculate statistics about venues."""
        venues = Counter(show['venue'] for show in shows)
        return {
            'total_venues': len(venues),
            'venue_counts': dict(venues.most_common()),
            'most_common_venue': venues.most_common(1)[0] if venues else None
        }
        
    def _calculate_date_range(self, shows: List[Dict]) -> Dict:
        """Calculate date range statistics."""
        if not shows:
            return {'start': None, 'end': None, 'days': 0}
            
        dates = [datetime.fromisoformat(show['start_date']) for show in shows]
        return {
            'start': min(dates).strftime('%Y-%m-%d'),
            'end': max(dates).strftime('%Y-%m-%d'),
            'days': (max(dates) - min(dates)).days + 1
        } 