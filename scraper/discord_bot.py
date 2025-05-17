"""
Discord bot module for Goose Tour Dates Scraper.

This module provides:
- Automated posting of new concerts to Discord
- Manual trigger of scraper via /scrape command
- System status checking via /status command
- Bot restart functionality via /restart command
- Authorization checks for commands
- Comprehensive logging and error handling

The bot requires the following environment variables:
- DISCORD_TOKEN: Your bot's authentication token
- DISCORD_CHANNEL_ID: ID of the channel to post updates
- AUTHORIZED_USER_ID: ID of the user allowed to use commands
- BOT_APPLICATION_ID: Your bot's application ID
- DISCORD_GUILD_ID: ID of the Discord server (optional)

All paths are relative to the project root (GooseTourDates/).
"""

import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import sys
from pathlib import Path
from typing import Optional
from goose_scraper import GooseTourScraper
from concert_comparator import ConcertComparator
from reporting import ScraperReporter
import traceback
import logging
import json
from datetime import datetime

# Configure logging to both file and console
# Logs are stored in logs/discord_bot.log relative to project root
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG level for development, change to INFO for production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/discord_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('discord_bot')

# Load environment variables from .env file
load_dotenv()
logger.debug("Environment variables loaded")

# Bot configuration from environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', '859536104570486805'))
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID', '589514250771234829'))
BOT_APPLICATION_ID = os.getenv('BOT_APPLICATION_ID', '1355578032714154038')
DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')
if DISCORD_GUILD_ID:
    DISCORD_GUILD_ID = int(DISCORD_GUILD_ID)
    logger.debug(f"Guild ID set to: {DISCORD_GUILD_ID}")
else:
    logger.warning("No Guild ID set - commands will sync globally")

logger.debug("Bot configuration loaded")

# Initialize bot with required intents
intents = discord.Intents.default()
intents.message_content = True  # Required for reading message content
bot = commands.Bot(command_prefix='!', intents=intents)
logger.debug("Bot initialized with intents")

# Store last scrape time for status reporting
last_scrape_time = None

# Add project root to Python path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

class BotError(Exception):
    """Base exception for bot-related errors."""
    pass

class ChannelNotFoundError(BotError):
    """Raised when the target channel cannot be found."""
    pass

class AuthorizationError(BotError):
    """Raised when a user is not authorized to use a command."""
    pass

