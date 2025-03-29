from datetime import datetime
import logging
from scraper import scrape_goose_tour_dates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

def process_date(date_str):
    """Process a date string and return a standardized format."""
    try:
        # Check if it's a date range
        if " - " in date_str:
            start_date, end_date = date_str.split(" - ")
            # Process both dates
            start_obj = None
            end_obj = None
            
            # Try common formats for both dates
            for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"]:
                try:
                    start_obj = datetime.strptime(start_date.strip(), fmt)
                    end_obj = datetime.strptime(end_date.strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if start_obj and end_obj:
                return f"{start_obj.strftime('%Y-%m-%d')} to {end_obj.strftime('%Y-%m-%d')}"
        
        # Single date processing
        for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"]:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return date_str  # Return original if no format matches
    except Exception as e:
        logger.warning(f"Could not parse date '{date_str}': {e}")
        return date_str

def format_date_for_display(date_str):
    """Format date string for display in Month Day, YYYY format."""
    try:
        if " to " in date_str:
            start_date, end_date = date_str.split(" to ")
            start_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_obj = datetime.strptime(end_date, "%Y-%m-%d")
            return f"{start_obj.strftime('%B %d, %Y')} to {end_obj.strftime('%B %d, %Y')}"
        else:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%B %d, %Y")
    except Exception as e:
        logger.warning(f"Could not format date '{date_str}': {e}")
        return date_str

def format_event_output(event):
    """Format a single event's output as a single string."""
    output_lines = []
    
    # Format date with bold
    output_lines.append(f"**Date:** {format_date_for_display(event['date'])}")
    
    # Add venue and location with bold headers
    output_lines.append(f"**Venue:** {event['venue']}")
    output_lines.append(f"**Location:** {event['location']}")
    
    # Add ticket links if present
    if event['ticketLinks']:
        # Split ticket links into multiple lines if too long
        ticket_lines = []
        current_line = "**Ticket Links:** "
        for link in event['ticketLinks'].split("; "):
            if len(current_line + link) > 80:  # Reasonable line length
                ticket_lines.append(current_line)
                current_line = "  " + link
            else:
                current_line += "; " + link
        ticket_lines.append(current_line)
        output_lines.extend(ticket_lines)
    
    # Add additional info if present
    if event['additionalInfo']:
        # Split additional info into multiple lines if too long
        info_lines = []
        current_line = "**Additional Info:** "
        words = event['additionalInfo'].split()
        for word in words:
            if len(current_line + " " + word) > 80:  # Reasonable line length
                info_lines.append(current_line)
                current_line = "  " + word
            else:
                current_line += " " + word
        info_lines.append(current_line)
        output_lines.extend(info_lines)
    
    # Add separator with emoji
    output_lines.append("🎸" * 20)
    
    # Join with double newlines for better spacing
    return "\n\n".join(output_lines)

def get_formatted_tour_dates():
    """Get and format tour dates for Discord output."""
    tour_dates = scrape_goose_tour_dates()
    
    if not tour_dates:
        return ["No tour dates found. The page structure may have changed."]
    
    # Process dates to ensure consistent format
    processed_dates = []
    for event in tour_dates:
        event["date"] = process_date(event["date"])
        processed_dates.append(event)
    
    # Sort dates chronologically using the first date for date ranges
    processed_dates.sort(key=lambda x: x['date'].split(" to ")[0])
    
    # Group events by month for better readability
    events_by_month = {}
    
    # First, group events by month
    for date in processed_dates:
        try:
            # Get the month from the date
            date_obj = datetime.strptime(date['date'].split(" to ")[0], "%Y-%m-%d")
            month = date_obj.strftime("%B %Y")
            
            if month not in events_by_month:
                events_by_month[month] = []
            events_by_month[month].append(date)
            
        except Exception as e:
            logger.error(f"Error processing date: {e}")
            continue
    
    # Create separate messages for each month
    messages = []
    
    # Add header message with total count and emoji
    header_message = f"🎵 **Goose Tour Dates** 🎵\nFound {len(processed_dates)} upcoming shows:"
    messages.append(header_message)
    
    # Create a message for each month
    for month in sorted(events_by_month.keys()):
        # Start with month header using bold and emoji
        month_message = [
            f"\n📅 **{month}**",
            "🎸" * 20
        ]
        
        # Sort events within each month by date
        month_events = sorted(events_by_month[month], 
                           key=lambda x: x['date'].split(" to ")[0])
        
        # Format all events in this month
        for date in month_events:
            try:
                month_message.append(format_event_output(date))
            except Exception as e:
                logger.error(f"Error formatting event: {e}")
                continue
        
        # Join the month message
        messages.append("\n".join(month_message))
    
    return messages 