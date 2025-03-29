from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime
import os
import time
import logging
import subprocess
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Remove timestamp and level from output
    force=True  # Force reconfiguration of the root logger
)
logger = logging.getLogger(__name__)

# Add a file handler for debugging
file_handler = logging.FileHandler('goose_tour_dates.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Add connection retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5

def get_chrome_version():
    """Get the installed Chrome version."""
    try:
        # Try different commands to get Chrome version
        for cmd in ['google-chrome --version', 'google-chrome-stable --version']:
            try:
                result = subprocess.run(cmd.split(), capture_output=True, text=True)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    logger.info(f"Found Chrome version: {version}")
                    return version
            except:
                continue
        return None
    except Exception as e:
        logger.error(f"Error getting Chrome version: {e}")
        return None

def setup_driver():
    """Set up and return a Chrome WebDriver instance."""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use environment variables for Chrome and ChromeDriver paths
        chrome_bin = os.getenv('CHROME_BIN', '/usr/bin/google-chrome')
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
        
        chrome_options.binary_location = chrome_bin
        service = Service(chromedriver_path)
        
        # Create driver with service and options
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set window size
        driver.set_window_size(1920, 1080)
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        return driver
    except Exception as e:
        logger.error(f"Error setting up Chrome driver: {e}")
        raise

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

def scrape_goose_tour_dates():
    driver = None
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            # Set up the driver
            logger.info(f"Setting up Chrome driver (attempt {attempt + 1}/{max_retries})...")
            driver = setup_driver()
            
            # Navigate to tour page
            logger.info("Navigating to Goose tour page...")
            driver.get("https://www.goosetheband.com/tour")
            
            # Wait for the page to load completely
            logger.info("Waiting for page to load...")
            wait = WebDriverWait(driver, 30)
            
            # First wait for the body to be present
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Then wait for the tour container with a longer timeout
            logger.info("Waiting for tour dates to load...")
            try:
                tour_container = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "seated-event-row"))
                )
            except Exception as e:
                logger.error(f"Timeout waiting for tour container: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
            
            # Add a small delay to ensure dynamic content is loaded
            time.sleep(5)
            
            # Extract tour data
            logger.info("Extracting tour dates...")
            tour_dates = []
            
            # Find all event containers
            event_elements = driver.find_elements(By.CSS_SELECTOR, ".seated-event-row")
            logger.info(f"Found {len(event_elements)} event elements")
            
            # Track processed dates to prevent duplicates
            processed_dates = set()
            
            for event in event_elements:
                try:
                    # Skip past events
                    if "past-event" in event.get_attribute("class"):
                        continue
                    
                    # Extract all information first before processing
                    date_element = event.find_element(By.CSS_SELECTOR, ".seated-event-date-cell")
                    venue_element = event.find_element(By.CSS_SELECTOR, ".seated-event-venue-name")
                    location_element = event.find_element(By.CSS_SELECTOR, ".seated-event-venue-location")
                    
                    # Get the text values
                    date_str = date_element.text.strip() if date_element else ""
                    venue = venue_element.text.strip() if venue_element else ""
                    location = location_element.text.strip() if location_element else ""
                    
                    # Skip if we're missing essential information
                    if not all([date_str, venue, location]):
                        continue
                    
                    # Create a unique identifier for the event
                    event_id = f"{date_str}_{venue}_{location}"
                    
                    # Skip if we've already processed this event
                    if event_id in processed_dates:
                        continue
                    
                    processed_dates.add(event_id)
                    
                    # Extract details info if present
                    try:
                        details_element = event.find_element(By.CSS_SELECTOR, ".seated-event-details-cell")
                        details = details_element.text.strip()
                    except:
                        details = ""
                    
                    # Extract ticket links
                    ticket_links = []
                    ticket_elements = event.find_elements(By.CSS_SELECTOR, ".seated-event-link")
                    for ticket_element in ticket_elements:
                        ticket_link = ticket_element.get_attribute("href")
                        ticket_text = ticket_element.text.strip()
                        if ticket_link and ticket_text:
                            ticket_links.append(f"{ticket_text}: {ticket_link}")
                    
                    # Join ticket links with semicolons
                    ticket_links_str = "; ".join(ticket_links)
                    
                    tour_dates.append({
                        "date": date_str,
                        "venue": venue,
                        "location": location,
                        "ticketLinks": ticket_links_str,
                        "additionalInfo": details if details else ""
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing event: {e}")
                    continue
            
            if not tour_dates:
                logger.warning("No tour dates found in the page")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                return None
            
            # Process dates to ensure consistent format
            processed_dates = []
            for event in tour_dates:
                event["date"] = process_date(event["date"])
                processed_dates.append(event)
            
            return processed_dates
            
        except Exception as e:
            logger.error(f"Error scraping tour dates (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.error(f"Error closing browser: {e}")
    
    return None

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
    
    # Always start with date
    output_lines.append(f"Date: {format_date_for_display(event['date'])}")
    
    # Add venue and location
    output_lines.append(f"Venue: {event['venue']}")
    output_lines.append(f"Location: {event['location']}")
    
    # Add ticket links if present
    if event['ticketLinks']:
        output_lines.append(f"Ticket Links: {event['ticketLinks']}")
    
    # Add additional info if present
    if event['additionalInfo']:
        output_lines.append(f"Additional Info: {event['additionalInfo']}")
    
    # Add separator with consistent length
    output_lines.append("-" * 50)
    
    # Join with double newlines for better spacing
    return "\n\n".join(output_lines)

def get_formatted_tour_dates():
    """Get and format tour dates for Discord output."""
    tour_dates = scrape_goose_tour_dates()
    
    if not tour_dates:
        return "No tour dates found. The page structure may have changed."
    
    # Sort dates chronologically using the first date for date ranges
    tour_dates.sort(key=lambda x: x['date'].split(" to ")[0])
    
    # Group events by month for better readability
    events_by_month = {}
    
    # First, group events by month
    for date in tour_dates:
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
    
    # Build the output message
    output_lines = []
    output_lines.append(f"Found {len(tour_dates)} tour dates:")
    output_lines.append("=" * 50)
    
    # Then format events grouped by month
    for month in sorted(events_by_month.keys()):
        # Format month header
        month_output = [
            f"\n{month}",
            "-" * len(month)
        ]
        output_lines.extend(month_output)
        
        # Sort events within each month by date
        month_events = sorted(events_by_month[month], 
                           key=lambda x: x['date'].split(" to ")[0])
        
        # Format all events in this month
        for date in month_events:
            try:
                output_lines.append(format_event_output(date))
            except Exception as e:
                logger.error(f"Error formatting event: {e}")
                continue
    
    return "\n".join(output_lines)

async def split_and_send_message(interaction: discord.Interaction, message: str, max_length: int = 1900):
    """Split and send a long message in chunks."""
    try:
        # Split by month separators
        parts = message.split("\n" + "=" * 50)
        current_message = parts[0]
        
        for part in parts[1:]:
            next_chunk = "\n" + "=" * 50 + part
            if len(current_message + next_chunk) > max_length:
                await interaction.followup.send(current_message, ephemeral=True)
                current_message = "=" * 50 + part
            else:
                current_message += next_chunk
        
        if current_message:
            await interaction.followup.send(current_message, ephemeral=True)
    except Exception as e:
        logger.error(f"Error splitting and sending message: {e}")
        raise

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    logger.info(f'Bot is ready! Logged in as {bot.user.name}')
    
    # Sync commands with Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.event
async def on_disconnect():
    """Called when the bot disconnects from Discord."""
    logger.warning("Bot disconnected from Discord. Attempting to reconnect...")
    for attempt in range(MAX_RETRIES):
        try:
            await bot.close()
            await bot.start(os.getenv('DISCORD_TOKEN'))
            logger.info("Successfully reconnected to Discord")
            return
        except Exception as e:
            logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
            else:
                logger.error("Failed to reconnect after maximum attempts")

@bot.tree.command(name="tourdates", description="Get upcoming Goose tour dates")
async def tour_dates(interaction: discord.Interaction):
    """Slash command to get tour dates."""
    # Get allowed role IDs from environment variables
    role_ids_str = os.getenv('ALLOWED_ROLE_IDS', '')
    if not role_ids_str:
        logger.error("No allowed role IDs found in environment variables!")
        await interaction.response.send_message(
            "Configuration error: Allowed roles not set. Please contact an administrator.",
            ephemeral=True
        )
        return
    
    try:
        # Convert comma-separated string to list of integers
        allowed_roles = [int(role_id.strip()) for role_id in role_ids_str.split(',')]
    except ValueError as e:
        logger.error(f"Error parsing role IDs: {e}")
        await interaction.response.send_message(
            "Configuration error: Invalid role ID format. Please contact an administrator.",
            ephemeral=True
        )
        return
    
    # Check if user has required roles
    user_roles = [role.id for role in interaction.user.roles]
    
    if not any(role_id in user_roles for role_id in allowed_roles):
        await interaction.response.send_message(
            "You don't have permission to use this command. Required roles: Goose Tour Dates, Goose Tour Dates Admin",
            ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)  # Make the response ephemeral
    
    try:
        # Get the tour dates
        tour_dates_message = get_formatted_tour_dates()
        
        # Split and send the message
        await split_and_send_message(interaction, tour_dates_message)
            
    except Exception as e:
        logger.error(f"Error in tour_dates command: {e}")
        try:
            await interaction.followup.send(
                "An error occurred while fetching tour dates. Please try again later.",
                ephemeral=True
            )
        except:
            logger.error("Failed to send error message to user")

def main():
    """Main function to run the Discord bot."""
    logger.info("Starting Goose Tour Date Bot")
    logger.info("=" * 50)
    
    # Get the Discord token from environment variables
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("No Discord token found in environment variables!")
        return
    
    # Run the Discord bot with retry logic
    while True:
        try:
            bot.run(token)
            break
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            logger.info(f"Attempting to restart in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

if __name__ == "__main__":
    main()