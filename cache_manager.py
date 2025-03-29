import os
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Cache file path
CACHE_FILE = os.path.join(os.getenv('RAILWAY_DATA_DIR', 'data'), 'tour_dates_cache.json')
CACHE_EXPIRY_DAYS = 1

def save_to_cache(tour_dates):
    """Save tour dates to cache file."""
    try:
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        # Create cache data with timestamp
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'tour_dates': tour_dates
        }
        
        # Save to file
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
        logger.info("Successfully saved tour dates to cache")
        return True
    except Exception as e:
        logger.error(f"Error saving to cache: {e}")
        return False

def load_from_cache():
    """Load tour dates from cache file if it exists and is not expired."""
    try:
        # Check if cache file exists
        if not os.path.exists(CACHE_FILE):
            logger.info("No cache file found")
            return None
            
        # Load cache data
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            
        # Check if cache is expired
        cache_timestamp = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - cache_timestamp > timedelta(days=CACHE_EXPIRY_DAYS):
            logger.info("Cache is expired")
            return None
            
        logger.info("Successfully loaded tour dates from cache")
        return cache_data['tour_dates']
    except Exception as e:
        logger.error(f"Error loading from cache: {e}")
        return None

def is_cache_valid():
    """Check if cache exists and is not expired."""
    try:
        if not os.path.exists(CACHE_FILE):
            return False
            
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            
        cache_timestamp = datetime.fromisoformat(cache_data['timestamp'])
        return datetime.now() - cache_timestamp <= timedelta(days=CACHE_EXPIRY_DAYS)
    except Exception as e:
        logger.error(f"Error checking cache validity: {e}")
        return False 