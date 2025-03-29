# Goose Tour Dates Discord Bot

A Discord bot that provides information about upcoming Goose concert tour dates. The bot scrapes tour information from Goose's official website and provides it through Discord slash commands.

## Features

- `/tourdates` command to view upcoming tour dates
- Filter tour dates by month
- Automatic caching of tour dates to reduce website load
- Daily cache refresh to ensure data accuracy
- Role-based access control
- Resilient error handling and automatic reconnection

## Prerequisites

- Python 3.12 or higher
- Discord Bot Token
- Chrome/Chromium browser (for web scraping)
- ChromeDriver compatible with your Chrome version

## Environment Variables

Create a `.env` file with the following variables:

```env
DISCORD_TOKEN=your_discord_bot_token
CHANNEL_ID=your_channel_id
ANNOUNCEMENTS_CHANNEL_ID=your_announcements_channel_id
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

The project includes a Dockerfile for containerized deployment. To build and run:

```bash
docker build -t goose-tour-dates-bot .
docker run -d --env-file .env goose-tour-dates-bot
```

## Railway Deployment

1. Push your code to GitHub
2. Connect your repository to Railway
3. Add the required environment variables in Railway's dashboard
4. Deploy!

## Usage

The bot provides the following slash command:

- `/tourdates [month]` - Get upcoming tour dates. If no month is specified, shows available months.

## Permissions

Users need one of the following roles to use the bot:
- Goose Tour Dates
- Goose Tour Dates Admin

## Error Handling

The bot includes comprehensive error handling for:
- Network issues
- Website structure changes
- Rate limiting
- Permission issues
- Connection resets

## Logging

Logs are written to both:
- Console output
- `goose_tour_dates.log` file

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Goose](https://www.goosetheband.com/) for providing tour information
- [Discord.py](https://discordpy.readthedocs.io/) for the Discord API wrapper
- [Selenium](https://www.selenium.dev/) for web scraping capabilities