# Goose Tour Dates Discord Bot

A Discord bot that provides information about upcoming Goose concert tour dates. The bot scrapes tour information from Goose's official website and provides it through Discord slash commands.

## Features

- `/tourdates` command to view upcoming tour dates
- Optional month filtering for tour dates
- Automatic caching of tour data (24-hour cache)
- Role-based access control
- Robust error handling and connection management
- Automatic reconnection on disconnection
- Rate limit handling for Discord API

## Prerequisites

- Python 3.12 or higher
- Discord Bot Token
- Chrome/Chromium browser (for web scraping)
- ChromeDriver (matching Chrome version)

## Environment Variables

Create a `.env` file with the following variables:

```env
DISCORD_TOKEN=your_discord_bot_token
CHANNEL_ID=your_channel_id
ANNOUNCEMENTS_CHANNEL_ID=your_announcements_channel_id
ALLOWED_ROLE_IDS=role_id1,role_id2

# Chrome Configuration
CHROME_BIN=/usr/bin/google-chrome
CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Python Configuration
PYTHONUNBUFFERED=1
PYTHONIOENCODING=utf-8

# Data Directory
RAILWAY_DATA_DIR=/data
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/goose-tour-dates-bot.git
cd goose-tour-dates-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables in `.env`

4. Run the bot:
```bash
python discord_bot.py
```

## Docker Deployment

1. Build the Docker image:
```bash
docker build -t goose-tour-dates-bot .
```

2. Run the container:
```bash
docker run -d \
  --name goose-tour-dates-bot \
  --env-file .env \
  goose-tour-dates-bot
```

## Railway Deployment

1. Push your code to GitHub
2. Connect your repository to Railway
3. Set up the environment variables in Railway
4. Deploy using the provided Dockerfile

## Usage

### Commands

- `/tourdates` - Get all upcoming tour dates
- `/tourdates [month]` - Get tour dates for a specific month

### Permissions

Users must have one of the following roles to use the bot:
- Goose Tour Dates
- Goose Tour Dates Admin

## Error Handling

The bot includes comprehensive error handling for:
- Discord API rate limits
- Connection issues
- Web scraping failures
- Invalid user input
- Permission issues

## Logging

Logs are written to `goose_tour_dates.log` and include:
- Bot startup and shutdown
- Command usage
- Error messages
- Cache operations
- Scraping operations

## Cache System

- Tour dates are cached for 24 hours
- Cache is stored in `data/tour_dates_cache.json`
- Cache is automatically refreshed when expired
- Initial scrape occurs on bot startup

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Goose for providing tour information
- Discord.py for the Discord API wrapper
- Selenium for web scraping capabilities