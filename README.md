# Goose Tour Dates Discord Bot

A Discord bot that scrapes and displays upcoming tour dates for the band Goose using slash commands.

## Features

- `/tourdates` slash command to fetch and display upcoming tour dates
- Role-based permission system for command access
- Automatic formatting of dates and event information
- Handles multi-day events and festivals
- Ephemeral responses (only visible to command user)
- Automatic message splitting for long responses
- Retry mechanism for failed scraping attempts

## Prerequisites

- Python 3.12 or higher
- Chrome browser
- ChromeDriver
- Discord Bot Token
- Required Discord roles

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env`:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ALLOWED_ROLE_IDS=role_id_1,role_id_2
   ```

4. Set up Chrome and ChromeDriver:
   - Install Chrome browser
   - Download and install ChromeDriver matching your Chrome version
   - Set environment variables for Chrome paths:
     ```
     CHROME_BIN=/path/to/chrome
     CHROMEDRIVER_PATH=/path/to/chromedriver
     ```

## Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t goose-tour-dates-bot .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --env-file .env \
     --name goose-tour-dates-bot \
     goose-tour-dates-bot
   ```

## Configuration

### Environment Variables

- `DISCORD_TOKEN`: Your Discord bot token
- `ALLOWED_ROLE_IDS`: Comma-separated list of Discord role IDs that can use the command
- `CHROME_BIN`: Path to Chrome browser (default: /usr/bin/google-chrome)
- `CHROMEDRIVER_PATH`: Path to ChromeDriver (default: /usr/local/bin/chromedriver)

### Discord Setup

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot and get the token
3. Enable required intents:
   - Message Content Intent
4. Invite the bot to your server with required permissions:
   - Send Messages
   - Read Messages/View Channels
   - Use Slash Commands

## Usage

1. Start the bot
2. Use the `/tourdates` command in any channel where the bot has access
3. Only users with the specified roles can use the command
4. The bot will respond with formatted tour dates

## Error Handling

- The bot includes retry mechanisms for failed scraping attempts
- Failed commands show ephemeral error messages
- Detailed logging is available in `goose_tour_dates.log`

## Security

- Role-based access control for commands
- Ephemeral responses to prevent channel spam
- Environment variable configuration for sensitive data
- Secure handling of Discord tokens

## Maintenance

- Regular updates to Chrome and ChromeDriver may be required
- Monitor the log file for any issues
- Update role IDs in the environment variables as needed

## Support

For issues or questions, please contact the server administrators or create an issue in the repository. 