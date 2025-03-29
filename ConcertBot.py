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
INITIAL_RETRY_DELAY = 5  # Increased initial delay
MAX_RETRY_DELAY = 60  # Maximum delay between retries

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"Response status code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        print("Successfully parsed HTML")
        
        tour_dates = []
        # Look for tour dates in the main content area
        events = soup.find_all('div', class_='event')
        print(f"Found {len(events)} event elements")
        
        for event in events:
            try:
                # Try different possible selectors for date
                date_elem = (
                    event.find('div', class_='date') or 
                    event.find('div', class_='event-date') or
                    event.find('span', class_='date')
                )
                
                # Try different possible selectors for venue
                venue_elem = (
                    event.find('div', class_='venue') or 
                    event.find('div', class_='event-venue') or
                    event.find('span', class_='venue')
                )
                
                # Try different possible selectors for location
                location_elem = (
                    event.find('div', class_='location') or 
                    event.find('div', class_='event-location') or
                    event.find('span', class_='location')
                )
                
                if not all([date_elem, venue_elem, location_elem]):
                    print("Missing required elements in event")
                    continue
                
                date_text = date_elem.text.strip()
                venue_text = venue_elem.text.strip()
                location_text = location_elem.text.strip()
                
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
            # Try alternative selectors if no events found
            print("No tour dates found with primary selectors, trying alternatives...")
            events = soup.find_all(['div', 'li'], class_=['tour-date', 'event-item', 'tour-event'])
            print(f"Found {len(events)} alternative event elements")
            
            for event in events:
                try:
                    # Try to find date, venue, and location in the text content
                    text_content = event.get_text(separator='\n').strip()
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    
                    if len(lines) >= 3:
                        date_text = lines[0]
                        venue_text = lines[1]
                        location_text = lines[2]
                        
                        print(f"Found tour date: {date_text} at {venue_text} in {location_text}")
                        
                        tour_dates.append({
                            'date': date_text,
                            'venue': venue_text,
                            'location': location_text
                        })
                except Exception as e:
                    print(f"Error processing alternative event: {e}")
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
                initial_delay = random.uniform(3, 7)
                print(f"Initial startup delay: {initial_delay:.2f} seconds")
                time.sleep(initial_delay)
            
            print(f"Attempting to start bot (attempt {attempt + 1}/{MAX_RETRIES})")
            bot.run(DISCORD_TOKEN)
            break
        except discord.HTTPException as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 2), MAX_RETRY_DELAY)
                print(f"Rate limited on startup. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                print(f"Failed to start bot after {MAX_RETRIES} attempts")
                raise
