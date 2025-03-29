# Goose Tour Dates Discord Bot

A Discord bot that monitors and shares Goose concert tour dates from goosetheband.com.

## Features

- Automatically posts tour dates to a specified channel every 24 hours
- Slash command `/tour_dates` to manually fetch tour dates
- Beautiful embed messages with venue and location information

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   CHANNEL_ID=your_discord_channel_id
   ```

## Deployment to Railway

1. Push your code to GitHub
2. Create a new project on Railway
3. Connect your GitHub repository
4. Add the following environment variables in Railway:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `CHANNEL_ID`: The Discord channel ID where tour dates will be posted

## Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section and create a bot
4. Copy the bot token and add it to your environment variables
5. Enable the following bot intents:
   - Message Content Intent
6. Invite the bot to your server with the following permissions:
   - Send Messages
   - Embed Links
   - Use Slash Commands

## Usage

The bot will automatically post tour dates every 24 hours to the specified channel. Users can also use the `/tour_dates` slash command to manually fetch the latest tour dates.

## Contributing

Feel free to submit issues and enhancement requests! 