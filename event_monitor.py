import os
import json
import logging
from datetime import datetime, timedelta
import pytz
from data_processor import format_event_output, get_tour_dates, process_date
import discord
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# File paths
PREVIOUS_EVENTS_FILE = os.path.join(os.getenv('RAILWAY_DATA_DIR', 'data'), 'previous_events.json')

# Constants
MAX_MESSAGE_HISTORY = 100  # Maximum number of messages to check in history
ANNOUNCEMENT_PREFIX = "**Goose the Organization has announced a new show!**"

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

def process_events(events):
    """Process all events to ensure consistent date formatting."""
    processed_events = []
    for event in events:
        try:
            # Create a copy of the event to avoid modifying the original
            processed_event = event.copy()
            # Process the date
            processed_event['date'] = process_date(event['date'])
            processed_events.append(processed_event)
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            continue
    return processed_events

async def get_announced_events_from_discord(bot, channel_id):
    """Get a list of events that have already been announced by checking Discord message history."""
    try:
        # Get the channel
        channel = bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Could not find announcements channel with ID {channel_id}")
            return []
        
        # Get message history
        announced_events = []
        try:
            async for message in channel.history(limit=MAX_MESSAGE_HISTORY):
                # Check if this is an announcement message
                if message.content.startswith(ANNOUNCEMENT_PREFIX):
                    # Extract event details from the message
                    content = message.content
                    lines = content.split('\n')
                    
                    # Skip the announcement header
                    if len(lines) < 2:
                        continue
                    
                    # Extract date (format: **Month Day, Year**)
                    date_line = lines[1]
                    if not date_line.startswith('**') or not date_line.endswith('**'):
                        continue
                    
                    date_str = date_line.strip('*')
                    
                    # Extract venue and location (format: Venue | Location)
                    if len(lines) < 3:
                        continue
                    
                    venue_location = lines[2].split(' | ')
                    if len(venue_location) != 2:
                        continue
                    
                    venue = venue_location[0]
                    location = venue_location[1]
                    
                    # Create event object
                    event = {
                        'date': date_str,
                        'venue': venue,
                        'location': location,
                        'announced_at': message.created_at.isoformat()
                    }
                    
                    announced_events.append(event)
        except discord.Forbidden:
            logger.error(f"Bot lacks permission to read message history in channel {channel_id}")
        except Exception as e:
            logger.error(f"Error reading message history: {e}")
        
        logger.info(f"Found {len(announced_events)} previously announced events in Discord history")
        return announced_events
    except Exception as e:
        logger.error(f"Error getting announced events from Discord: {e}")
        return []

def check_for_new_events():
    """Check for new events by comparing current events with previously seen events."""
    try:
        # Get current events
        current_events = get_tour_dates()
        if not current_events:
            logger.error("Failed to get current events")
            return []

        # Process current events to ensure consistent date formatting
        current_events = process_events(current_events)

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
        
        # Find new events (events that weren't in previous events)
        new_event_ids = current_event_ids - previous_event_ids
        
        # Get the actual events to announce
        events_to_announce = [
            event for event in current_events
            if f"{event['date']}_{event['venue']}_{event['location']}" in new_event_ids
        ]
        
        # Add timestamp to each event to be announced
        current_time = datetime.now().isoformat()
        for event in events_to_announce:
            event['announced_at'] = current_time
        
        # Save current events as previous events for next check
        save_previous_events(current_events)
        
        return events_to_announce
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
        
        # Get previously announced events from Discord
        announced_events = await get_announced_events_from_discord(bot, channel_id)
        
        # Get current events
        current_events = get_tour_dates()
        if not current_events:
            logger.error("Failed to get current events")
            return
        
        # Process current events
        current_events = process_events(current_events)
        
        # Create unique identifiers for current events
        current_event_ids = {
            f"{event['date']}_{event['venue']}_{event['location']}"
            for event in current_events
        }
        
        # Create unique identifiers for announced events
        announced_event_ids = {
            f"{event['date']}_{event['venue']}_{event['location']}"
            for event in announced_events
        }
        
        # Find events that haven't been announced yet
        unannounced_event_ids = current_event_ids - announced_event_ids
        
        # Get the actual events to announce
        events_to_announce = [
            event for event in current_events
            if f"{event['date']}_{event['venue']}_{event['location']}" in unannounced_event_ids
        ]
        
        # Announce each new event with retry logic
        for event in events_to_announce:
            max_retries = 3
            retry_delay = 2
            
            for attempt in range(max_retries):
                try:
                    announcement = format_new_event_announcement(event)
                    if announcement:
                        await channel.send(announcement)
                        logger.info(f"Announced new event: {event['date']} at {event['venue']}")
                        break  # Success, exit retry loop
                except discord.Forbidden:
                    logger.error(f"Bot lacks permission to send messages in channel {channel_id}")
                    # Don't retry on permission errors
                    break
                except discord.HTTPException as e:
                    if e.code == 429:  # Rate limit
                        retry_after = e.retry_after
                        logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        logger.error(f"HTTP error announcing event: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        break
                except Exception as e:
                    logger.error(f"Error announcing event: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    break
                
    except Exception as e:
        logger.error(f"Error in announce_new_events: {e}") 