class GooseTourBot:
    """
    Main bot class that handles:
    - Concert comparison and scraping
    - Discord message posting
    - Status reporting
    - Error handling
    """
    def __init__(self):
        try:
            self.comparator = ConcertComparator()
            self.reporter = ScraperReporter()
            self.channel: Optional[discord.TextChannel] = None
            logger.info("GooseTourBot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GooseTourBot: {e}")
            raise BotError(f"Bot initialization failed: {e}")
        
    async def setup(self):
        """Initialize the bot and get the target channel."""
        try:
            await bot.wait_until_ready()
            self.channel = bot.get_channel(DISCORD_CHANNEL_ID)
            if not self.channel:
                raise ChannelNotFoundError(f"Could not find channel with ID {DISCORD_CHANNEL_ID}")
            logger.info(f"Bot connected to channel: {self.channel.name}")
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            raise BotError(f"Bot setup failed: {e}")
        
    async def post_new_concerts(self, concerts: list):
        """
        Post new concerts to Discord channel.
        
        Args:
            concerts (list): List of concert dictionaries containing:
                - venue: Venue name
                - start_date: Event start date
                - location: Venue location
                - ticket_link: Link to purchase tickets
                - vip_link: Optional VIP ticket link
                - additional_info: Optional list of additional information
        """
        if not concerts:
            return
            
        try:
            embed = discord.Embed(
                title="🎸 New Goose Tour Dates!",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            
            for concert in concerts:
                try:
                    venue = concert['venue']
                    date = concert['start_date'].split('T')[0]  # Format: YYYY-MM-DD
                    location = concert['location']
                    ticket_link = concert['ticket_link']
                    
                    # Add VIP info if available
                    vip_info = ""
                    if concert.get('vip_link'):
                        vip_info = "\n🎫 VIP tickets available!"
                        
                    # Add additional info if available
                    additional_info = ""
                    if concert.get('additional_info'):
                        additional_info = "\nℹ️ " + " | ".join(concert['additional_info'])
                        
                    embed.add_field(
                        name=f"{venue} - {date}",
                        value=f"📍 {location}\n🔗 [Get Tickets]({ticket_link}){vip_info}{additional_info}",
                        inline=False
                    )
                except KeyError as e:
                    logger.error(f"Missing required field in concert data: {e}")
                    continue
                    
            await self.channel.send(embed=embed)
            logger.info(f"Posted {len(concerts)} new concerts to Discord")
        except Exception as e:
            logger.error(f"Failed to post concerts: {e}")
            raise BotError(f"Failed to post concerts: {e}")
        
    async def check_status(self):
        """
        Check and post the status of the bot and system.
        
        Reports:
        - Data directory status
        - Log directory status
        - Last scrape time
        - System status
        - Bot uptime
        """
        try:
            embed = discord.Embed(
                title="🤖 Bot Status",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            
            # Check if data directories exist
            data_dir = Path("data")
            scraped_dir = data_dir / "scraped_concerts"
            new_concerts_dir = data_dir / "new_concerts"
            
            embed.add_field(
                name="Data Directories",
                value=f"📁 Scraped Data: {'✅' if scraped_dir.exists() else '❌'}\n"
                      f"📁 New Concerts: {'✅' if new_concerts_dir.exists() else '❌'}",
                inline=False
            )
            
            # Check log directory
            log_dir = Path("logs")
            embed.add_field(
                name="Logging",
                value=f"📝 Log Directory: {'✅' if log_dir.exists() else '❌'}",
                inline=False
            )
            
            # Check last scrape time
            last_scrape = self.reporter.get_last_scrape_time()
            embed.add_field(
                name="Last Scrape",
                value=f"⏰ {last_scrape if last_scrape else 'Never'}",
                inline=False
            )
            
            # Add system status
            embed.add_field(
                name="System Status",
                value=f"🟢 Bot Online\n"
                      f"🟢 Channel Connected\n"
                      f"🟢 Scheduler Running",
                inline=False
            )
            
            # Add uptime
            embed.add_field(
                name="Uptime",
                value=f"⏱️ Bot has been running since: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                inline=False
            )
            
            await self.channel.send(embed=embed)
            logger.info("Status check completed successfully")
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            raise BotError(f"Status check failed: {e}")

# Initialize the bot instance
goose_bot = GooseTourBot()

@bot.event
async def on_ready():
    """
    Called when the bot is ready and connected to Discord.
    
    This function:
    1. Logs bot connection details
    2. Sets up the bot
    3. Syncs commands to the guild
    """
    try:
        logger.info(f"Bot connected as {bot.user.name}")
        logger.debug(f"Bot user ID: {bot.user.id}")
        logger.debug(f"Bot is in {len(bot.guilds)} guilds")
        
        await goose_bot.setup()
        logger.debug("GooseTourBot setup completed")
        
        # Sync commands to a specific guild for instant update if GUILD_ID is set
        if DISCORD_GUILD_ID:
            logger.debug(f"Attempting to sync commands to guild {DISCORD_GUILD_ID}")
            guild = discord.Object(id=DISCORD_GUILD_ID)
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} command(s) to guild {DISCORD_GUILD_ID}")
            for cmd in synced:
                logger.debug(f"Synced command: {cmd.name}")
        else:
            logger.debug("Syncing commands globally")
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} command(s) globally")
            for cmd in synced:
                logger.debug(f"Synced command: {cmd.name}")
    except Exception as e:
        logger.error(f"Bot startup failed: {e}\n{traceback.format_exc()}")
        sys.exit(1)

