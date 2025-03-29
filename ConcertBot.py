import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import datetime
import os
from dotenv import load_dotenv
import json
import asyncio
import time
import random
import sys

# Load environment variables
load_dotenv()

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Get environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv('ANNOUNCEMENTS_CHANNEL_ID'))

# File to store previous tour dates
TOUR_DATES_FILE = 'previous_tour_dates.json'

# Rate limit handling
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 30  # Increased initial delay
MAX_RETRY_DELAY = 300  # Maximum delay between retries (5 minutes)

async def retry_with_backoff(func, *args, **kwargs):
    retry_delay = INITIAL_RETRY_DELAY
    for attempt in range(MAX_RETRIES):
        try:
            return await func(*args, **kwargs)
        except discord.HTTPException as e:
            if e.code == 429:  # Rate limit error
                if attempt < MAX_RETRIES - 1:
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0, 1)
                    actual_delay = min(retry_delay + jitter, MAX_RETRY_DELAY)
                    print(f"Rate limited. Retrying in {actual_delay:.2f} seconds...")
                    await asyncio.sleep(actual_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
            else:
                raise
    return None

def load_previous_tour_dates():
    try:
        with open(TOUR_DATES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_tour_dates(tour_dates):
    with open(TOUR_DATES_FILE, 'w') as f:
        json.dump(tour_dates, f)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    
    # Sync slash commands with retry
    try:
        synced = await retry_with_backoff(bot.tree.sync)
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    check_tour_dates.start()

@tasks.loop(hours=24)  # Check once per day
async def check_tour_dates():
    channel = bot.get_channel(CHANNEL_ID)
    announcements_channel = bot.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    
    if not channel:
        print(f"Could not find channel with ID: {CHANNEL_ID}")
        return
    
    if not announcements_channel:
        print(f"Could not find announcements channel with ID: {ANNOUNCEMENTS_CHANNEL_ID}")
        return
    
    current_tour_dates = get_tour_dates()
    if not current_tour_dates:
        return
    
    # Load previous tour dates
    previous_tour_dates = load_previous_tour_dates()
    
    # Check for new tour dates
    new_tour_dates = []
    for date in current_tour_dates:
        if date not in previous_tour_dates:
            new_tour_dates.append(date)
    
    # If there are new tour dates, announce them
    if new_tour_dates:
        try:
            announcement = "🎸 **Goose the Organization just announced new tour dates!** 🎸"
            await retry_with_backoff(announcements_channel.send, announcement)
            
            for date in new_tour_dates:
                embed = discord.Embed(
                    title="New Tour Date!",
                    description=f"📍 {date['venue']}\n🏙️ {date['location']}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Date", value=date['date'], inline=False)
                await retry_with_backoff(announcements_channel.send, embed=embed)
                await asyncio.sleep(1)  # Add delay between messages
        except Exception as e:
            print(f"Error sending announcements: {e}")
    
    # Save current tour dates for next comparison
    save_tour_dates(current_tour_dates)
    
    # Post all tour dates to the regular channel
    try:
        embed = discord.Embed(
            title="Goose Tour Dates",
            description="Latest tour dates from goosetheband.com",
            color=discord.Color.blue()
        )
        
        for date in current_tour_dates:
            embed.add_field(
                name=date['date'],
                value=f"📍 {date['venue']}\n🏙️ {date['location']}",
                inline=False
            )
        
        await retry_with_backoff(channel.send, embed=embed)
    except Exception as e:
        print(f"Error posting tour dates: {e}")

@bot.tree.command(name="tour_dates", description="Get the latest Goose tour dates")
async def tour_dates(interaction: discord.Interaction):
    await interaction.response.defer()
    
    tour_dates = get_tour_dates()
    
    if not tour_dates:
        await interaction.followup.send("Sorry, I couldn't fetch the tour dates at this time.")
        return
    
    try:
        embed = discord.Embed(
            title="Goose Tour Dates",
            description="Latest tour dates from goosetheband.com",
            color=discord.Color.blue()
        )
        
        for date in tour_dates:
            embed.add_field(
                name=date['date'],
                value=f"📍 {date['venue']}\n🏙️ {date['location']}",
                inline=False
            )
        
        await retry_with_backoff(interaction.followup.send, embed=embed)
    except Exception as e:
        print(f"Error sending tour dates: {e}")
        await interaction.followup.send("Sorry, there was an error sending the tour dates.")

def get_tour_dates():
    url = "https://www.goosetheband.com/tour"
    try:
        print("Fetching tour dates from website...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://www.goosetheband.com/'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"Response status code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        print("Successfully parsed HTML")
        
        # Remove SVG elements, scripts, and marquee elements as they're not relevant for tour dates
        for element in soup.find_all(['svg', 'script', 'style', 'div', 'h1', 'nav'], class_=['Marquee-item', 'Marquee-track', 'Footer-nav', 'sqs-svg-icon--social']):
            element.decompose()
        
        tour_dates = []
        
        # First try to find the main content area
        main_content = soup.find(['main', 'div', 'section'], class_=['Main-content', 'content', 'main-content', 'tour-content'])
        if not main_content:
            print("Could not find main content area, searching entire document")
            main_content = soup
        
        print("Main content classes:", main_content.get('class', []) if main_content else "No classes found")
        
        # Look for the Seated widget
        seated_widget = soup.find('div', id='seated-55fdf2c0')
        if seated_widget:
            print("Found Seated widget")
            artist_id = seated_widget.get('data-artist-id')
            print(f"Artist ID: {artist_id}")
            
            # The Seated widget loads tour dates dynamically via JavaScript
            # We'll need to make a separate request to their API
            seated_url = f"https://widget.seated.com/api/v1/artists/{artist_id}/events"
            print(f"Fetching Seated data from: {seated_url}")
            
            # Headers specific to the Seated API
            seated_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://www.goosetheband.com',
                'Referer': 'https://www.goosetheband.com/tour',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            try:
                seated_response = requests.get(seated_url, headers=seated_headers)
                seated_response.raise_for_status()
                print(f"Seated API response status: {seated_response.status_code}")
                print(f"Seated API response headers: {seated_response.headers}")
                print(f"Seated API response content: {seated_response.text[:500]}...")  # Print first 500 chars
                
                seated_data = seated_response.json()
                
                for event in seated_data.get('events', []):
                    try:
                        # Parse the date from the event data
                        date_text = event.get('date', '')
                        if not date_text:
                            # Try to construct date from start_time if available
                            start_time = event.get('start_time')
                            if start_time:
                                try:
                                    # Convert timestamp to readable date
                                    date = datetime.datetime.fromtimestamp(start_time)
                                    date_text = date.strftime('%B %d, %Y')
                                except:
                                    date_text = "Date TBA"
                        
                        venue_text = event.get('venue', {}).get('name', 'Venue TBA')
                        city = event.get('venue', {}).get('city', '')
                        state = event.get('venue', {}).get('state', '')
                        location_text = f"{city}, {state}" if city and state else "Location TBA"
                        
                        if date_text and venue_text and location_text:
                            print(f"Found tour date from Seated: {date_text} at {venue_text} in {location_text}")
                            tour_dates.append({
                                'date': date_text,
                                'venue': venue_text,
                                'location': location_text
                            })
                    except Exception as e:
                        print(f"Error processing Seated event: {e}")
                        continue
            except requests.exceptions.RequestException as e:
                print(f"Error fetching Seated data: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Seated response status: {e.response.status_code}")
                    print(f"Seated response headers: {e.response.headers}")
                    print(f"Seated response content: {e.response.text}")
            except json.JSONDecodeError as e:
                print(f"Error decoding Seated JSON: {e}")
                print(f"Raw response: {seated_response.text}")
            except Exception as e:
                print(f"Unexpected error with Seated API: {e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
        else:
            print("Could not find Seated widget in HTML")
            # Print the full HTML for debugging
            print("Full HTML content:")
            print(soup.prettify())
        
        # If we didn't find any dates from Seated, try the regular HTML parsing
        if not tour_dates:
            print("No dates found from Seated, trying HTML parsing...")
            # Try to find tour dates in various ways
            potential_containers = main_content.find_all(['div', 'section', 'article'], class_=[
                'tour-dates', 'tour', 'events', 'tour-events', 'tour-schedule',
                'tour-list', 'event-list', 'tour-dates-container', 'tour-schedule-container',
                'sqs-block', 'sqs-block-content'
            ])
            
            if not potential_containers:
                print("Could not find tour dates container, trying alternative methods...")
                # Try to find any elements that look like they might contain tour dates
                potential_containers = main_content.find_all(['div', 'section', 'article'], 
                    class_=lambda x: x and any(term in x.lower() for term in ['tour', 'event', 'date', 'schedule', 'block']))
            
            print(f"Found {len(potential_containers)} potential containers")
            
            # Print all block types for debugging
            blocks = main_content.find_all(class_='sqs-block')
            print("Found blocks:", [block.get('data-block-type', 'unknown') for block in blocks])
            
            for container in potential_containers:
                # Look for individual tour date entries
                events = container.find_all(['div', 'li', 'article', 'tr', 'p'], class_=[
                    'tour-date', 'event', 'tour-event', 'event-item',
                    'tour-date-item', 'event-entry', 'tour-entry', 'tour-date-row',
                    'sqs-block-content'
                ])
                
                if not events:
                    # Try to find events by looking for date-like text
                    events = container.find_all(['div', 'li', 'article', 'tr', 'p'], 
                        string=lambda x: x and any(term in x.lower() for term in ['2024', '2025', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']))
                
                print(f"Found {len(events)} potential events in container")
                
                for event in events:
                    try:
                        # Print event HTML for debugging
                        print("Event HTML:", event.prettify())
                        
                        # Try to find the date
                        date_elem = (
                            event.find(['div', 'span', 'td', 'p'], class_=['date', 'event-date', 'tour-date-date']) or
                            event.find('time') or
                            event.find(string=lambda x: x and any(term in x.lower() for term in ['2024', '2025', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']))
                        )
                        
                        # Try to find the venue
                        venue_elem = (
                            event.find(['div', 'span', 'td', 'p'], class_=['venue', 'event-venue', 'tour-date-venue']) or
                            event.find(string=lambda x: x and any(term in x.lower() for term in ['theater', 'theatre', 'arena', 'hall', 'center', 'centre', 'club', 'venue']))
                        )
                        
                        # Try to find the location
                        location_elem = (
                            event.find(['div', 'span', 'td', 'p'], class_=['location', 'event-location', 'tour-date-location']) or
                            event.find(string=lambda x: x and any(term in x.lower() for term in ['ny', 'ca', 'tx', 'fl', 'il', 'co', 'ma', 'pa', 'ga', 'tn', 'va', 'nc', 'sc', 'md', 'dc']))
                        )
                        
                        # If we can't find elements by class, try to find them by text structure
                        if not all([date_elem, venue_elem, location_elem]):
                            text_content = event.get_text(separator='\n').strip()
                            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                            
                            if len(lines) >= 3:
                                date_text = lines[0]
                                venue_text = lines[1]
                                location_text = lines[2]
                            else:
                                print("Could not find required information in event text")
                                continue
                        else:
                            date_text = date_elem.text.strip() if date_elem else "Date TBA"
                            venue_text = venue_elem.text.strip() if venue_elem else "Venue TBA"
                            location_text = location_elem.text.strip() if location_elem else "Location TBA"
                        
                        # Clean up the text
                        date_text = ' '.join(date_text.split())
                        venue_text = ' '.join(venue_text.split())
                        location_text = ' '.join(location_text.split())
                        
                        # Skip if this looks like a marquee or header text
                        if any(term in date_text.lower() for term in ['on tour', 'goose', 'tour dates']):
                            print("Skipping marquee/header text")
                            continue
                        
                        print(f"Found tour date: {date_text} at {venue_text} in {location_text}")
                        
                        tour_dates.append({
                            'date': date_text,
                            'venue': venue_text,
                            'location': location_text
                        })
                    except Exception as e:
                        print(f"Error processing event: {e}")
                        continue
        
        if not tour_dates:
            print("No tour dates found in the parsed HTML")
            # Print the full HTML for debugging
            print("Full HTML content:")
            print(soup.prettify())
            return None
            
        print(f"Successfully found {len(tour_dates)} tour dates")
        return tour_dates
        
    except requests.RequestException as e:
        print(f"Error fetching tour dates: {e}")
        print(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_tour_dates: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is not set")
    if not CHANNEL_ID:
        raise ValueError("CHANNEL_ID environment variable is not set")
    if not ANNOUNCEMENTS_CHANNEL_ID:
        raise ValueError("ANNOUNCEMENTS_CHANNEL_ID environment variable is not set")
    
    # Add retry logic for bot startup with jitter
    for attempt in range(MAX_RETRIES):
        try:
            # Add initial delay with jitter before first attempt
            if attempt == 0:
                initial_delay = random.uniform(60, 120)  # Much longer initial delay (1-2 minutes)
                print(f"Initial startup delay: {initial_delay:.2f} seconds")
                time.sleep(initial_delay)
            else:
                # Exponential backoff with jitter for subsequent attempts
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(30, 60), MAX_RETRY_DELAY)
                print(f"Waiting {delay:.2f} seconds before next attempt...")
                time.sleep(delay)
            
            print(f"Attempting to start bot (attempt {attempt + 1}/{MAX_RETRIES})")
            
            # Create a new event loop for each attempt
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Set up the bot with proper rate limit handling
                bot._connection.http.rate_limit = True
                bot._connection.http.max_retries = MAX_RETRIES
                
                # Start the bot
                loop.run_until_complete(bot.start(DISCORD_TOKEN))
                print("Bot started successfully!")
                break
            except Exception as e:
                print(f"Error during bot startup: {e}")
                if loop and not loop.is_closed():
                    loop.close()
                if attempt == MAX_RETRIES - 1:
                    raise
                continue
            finally:
                # Clean up the event loop
                try:
                    if loop and not loop.is_closed():
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        loop.close()
                except Exception as e:
                    print(f"Error cleaning up event loop: {e}")
                
        except discord.HTTPException as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                print(f"Rate limited on startup. Will retry with exponential backoff.")
                continue
            else:
                print(f"Failed to start bot after {MAX_RETRIES} attempts")
                sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}")
            sys.exit(1)
