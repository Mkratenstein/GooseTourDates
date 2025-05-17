# Goose Tour Dates Scraper

A Python-based web scraper that monitors Goose's tour dates and notifies users of new concerts. The project includes a Discord bot for notifications and manual control.

## Features

- **Automated Scraping**: Monitors Goose's tour dates every 6 hours
- **New Concert Detection**: Identifies and notifies about new tour dates
- **Discord Bot**: 
  - `/status` - Check bot and system status
  - `/scrape` - Manually trigger scraper
  - `/restart` - Restart the bot
- **Logging System**: Comprehensive logging with daily rotation
- **Test Suite**: Automated tests for all components
- **Error Handling**: Robust error handling and reporting

## Project Structure

```
GooseTourDates/
├── scraper/                 # Core scraping and comparison logic
│   ├── goose_scraper.py     # Main scraping implementation
│   ├── concert_comparator.py # New concert detection
│   ├── reporting.py         # Logging and reporting
│   ├── discord_bot.py       # Discord bot implementation
│   ├── scheduler.py         # Automated scheduling
│   └── test_*.py           # Test files
├── data/                    # Data storage
│   ├── scraped_concerts/    # Raw scraped data
│   └── new_concerts/        # Newly detected concerts
├── logs/                    # Application logs
│   └── archive/            # Rotated log files
└── .env                    # Environment variables (not in repo)
```

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Mkratenstein/GooseTourDates.git
   cd GooseTourDates
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create required directories**:
   ```bash
   mkdir -p data/scraped_concerts data/new_concerts logs/archive
   ```

5. **Set up environment variables**:
   Create a `.env` file with:
   ```
   DISCORD_TOKEN=your_bot_token
   DISCORD_CHANNEL_ID=your_channel_id
   AUTHORIZED_USER_ID=your_user_id
   BOT_APPLICATION_ID=your_app_id
   DISCORD_GUILD_ID=your_guild_id
   ```

## Usage

### Running the Discord Bot

1. **Start the bot**:
   ```bash
   python scraper/discord_bot.py
   ```

2. **Available Commands**:
   - `/status` - View bot and system status
   - `/scrape` - Manually trigger the scraper
   - `/restart` - Restart the bot

### Running the Scraper

1. **Continuous Mode** (runs every 6 hours):
   ```bash
   python -m scraper.scheduler
   ```

2. **One-time Run**:
   ```bash
   python -m scraper.scheduler --once
   ```

3. **Test Mode** (uses existing files):
   ```bash
   python -m scraper.scheduler --test
   ```

### Running Tests

```bash
pytest scraper/test_*.py -v
```

### Log Rotation

The system implements daily log rotation with:
- Logs stored in `logs/` directory
- Daily rotation at midnight
- 30-day retention period
- Archived logs in `logs/archive/`

## File Management

- **Scraped Data**: Stored in `data/scraped_concerts/`
  - JSON and CSV formats
  - Keeps 2 most recent files
  - Automatically cleaned up

- **New Concerts**: Stored in `data/new_concerts/`
  - JSON and CSV formats
  - Timestamped files
  - Retained for history

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with Python 3.8+
- Uses Selenium for web scraping
- Implements schedule for automation
- Uses pytest for testing
- Discord.py for bot functionality 