import json
import os
import time
import logging
from datetime import datetime, timedelta
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_EXPIRY_BUSINESS_HOURS = 1  # Cache expires after 1 hour during business hours
CACHE_EXPIRY_OFF_HOURS = 4      # Cache expires after 4 hours during off hours
CACHE_FILE = os.path.join(os.getenv('RAILWAY_DATA_DIR', 'data'), 'tour_dates_cache.json')

def is_business_hours():
    """Check if current time is within business hours (10 AM - 5 PM ET)."""
    try:
        # Get current time in ET
        et_timezone = pytz.timezone('America/New_York')
        current_time = datetime.now(et_timezone)
        
        # Check if it's a weekday and within business hours
        is_weekday = current_time.weekday() < 5  # Monday = 0, Sunday = 6
        is_business_hours = 10 <= current_time.hour < 17  # 10 AM to 5 PM
        
        return is_weekday and is_business_hours
    except Exception as e:
        logger.error(f"Error checking business hours: {e}")
        return False  # Default to off-hours if there's an error

def get_cache_expiry_hours():
    """Get the appropriate cache expiry time based on current time."""
    return CACHE_EXPIRY_BUSINESS_HOURS if is_business_hours() else CACHE_EXPIRY_OFF_HOURS

def save_to_cache(tour_dates):
    """Save tour dates to cache file with timestamp."""
    try:
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        # Prepare cache data with timestamp
        cache_data = {
            'timestamp': time.time(),
            'tour_dates': tour_dates
        }
        
        # Write to file
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
            
        logger.info(f"Successfully saved tour dates to cache at {CACHE_FILE}")
        
    except Exception as e:
        logger.error(f"Error saving to cache: {e}")

def load_from_cache():
    """Load tour dates from cache if valid."""
    try:
        # Check if cache file exists
        if not os.path.exists(CACHE_FILE):
            logger.info("No cache file found")
            return None
            
        # Read cache file
        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
            
        # Check if cache is expired
        if is_cache_valid(cache_data['timestamp']):
            logger.info("Using cached tour dates")
            return cache_data['tour_dates']
        else:
            logger.info("Cache expired")
            return None
            
    except Exception as e:
        logger.error(f"Error loading from cache: {e}")
        return None

def is_cache_valid(timestamp):
    """Check if cache is still valid based on timestamp and current time."""
    try:
        # Convert timestamp to datetime
        cache_time = datetime.fromtimestamp(timestamp)
        current_time = datetime.now()
        
        # Calculate age of cache
        cache_age = current_time - cache_time
        
        # Get appropriate expiry time
        expiry_hours = get_cache_expiry_hours()
        
        # Check if cache is older than expiry time
        if cache_age > timedelta(hours=expiry_hours):
            logger.info(f"Cache is {cache_age.total_seconds() / 3600:.1f} hours old and has expired")
            return False
            
        logger.info(f"Cache is {cache_age.total_seconds() / 3600:.1f} hours old and is still valid")
        return True
        
    except Exception as e:
        logger.error(f"Error checking cache validity: {e}")
        return False 