# Goose Tour Dates Scraper

A Discord bot that automatically scrapes and posts Goose tour dates to a specified Discord channel.

## Features

- Automated scraping of Goose tour dates
- Discord bot integration for posting new concerts
- Manual trigger of scraper via `/scrape` command
- System status checking via `/status` command
- Comprehensive logging system with rotation
- Error handling and reporting

## Commands

- `/scrape` - Manually trigger the scraper to check for new tour dates
- `/status` - Check the status of the bot and system

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/GooseTourDates.git
cd GooseTourDates
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Unix/MacOS:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with the following variables:
```
DISCORD_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
AUTHORIZED_USER_ID=your_user_id
BOT_APPLICATION_ID=your_application_id
DISCORD_GUILD_ID=your_guild_id
```

5. Run the bot:
```bash
python -m scraper.discord_bot
```

## Logging System

The bot uses a comprehensive logging system that:
- Rotates logs daily
- Keeps logs for 30 days
- Automatically archives old logs
- Maintains separate logs for different components

Log files are stored in `scraper/logs/` and are automatically managed by the logging system.

## Project Structure

```
GooseTourDates/
├── scraper/
│   ├── discord_bot.py      # Discord bot implementation
│   ├── goose_scraper.py    # Web scraping logic
│   ├── concert_comparator.py # Concert comparison logic
│   ├── reporting.py        # Logging and reporting
│   └── logs/              # Log files
├── data/
│   ├── scraped_concerts/  # Scraped concert data
│   └── new_concerts/      # New concert data
├── scripts/
│   └── rotate_logs.ps1    # Log rotation script
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (not in repo)
└── README.md            # This file
```

## Error Handling

The bot includes comprehensive error handling:
- Detailed error logging
- User-friendly error messages
- Automatic retry mechanisms
- Status reporting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 