def is_authorized():
    """
    Check if the user is authorized to use commands.
    
    Returns:
        bool: True if user is authorized, False otherwise
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            if interaction.user.id != AUTHORIZED_USER_ID:
                await interaction.response.send_message(
                    "❌ You are not authorized to use this command.",
                    ephemeral=True
                )
                return False
            return True
        except Exception as e:
            logger.error(f"Authorization check failed: {e}")
            await interaction.response.send_message(
                "❌ An error occurred during authorization check.",
                ephemeral=True
            )
            return False
    return app_commands.check(predicate)

@bot.tree.command(
    name="scrape",
    description="Manually trigger the scraper to check for new tour dates"
)
@app_commands.checks.cooldown(1, 300)  # 5 minute cooldown
@is_authorized()
async def manual_scrape(interaction: discord.Interaction):
    """
    Manually trigger the scraper and comparator.
    
    This command:
    1. Runs the scraper
    2. Compares with previous data
    3. Posts any new concerts found
    4. Updates last scrape time
    """
    try:
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        logger.debug("Scrape command received, deferring response")
        
        # Send initial status
        await interaction.followup.send("🔄 Starting manual scrape...", ephemeral=True)
        
        try:
            # Run the scraper
            new_concerts = goose_bot.comparator.process_new_concerts()
            
            if new_concerts:
                # Post new concerts to the channel
                await goose_bot.post_new_concerts(new_concerts)
                await interaction.followup.send(
                    f"✅ Found {len(new_concerts)} new concerts! Check the channel for details.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "ℹ️ No new concerts found.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error during scrape: {e}\n{traceback.format_exc()}")
            await interaction.followup.send(
                f"❌ Error during scrape: {str(e)}\nPlease check the logs for more details.",
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Error handling scrape command: {e}\n{traceback.format_exc()}")
        try:
            await interaction.followup.send(
                "❌ An unexpected error occurred. Please check the logs for more details.",
                ephemeral=True
            )
        except:
            pass

@bot.tree.command(
    name="status",
    description="Check the status of the bot and system"
)
@app_commands.checks.cooldown(1, 60)  # 1 minute cooldown
@is_authorized()
async def check_status(interaction: discord.Interaction):
    """
    Check the status of the bot and system.
    
    This command:
    1. Checks data directory status
    2. Checks log directory status
    3. Reports last scrape time
    4. Shows system status
    5. Displays bot uptime
    """
    try:
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)
        logger.debug("Status command received, deferring response")
        
        # Create status embed
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        # Check if data directories exist
        data_dir = Path("data")
        scraped_dir = data_dir / "scraped_concerts"
        new_concerts_dir = data_dir / "new_concerts"
        
        embed.add_field(
            name="Data Directories",
            value=f"📁 Scraped Data: {'✅' if scraped_dir.exists() else '❌'}\n"
                  f"📁 New Concerts: {'✅' if new_concerts_dir.exists() else '❌'}",
            inline=False
        )
        
        # Check log directory
        log_dir = Path("logs")
        embed.add_field(
            name="Logging",
            value=f"📝 Log Directory: {'✅' if log_dir.exists() else '❌'}",
            inline=False
        )
        
        # Check last scrape time
        try:
            last_scrape = goose_bot.reporter.get_last_scrape_time()
            embed.add_field(
                name="Last Scrape",
                value=f"⏰ {last_scrape if last_scrape else 'Never'}",
                inline=False
            )
        except Exception as e:
            logger.error(f"Error getting last scrape time: {e}")
            embed.add_field(
                name="Last Scrape",
                value="❌ Error retrieving last scrape time",
                inline=False
            )
        
        # Add system status
        embed.add_field(
            name="System Status",
            value=f"🟢 Bot Online\n"
                  f"🟢 Channel Connected\n"
                  f"🟢 Scheduler Running",
            inline=False
        )
        
        # Add uptime
        embed.add_field(
            name="Uptime",
            value=f"⏱️ Bot has been running since: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            inline=False
        )
        
        # Send the response
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info("Status check completed successfully")
        
    except Exception as e:
        logger.error(f"Status check failed: {e}\n{traceback.format_exc()}")
        try:
            await interaction.followup.send(
                f"❌ Error during status check: {str(e)}\nPlease check the logs for more details.",
                ephemeral=True
            )
        except Exception as followup_error:
            logger.error(f"Failed to send error message: {followup_error}")

@bot.tree.command(
    name="restart",
    description="Restart the bot"
)
@app_commands.checks.cooldown(1, 300)  # 5 minute cooldown
@is_authorized()
async def restart_bot(interaction: discord.Interaction):
    """
    Restart the bot.
    
    This command:
    1. Sends a restart message
    2. Closes the bot
    3. Restarts the Python process
    """
    try:
        await interaction.response.send_message("🔄 Restarting bot...")
        await bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)
    except Exception as e:
        logger.error(f"Bot restart failed: {e}\n{traceback.format_exc()}")
        await interaction.followup.send(
            f"❌ Error during restart: {str(e)}\nPlease check the logs for more details.",
            ephemeral=True
        )

@manual_scrape.error
@check_status.error
@restart_bot.error
async def command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """
    Handle command errors.
    
    This function handles:
    - Command cooldowns
    - Authorization errors
    - Other command errors
    """
    try:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏰ This command is on cooldown. Try again in {error.retry_after:.0f} seconds.",
                ephemeral=True
            )
        elif isinstance(error, AuthorizationError):
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.",
                ephemeral=True
            )
        else:
            logger.error(f"Command error: {error}\n{traceback.format_exc()}")
            await interaction.response.send_message(
                f"❌ An error occurred: {str(error)}\nPlease check the logs for more details.",
                ephemeral=True
            )
    except Exception as e:
        logger.error(f"Error handler failed: {e}\n{traceback.format_exc()}")
        try:
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please check the logs.",
                ephemeral=True
            )
        except:
            pass

def run_bot():
    """
    Run the Discord bot.
    
    This function:
    1. Verifies the Discord token exists
    2. Starts the bot
    3. Handles any runtime errors
    """
    if not DISCORD_TOKEN:
        logger.error("Discord token not found in environment variables")
        sys.exit(1)
        
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot runtime error: {e}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    run_bot() 