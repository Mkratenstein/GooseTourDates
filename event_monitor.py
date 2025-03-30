import os
import json
import logging
from datetime import datetime
import discord
from data_processor import format_event_output

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# File paths
CACHE_FILE = os.path.join(os.getenv('RAILWAY_DATA_DIR', 'data'), 'tour_dates_cache.json')
PREVIOUS_EVENTS_FILE = os.path.join(os.getenv('RAILWAY_DATA_DIR', 'data'), 'previous_events.json')

def load_previous_events():
    """Load the list of previously seen events."""
    try:
        if os.path.exists(PREVIOUS_EVENTS_FILE):
            with open(PREVIOUS_EVENTS_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error loading previous events: {e}")
        return []

def save_previous_events(events):
    """Save the list of previously seen events."""
    try:
        os.makedirs(os.path.dirname(PREVIOUS_EVENTS_FILE), exist_ok=True)
        with open(PREVIOUS_EVENTS_FILE, 'w') as f:
            json.dump(events, f)
    except Exception as e:
        logger.error(f"Error saving previous events: {e}")

def get_event_identifier(event):
    """Create a unique identifier for an event."""
    return f"{event['date']}_{event['venue']}_{event['location']}"

def check_for_new_events():
    """Check for new events and return a list of new events."""
    try:
        # Load current events from cache
        if not os.path.exists(CACHE_FILE):
            logger.warning("Cache file not found")
            return []

        with open(CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
            current_events = cache_data.get('tour_dates', [])

        # Load previous events
        previous_events = load_previous_events()
        
        # Find new events
        new_events = []
        for event in current_events:
            event_id = get_event_identifier(event)
            if event_id not in previous_events:
                new_events.append(event)
                previous_events.append(event_id)
        
        # Save updated previous events
        save_previous_events(previous_events)
        
        return new_events
    except Exception as e:
        logger.error(f"Error checking for new events: {e}")
        return []

def format_new_event_announcement(event):
    """Format a new event announcement message."""
    # Get the standard event formatting
    event_text = format_event_output(event)
    
    # Add the announcement header
    announcement = "**Goose the Organization has announced a new show!**\n\n"
    announcement += event_text
    
    return announcement

async def announce_new_events(bot):
    """Check for and announce new events in Discord."""
    try:
        # Get the announcements channel ID from environment variables
        channel_id = int(os.getenv('ANNOUNCEMENTS_CHANNEL_ID', '859536104570486805'))
        if not channel_id:
            logger.error("No announcements channel ID found in environment variables")
            return

        # Get the channel
        channel = bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Could not find announcements channel with ID {channel_id}")
            return

        # Check for new events
        new_events = check_for_new_events()
        
        # Announce each new event
        for event in new_events:
            try:
                announcement = format_new_event_announcement(event)
                await channel.send(announcement)
                logger.info(f"Announced new event: {event['date']} at {event['venue']}")
            except Exception as e:
                logger.error(f"Error announcing event: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in announce_new_events: {e}") 