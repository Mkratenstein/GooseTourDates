import os
import json
import logging
from datetime import datetime
import pytz
from data_processor import format_event_output, get_tour_dates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# File paths
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
    """Save the current list of events for future comparison."""
    try:
        os.makedirs(os.path.dirname(PREVIOUS_EVENTS_FILE), exist_ok=True)
        with open(PREVIOUS_EVENTS_FILE, 'w') as f:
            json.dump(events, f)
    except Exception as e:
        logger.error(f"Error saving previous events: {e}")

def check_for_new_events():
    """Check for new events by comparing current events with previously seen events."""
    try:
        # Get current events
        current_events = get_tour_dates()
        if not current_events:
            logger.error("Failed to get current events")
            return []

        # Get previous events
        previous_events = load_previous_events()
        
        # Create unique identifiers for current events
        current_event_ids = {
            f"{event['date']}_{event['venue']}_{event['location']}"
            for event in current_events
        }
        
        # Create unique identifiers for previous events
        previous_event_ids = {
            f"{event['date']}_{event['venue']}_{event['location']}"
            for event in previous_events
        }
        
        # Find new events
        new_event_ids = current_event_ids - previous_event_ids
        new_events = [
            event for event in current_events
            if f"{event['date']}_{event['venue']}_{event['location']}" in new_event_ids
        ]
        
        # Save current events as previous events for next check
        save_previous_events(current_events)
        
        return new_events
    except Exception as e:
        logger.error(f"Error checking for new events: {e}")
        return []

def format_new_event_announcement(event):
    """Format the announcement message for a new event."""
    try:
        announcement = "**Goose the Organization has announced a new show!**\n\n"
        announcement += format_event_output(event)
        return announcement
    except Exception as e:
        logger.error(f"Error formatting announcement: {e}")
        return None

async def announce_new_events(bot):
    """Check for and announce any new events."""
    try:
        # Get the announcements channel ID from environment variables
        channel_id = int(os.getenv('ANNOUNCEMENTS_CHANNEL_ID', '859536104570486805'))
        
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
                if announcement:
                    await channel.send(announcement)
                    logger.info(f"Announced new event: {event['date']} at {event['venue']}")
            except Exception as e:
                logger.error(f"Error announcing event: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error in announce_new_events: {e}") 