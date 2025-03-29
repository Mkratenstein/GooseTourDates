import os
import time
import logging
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from data_processor import get_formatted_tour_dates, get_tour_dates
import aiohttp
from aiohttp import ClientTimeout
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    force=True
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
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 10
WEBSOCKET_TIMEOUT = 30
CONNECTION_TIMEOUT = ClientTimeout(total=30, connect=10)
MESSAGE_RETRY_DELAY = 2  # Delay between message retries
MESSAGE_SEND_DELAY = 1  # Delay between sending messages to avoid rate limits

# Add connection state tracking
connection_attempts = 0
last_connection_time = 0
is_reconnecting = False
session = None
executor = ThreadPoolExecutor(max_workers=1)  # Single worker for scraping

# Add month validation
VALID_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

async def run_in_executor(func, *args):
    """Run a function in the thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)

async def initial_scrape():
    """Run initial scrape on bot startup."""
    try:
        logger.info("Running initial tour dates scrape...")
        await run_in_executor(get_tour_dates)
        logger.info("Initial scrape completed successfully")
    except Exception as e:
        logger.error(f"Error during initial scrape: {e}")

async def create_session():
    """Create a new aiohttp session with proper timeout settings."""
    return aiohttp.ClientSession(timeout=CONNECTION_TIMEOUT)

async def close_session(session):
    """Safely close an aiohttp session."""
    if not session.closed:
        await session.close()

async def send_message_with_retry(interaction: discord.Interaction, message: str, max_retries: int = 3) -> bool:
    """Send a message with retry logic."""
    for attempt in range(max_retries):
        try:
            if not bot.is_ready():
                logger.warning("Bot not ready, waiting before retry...")
                await asyncio.sleep(MESSAGE_RETRY_DELAY)
                continue
                
            await interaction.followup.send(message, ephemeral=True)
            return True
        except discord.HTTPException as e:
            if e.code == 50035:  # Message too long
                logger.error("Message too long, splitting into chunks...")
                # Split message into lines and send each line
                lines = message.split("\n")
                for line in lines:
                    if not await send_message_with_retry(interaction, line):
                        return False
                return True
            elif e.code == 10008:  # Unknown Channel
                logger.error("Channel not found")
                return False
            elif e.code == 50001:  # Missing Access
                logger.error("Missing permissions")
                return False
            elif e.code == 429:  # Rate limit
                retry_after = e.retry_after
                logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                continue
            else:
                logger.error(f"HTTP Exception: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(MESSAGE_RETRY_DELAY)
                    continue
                return False
        except discord.ConnectionClosed:
            logger.error("Connection closed while sending message")
            if attempt < max_retries - 1:
                await asyncio.sleep(MESSAGE_RETRY_DELAY)
                continue
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(MESSAGE_RETRY_DELAY)
                continue
            return False
    return False

async def send_monthly_messages(interaction: discord.Interaction, messages: list):
    """Send multiple messages, one for each event."""
    try:
        # Send the header message first
        if not await send_message_with_retry(interaction, messages[0]):
            logger.error("Failed to send header message")
            return
        
        # Send each event message with a delay
        for message in messages[1:]:
            if not bot.is_ready():
                logger.warning("Bot disconnected while sending messages")
                await interaction.followup.send(
                    "Connection lost while sending messages. Please try again.",
                    ephemeral=True
                )
                return
            
            # Add a small delay between messages to avoid rate limits
            await asyncio.sleep(MESSAGE_SEND_DELAY)
            
            if not await send_message_with_retry(interaction, message):
                logger.error("Failed to send event message")
                return
                
    except Exception as e:
        logger.error(f"Error sending messages: {e}")
        try:
            if bot.is_ready():
                await interaction.followup.send(
                    "An error occurred while sending the tour dates. Please try again later.",
                    ephemeral=True
                )
        except:
            logger.error("Failed to send error message to user")

async def handle_disconnect():
    """Handle bot disconnection and reconnection."""
    global connection_attempts, is_reconnecting, session
    logger.warning("Bot disconnected from Discord. Attempting to reconnect...")
    
    # Close existing session if it exists
    if session and not session.closed:
        await session.close()
        session = None
    
    for attempt in range(MAX_RECONNECT_ATTEMPTS):
        try:
            connection_attempts += 1
            logger.info(f"Reconnection attempt {attempt + 1}/{MAX_RECONNECT_ATTEMPTS}")
            
            # Close the current session if it exists
            if bot.is_closed():
                logger.info("Bot is already closed, starting fresh...")
            else:
                await bot.close()
            
            # Calculate delay with exponential backoff and jitter
            base_delay = RECONNECT_DELAY * (2 ** attempt)
            jitter = (time.time() % 1) * 2  # Random jitter between 0 and 2 seconds
            delay = base_delay + jitter
            
            logger.info(f"Waiting {delay:.1f} seconds before reconnecting...")
            await asyncio.sleep(delay)
            
            # Start a new session
            token = os.getenv('DISCORD_TOKEN')
            if not token:
                logger.error("No Discord token found in environment variables!")
                return
            
            # Create a new session with proper timeout
            try:
                async with asyncio.timeout(WEBSOCKET_TIMEOUT):
                    await bot.start(token)
                    logger.info("Successfully reconnected to Discord")
                    is_reconnecting = False
                    return
            except asyncio.TimeoutError:
                logger.error("Connection attempt timed out")
                continue
            except aiohttp.ClientConnectionResetError:
                logger.error("Connection reset by peer")
                continue
            except aiohttp.ClientError as e:
                logger.error(f"Connection error: {e}")
                continue
                
        except Exception as e:
            logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RECONNECT_ATTEMPTS - 1:
                delay = RECONNECT_DELAY * (2 ** attempt)
                logger.info(f"Waiting {delay} seconds before next attempt...")
                await asyncio.sleep(delay)
            else:
                logger.error("Failed to reconnect after maximum attempts")
                is_reconnecting = False
                # Try to restart the entire bot
                try:
                    await restart_bot()
                except Exception as restart_error:
                    logger.error(f"Failed to restart bot: {restart_error}")

async def restart_bot():
    """Restart the entire bot process."""
    logger.info("Attempting to restart the bot...")
    try:
        # Close the current session
        if not bot.is_closed():
            await bot.close()
        
        # Wait a moment before restarting
        await asyncio.sleep(RECONNECT_DELAY)
        
        # Get the token
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("No Discord token found in environment variables!")
            return
        
        # Start a new session with timeout
        try:
            async with asyncio.timeout(WEBSOCKET_TIMEOUT):
                await bot.start(token)
                logger.info("Bot successfully restarted")
        except asyncio.TimeoutError:
            logger.error("Bot restart timed out")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Bot restart connection error: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Failed to restart bot: {e}")
        raise

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    global connection_attempts, last_connection_time, session
    connection_attempts = 0
    last_connection_time = time.time()
    
    logger.info(f'Bot is ready! Logged in as {bot.user.name}')
    
    # Configure HTTP session timeout
    try:
        bot.http.connector._timeout = WEBSOCKET_TIMEOUT
        logger.info(f"Set HTTP session timeout to {WEBSOCKET_TIMEOUT} seconds")
    except Exception as e:
        logger.warning(f"Could not set HTTP session timeout: {e}")
    
    # Sync commands with Discord
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    # Set bot's activity to show it's online
    try:
        await bot.change_presence(activity=discord.Game(name="Goose Tour Dates"))
    except Exception as e:
        logger.warning(f"Failed to set bot activity: {e}")
    
    # Run initial scrape
    await initial_scrape()

@bot.event
async def on_disconnect():
    """Called when the bot disconnects from Discord."""
    global is_reconnecting
    if not is_reconnecting:  # Only handle if not already reconnecting
        await handle_disconnect()

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler for the bot."""
    logger.error(f"Error in {event}: {args} {kwargs}")
    if event == 'on_message':
        logger.error(f"Message content: {args[0].content if args else 'No message content'}")
    elif event == 'on_command_error':
        logger.error(f"Command error: {args[0] if args else 'No error details'}")

