from datetime import datetime
import logging
from scraper import scrape_goose_tour_dates
from cache_manager import load_from_cache, save_to_cache, is_cache_valid

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
        # Convert to title case for consistent formatting
        date_str = date_str.title()
        
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
    output_lines.append(f"**{format_date_for_display(event['date'])}**")
    
    # Add venue and location on the same line
    output_lines.append(f"{event['venue']} | {event['location']}")
    
    # Add additional info if present
    if event['additionalInfo']:
        # Format additional info more compactly
        info_lines = []
        current_line = ""
        words = event['additionalInfo'].split()
        for word in words:
            if len(current_line + " " + word) > 80:  # Reasonable line length
                info_lines.append(current_line)
                current_line = "  " + word
            else:
                current_line += " " + word
        info_lines.append(current_line)
        # Format each line in italics
        output_lines.extend([f"*{line.strip()}*" for line in info_lines])
    
    # Add ticket links if present
    if event['ticketLinks']:
        # Format ticket links more compactly
        ticket_lines = []
        current_line = "🎫 "
        
        # Split ticket links and clean them up
        links = [link.strip() for link in event['ticketLinks'].split(";") if link.strip()]
        
        # Filter out VIP and Package tickets
        standard_links = []
        for link in links:
            # Skip VIP and Package tickets
            if any(keyword in link.lower() for keyword in ["vip", "package"]):
                continue
            standard_links.append(link)
        
        if standard_links:
            # Add the first standard ticket link
            current_line += standard_links[0]
            ticket_lines.append(current_line)
            
            # Add any additional standard ticket links on new lines
            for link in standard_links[1:]:
                ticket_lines.append("  " + link)
            
            output_lines.extend(ticket_lines)
    
    # Join with single newlines for better spacing
    return "\n".join(output_lines)

def get_month_from_date(date_str):
    """Extract month from a date string."""
    try:
        if " to " in date_str:
            date_str = date_str.split(" to ")[0]  # Use start date for date ranges
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%B")  # Returns full month name
    except Exception as e:
        logger.warning(f"Could not extract month from date '{date_str}': {e}")
        return None

def filter_dates_by_month(tour_dates, target_month):
    """Filter tour dates to only include dates from the specified month."""
    if not target_month:
        return tour_dates
        
    filtered_dates = []
    for event in tour_dates:
        event_month = get_month_from_date(event['date'])
        if event_month and event_month.lower() == target_month.lower():
            filtered_dates.append(event)
    return filtered_dates

def get_available_months(tour_dates):
    """Get a list of months that have tour dates."""
    months = set()
    for event in tour_dates:
        event_month = get_month_from_date(event['date'])
        if event_month:
            months.add(event_month)
    return sorted(list(months), key=lambda x: datetime.strptime(x, "%B").month)

def get_tour_dates():
    """Get tour dates from cache or scrape if needed."""
    # Try to load from cache first
    cached_dates = load_from_cache()
    if cached_dates:
        logger.info("Using cached tour dates")
        return cached_dates
    
    # If no valid cache, scrape new data
    logger.info("No valid cache found, scraping new tour dates")
    tour_dates = scrape_goose_tour_dates()
    
    if tour_dates:
        # Save to cache for future use
        save_to_cache(tour_dates)
        return tour_dates
    
    return None

def get_formatted_tour_dates(month=None):
    """Get and format tour dates for Discord output."""
    # Always try to get from cache first
    tour_dates = load_from_cache()
    
    if not tour_dates:
        return ["No tour dates found. Please try again later."]
    
    # Process dates to ensure consistent format
    processed_dates = []
    for event in tour_dates:
        event["date"] = process_date(event["date"])
        processed_dates.append(event)
    
    # Sort dates chronologically using the first date for date ranges
    processed_dates.sort(key=lambda x: x['date'].split(" to ")[0])
    
    # If no month specified, return available months
    if month is None:
        available_months = get_available_months(processed_dates)
        if not available_months:
            return ["No upcoming tour dates found."]
            
        message = "**Goose Tour Dates**\n\n"
        message += "**Goose the Organization is playing during these months:**\n"
        message += "• " + "\n• ".join(available_months) + "\n\n"
        message += "Use `/tourdates [month]` to view shows for a specific month."
        return [message]
    
    # Filter by month
    processed_dates = filter_dates_by_month(processed_dates, month)
    if not processed_dates:
        return [f"No tour dates found for {month}."]
    
    # Create messages array
    messages = []
    
    # Add header message with total count and month
    header_message = f"**Goose Tour Dates**\n"
    header_message += f"**{month} Shows** ({len(processed_dates)} upcoming)\n"
    messages.append(header_message)
    
    # Format each event as a separate message
    for event in processed_dates:
        try:
            event_text = format_event_output(event)
            messages.append(event_text)
        except Exception as e:
            logger.error(f"Error formatting event: {e}")
            continue
    
    return messages 