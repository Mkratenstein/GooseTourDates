import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import datetime
import os
from dotenv import load_dotenv
import json

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
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
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
        announcement = "🎸 **Goose the Organization just announced new tour dates!** 🎸"
        await announcements_channel.send(announcement)
        
        for date in new_tour_dates:
            embed = discord.Embed(
                title="New Tour Date!",
                description=f"📍 {date['venue']}\n🏙️ {date['location']}",
                color=discord.Color.green()
            )
            embed.add_field(name="Date", value=date['date'], inline=False)
            await announcements_channel.send(embed=embed)
    
    # Save current tour dates for next comparison
    save_tour_dates(current_tour_dates)
    
    # Post all tour dates to the regular channel
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
    
    await channel.send(embed=embed)

@bot.tree.command(name="tour_dates", description="Get the latest Goose tour dates")
async def tour_dates(interaction: discord.Interaction):
    await interaction.response.defer()
    
    tour_dates = get_tour_dates()
    
    if not tour_dates:
        await interaction.followup.send("Sorry, I couldn't fetch the tour dates at this time.")
        return
    
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
    
    await interaction.followup.send(embed=embed)

def get_tour_dates():
    url = "https://www.goosetheband.com/tour"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        tour_dates = []
        events = soup.find_all('div', class_='tour-date')
        
        for event in events:
            date = event.find('div', class_='date').text.strip()
            venue = event.find('div', class_='venue').text.strip()
            location = event.find('div', class_='location').text.strip()
            
            tour_dates.append({
                'date': date,
                'venue': venue,
                'location': location
            })
            
        return tour_dates
    except requests.RequestException as e:
        print(f"Error fetching tour dates: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is not set")
    if not CHANNEL_ID:
        raise ValueError("CHANNEL_ID environment variable is not set")
    if not ANNOUNCEMENTS_CHANNEL_ID:
        raise ValueError("ANNOUNCEMENTS_CHANNEL_ID environment variable is not set")
    
    bot.run(DISCORD_TOKEN)
