"""
Railway-specific configuration for the Goose Tour Dates bot.
Handles ephemeral filesystem and environment-specific settings.
"""

import os
from pathlib import Path

def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        'scraper/logs',
        'scraper/data',
        'scraper/data/scraped_concerts',
        'scraper/data/new_concerts'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def get_railway_config():
    """Get Railway-specific configuration."""
    return {
        'is_railway': bool(os.getenv('RAILWAY_ENVIRONMENT')),
        'port': int(os.getenv('PORT', 8080)),
        'host': '0.0.0.0'
    }

def setup_railway():
    """Setup Railway-specific configurations."""
    config = get_railway_config()
    
    if config['is_railway']:
        # Ensure all required directories exist
        ensure_directories()
        
        # Additional Railway-specific setup can be added here
        pass
    
    return config 