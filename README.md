# Goose Tour Dates Discord Bot

A Discord bot that scrapes and displays upcoming tour dates for the band Goose. The bot provides tour information in a clean, organized format with proper message length handling and error recovery.

## Features

- Scrapes tour dates from Goose's official website
- Groups dates by month for better readability
- Handles Discord message length limits automatically
- Includes venue information, ticket links, and additional details
- Role-based access control
- Automatic reconnection handling
- Comprehensive error logging

## Project Structure

The project is split into three main Python files:

- `scraper.py`: Handles web scraping functionality using Selenium
- `data_processor.py`: Processes and formats the scraped data
- `discord_bot.py`: Manages Discord bot functionality and message handling

## Prerequisites

- Python 3.12 or higher
- Chrome browser
- ChromeDriver
- Discord Bot Token
- Required Python packages (listed in requirements.txt)

## Environment Variables

Create a `.env` file with the following variables:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here
ALLOWED_ROLE_IDS=role_id_1,role_id_2

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

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up Chrome and ChromeDriver:
   - Install Chrome browser
   - Download and install ChromeDriver matching your Chrome version
   - Update the Chrome paths in your `.env` file if different from defaults

## Local Development

Run the bot locally:
```bash
python discord_bot.py
```

## Docker Deployment

The project includes a Dockerfile for containerized deployment:

1. Build the Docker image:
   ```bash
   docker build -t goose-tour-bot .
   ```

2. Run the container:
   ```bash
   docker run -d --env-file .env goose-tour-bot
   ```

## Railway Deployment

The project is configured for deployment on Railway:

1. Connect your GitHub repository to Railway
2. Set up the environment variables in Railway's dashboard
3. Deploy using the provided Dockerfile

## Usage

The bot provides a slash command `/tourdates` that:
- Requires specific Discord roles to use
- Returns tour dates grouped by month
- Handles long messages by splitting them appropriately
- Provides venue information and ticket links
- Includes additional details when available

## Error Handling

The bot includes comprehensive error handling for:
- Connection issues
- Message length limits
- Web scraping failures
- Role permission issues
- Chrome/ChromeDriver problems

## Logging

Logs are written to `goose_tour_dates.log` with timestamps and log levels for debugging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.