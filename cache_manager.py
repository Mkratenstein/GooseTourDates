import json
import os
import time
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_EXPIRY_HOURS = 24  # Cache expires after 24 hours
CACHE_FILE = os.path.join(os.getenv('RAILWAY_DATA_DIR', 'data'), 'tour_dates_cache.json')

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
    """Check if cache is still valid based on timestamp."""
    try:
        # Convert timestamp to datetime
        cache_time = datetime.fromtimestamp(timestamp)
        current_time = datetime.now()
        
        # Calculate age of cache
        cache_age = current_time - cache_time
        
        # Check if cache is older than expiry time
        if cache_age > timedelta(hours=CACHE_EXPIRY_HOURS):
            logger.info(f"Cache is {cache_age.total_seconds() / 3600:.1f} hours old and has expired")
            return False
            
        logger.info(f"Cache is {cache_age.total_seconds() / 3600:.1f} hours old and is still valid")
        return True
        
    except Exception as e:
        logger.error(f"Error checking cache validity: {e}")
        return False 