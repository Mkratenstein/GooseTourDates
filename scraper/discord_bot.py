"""
Discord bot module for Goose Tour Dates Scraper.

This module provides:
- Automated posting of new concerts to Discord
- Manual trigger of scraper via /scrape command
- System status checking via /status command
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
from scraper.goose_scraper import GooseTourScraper
from scraper.concert_comparator import ConcertComparator
from scraper.reporting import ScraperReporter
import traceback
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from scraper.railway_config import setup_railway

# Setup Railway configurations
railway_config = setup_railway()

# Load environment variables
load_dotenv()

# Create logs directory if it doesn't exist
logs_dir = Path("scraper/logs")
logs_dir.mkdir(parents=True, exist_ok=True)

# Configure logging to both file and console
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.DEBUG)

# Create a rotating file handler (1MB max size, keep 5 backup files)
log_file = logs_dir / "discord_bot.log"
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=1024*1024,  # 1MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Now clean up old logs (logger is set up)
def cleanup_old_logs():
    """Clean up old timestamped log files, keeping only the 5 most recent ones."""
    try:
        # Find all timestamped log files
        old_logs = list(logs_dir.glob("discord_bot_*.log"))
        if not old_logs:
            return
        # Sort by modification time (newest first)
        old_logs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        # Keep the 5 most recent files, delete the rest
        for old_log in old_logs[5:]:
            try:
                old_log.unlink()
                # Use print as logger may not be set up yet
                print(f"Deleted old log file: {old_log}")
            except Exception as e:
                print(f"Failed to delete old log file {old_log}: {e}")
        print(f"Cleaned up {len(old_logs[5:])} old log files")
    except Exception as e:
        print(f"Error during log cleanup: {e}")

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
                - end_date: Event end date (optional)
                - location: Venue location
                - ticket_link: Link to purchase tickets
                - additional_info: Optional list of additional information
        """
        if not concerts:
            return
            
        try:
            for concert in concerts:
                try:
                    venue = concert['venue']
                    start_date = datetime.fromisoformat(concert['start_date']).strftime('%B %d, %Y')
                    end_date = datetime.fromisoformat(concert['end_date']).strftime('%B %d, %Y') if concert.get('end_date') else None
                    location = concert['location']
                    ticket_link = concert['ticket_link']
                    
                    # Format the date range
                    date_range = f"{start_date} to {end_date}" if end_date else start_date
                    
                    # Create the message
                    message = (
                        "Goose the Organization has announced a new show!\n\n"
                        f"{date_range}\n"
                        f"{venue} | {location}\n"
                        f"🎫 Tickets: [{ticket_link}]({ticket_link})"
                    )
                    
                    # Add additional info if available, each as a bullet point
                    if concert.get('additional_info'):
                        message += "\n\n" + "\n".join(f"- {line}" for line in concert['additional_info'])
                    
                    await self.channel.send(message)
                    
                except KeyError as e:
                    logger.error(f"Missing required field in concert data: {e}")
                    continue
                    
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
            data_dir = Path("scraper/data")
            scraped_dir = data_dir / "scraped_concerts"
            new_concerts_dir = data_dir / "new_concerts"
            
            embed.add_field(
                name="Data Directories",
                value=f"📁 Scraped Data: {'✅' if scraped_dir.exists() else '❌'}\n"
                      f"📁 New Concerts: {'✅' if new_concerts_dir.exists() else '❌'}",
                inline=False
            )
            
            # Check log directory
            log_dir = Path("scraper/logs")
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
    3. Syncs only the current commands to the guild/global
    """
    try:
        logger.info(f"Bot connected as {bot.user.name}")
        logger.debug(f"Bot user ID: {bot.user.id}")
        logger.debug(f"Bot is in {len(bot.guilds)} guilds")

        await goose_bot.setup()
        logger.debug("GooseTourBot setup completed")

        guild = None
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=DISCORD_GUILD_ID)

        # Normal sync logic only
        logger.debug("Syncing commands...")
        if guild:
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} command(s) to guild {DISCORD_GUILD_ID}")
            for cmd in synced:
                logger.debug(f"Synced command: {cmd.name}")
        else:
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
    description="Manually trigger the scraper to check for new tour dates",
    guild=discord.Object(id=DISCORD_GUILD_ID) if DISCORD_GUILD_ID else None
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
        logger.info("Starting manual scrape process")
        
        try:
            # Run the scraper
            logger.debug("Calling process_new_concerts()")
            new_concerts = goose_bot.comparator.process_new_concerts()
            logger.info(f"Scrape completed. Found {len(new_concerts)} new concerts")
            
            if new_concerts:
                # Post new concerts to the channel
                logger.debug("Posting new concerts to Discord")
                await goose_bot.post_new_concerts(new_concerts)
                await interaction.followup.send(
                    f"✅ Found {len(new_concerts)} new concerts! Check the channel for details.",
                    ephemeral=True
                )
                logger.info("Successfully posted new concerts to Discord")
            else:
                await interaction.followup.send(
                    "ℹ️ No new concerts found.",
                    ephemeral=True
                )
                logger.info("No new concerts found during scrape")
                
        except Exception as e:
            error_msg = f"Error during scrape: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            await interaction.followup.send(
                f"❌ Error during scrape: {str(e)}\nPlease check the logs for more details.",
                ephemeral=True
            )
            
    except Exception as e:
        error_msg = f"Error handling scrape command: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please check the logs for more details.",
                ephemeral=True
            )

@bot.tree.command(
    name="status",
    description="Check the status of the bot and system",
    guild=discord.Object(id=DISCORD_GUILD_ID) if DISCORD_GUILD_ID else None
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
        data_dir = Path("scraper/data")
        scraped_dir = data_dir / "scraped_concerts"
        new_concerts_dir = data_dir / "new_concerts"
        
        embed.add_field(
            name="Data Directories",
            value=f"📁 Scraped Data: {'✅' if scraped_dir.exists() else '❌'}\n"
                  f"📁 New Concerts: {'✅' if new_concerts_dir.exists() else '❌'}"
        )
        
        # Check log directory
        log_dir = Path("scraper/logs")
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
        error_msg = f"Status check failed: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ Error during status check: {str(e)}\nPlease check the logs for more details.",
                ephemeral=True
            )

@manual_scrape.error
@check_status.error
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
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"⏰ This command is on cooldown. Try again in {error.retry_after:.0f} seconds.",
                    ephemeral=True
                )
        elif isinstance(error, AuthorizationError):
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ You are not authorized to use this command.",
                    ephemeral=True
                )
        else:
            logger.error(f"Command error: {error}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ An error occurred: {str(error)}\nPlease check the logs for more details.",
                    ephemeral=True
                )
    except Exception as e:
        logger.error(f"Error handler failed: {e}\n{traceback.format_exc()}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please check the logs.",
                ephemeral=True
            )

def run_bot():
    """Run the Discord bot."""
    try:
        print("\n=== Goose Tour Bot Starting ===")
        print(f"Log file: {log_file}")
        print("Initializing bot...")
        
        # If running on Railway, start a simple HTTP server to keep the app alive
        if railway_config['is_railway']:
            print("Railway environment detected - starting health check server...")
            import threading
            from http.server import HTTPServer, BaseHTTPRequestHandler
            
            class HealthCheckHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'Bot is running!')
            
            def run_health_check():
                server = HTTPServer((railway_config['host'], railway_config['port']), HealthCheckHandler)
                server.serve_forever()
            
            # Start health check server in a separate thread
            health_check_thread = threading.Thread(target=run_health_check)
            health_check_thread.daemon = True
            health_check_thread.start()
            print("Health check server started")
        
        print("Starting Discord bot...")
        # Run the bot
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"\n❌ ERROR: Failed to run bot: {e}")
        logger.error(f"Failed to run bot: {e}")
        raise

if __name__ == "__main__":
    print("\n=== Goose Tour Bot ===")
    print("Press Ctrl+C to stop the bot")
    run_bot() 