@bot.tree.command(name="tourdates", description="Get upcoming Goose tour dates. Optionally specify a month to filter results.")
async def tour_dates(interaction: discord.Interaction, month: str = None):
    """Slash command to get tour dates. If no month is specified, shows available months."""
    if is_reconnecting:
        try:
            await interaction.response.send_message(
                "Bot is currently reconnecting. Please try again in a moment.",
                ephemeral=True
            )
        except:
            logger.error("Failed to send reconnecting message")
        return
    
    # Validate month if provided
    if month:
        # Convert month to title case for validation
        month = month.title()
        if month not in VALID_MONTHS:
            try:
                await interaction.response.send_message(
                    f"Invalid month. Please use one of: {', '.join(VALID_MONTHS)}",
                    ephemeral=True
                )
            except:
                logger.error("Failed to send invalid month message")
            return
        
    # Get allowed role IDs from environment variables
    role_ids_str = os.getenv('ALLOWED_ROLE_IDS', '')
    if not role_ids_str:
        logger.error("No allowed role IDs found in environment variables!")
        try:
            await interaction.response.send_message(
                "Configuration error: Allowed roles not set. Please contact an administrator.",
                ephemeral=True
            )
        except:
            logger.error("Failed to send configuration error message")
        return
    
    try:
        # Convert comma-separated string to list of integers
        allowed_roles = [int(role_id.strip()) for role_id in role_ids_str.split(',')]
    except ValueError as e:
        logger.error(f"Error parsing role IDs: {e}")
        try:
            await interaction.response.send_message(
                "Configuration error: Invalid role ID format. Please contact an administrator.",
                ephemeral=True
            )
        except:
            logger.error("Failed to send role ID error message")
        return
    
    # Check if user has required roles
    user_roles = [role.id for role in interaction.user.roles]
    
    if not any(role_id in user_roles for role_id in allowed_roles):
        try:
            await interaction.response.send_message(
                "You don't have permission to use this command. Required roles: Goose Tour Dates, Goose Tour Dates Admin",
                ephemeral=True
            )
        except:
            logger.error("Failed to send permission error message")
        return
    
    try:
        # Only use ephemeral if no month is specified
        await interaction.response.defer(ephemeral=(month is None))
    except:
        logger.error("Failed to defer interaction")
        return
    
    try:
        # Get the tour dates from cache
        messages = get_formatted_tour_dates(month)
        
        # Send the messages
        await send_monthly_messages(interaction, messages)
            
    except Exception as e:
        logger.error(f"Error in tour_dates command: {e}")
        try:
            if bot.is_ready():
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
            # Start the bot
            bot.run(token)
            break
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            logger.info(f"Attempting to restart in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
            
            # If we've hit a critical error, wait longer before retrying
            if "Cannot write to closing transport" in str(e):
                time.sleep(RETRY_DELAY * 2)
            elif "Connection reset" in str(e):
                time.sleep(RETRY_DELAY * 3)
            elif "Timeout" in str(e):
                time.sleep(RETRY_DELAY * 2)

if __name__ == "__main__":
    main() 