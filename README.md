# Goose Concerts Bot

A Discord bot that tracks and announces Goose concert tour dates. The bot provides real-time updates about new shows and allows users to query upcoming tour dates by month.

## Features

- **Tour Date Tracking**: Automatically monitors Goose's tour page for new shows
- **Smart Caching System**: 
  - Updates every hour during business hours (10 AM - 5 PM ET, weekdays)
  - Updates every 4 hours during off-hours (5 PM - 10 AM ET and weekends)
  - Reduces load on the website while maintaining data freshness
- **Discord Commands**:
  - `/tourdates`: Shows all available months with tour dates
  - `/tourdates [month]`: Shows all tour dates for a specific month
- **Event Announcements**: Automatically announces new shows in a designated channel
- **Ticket Link Filtering**: Automatically filters out VIP and Package tickets
- **Role-Based Access**: Only users with specific roles can use the bot commands

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   DISCORD_TOKEN=your_discord_token
   CHANNEL_ID=your_channel_id
   ANNOUNCEMENTS_CHANNEL_ID=your_announcements_channel_id
   ALLOWED_ROLE_IDS=role_id1,role_id2
   ```

## Docker Deployment

The bot can be deployed using Docker:

```bash
docker build -t goose-concerts-bot .
docker run -d --env-file .env goose-concerts-bot
```

## Cache System

The bot implements a smart caching system that adapts to the time of day:

- **Business Hours (10 AM - 5 PM ET, weekdays)**:
  - Cache expires every hour
  - More frequent updates to catch new shows quickly
  - Ideal for peak announcement times

- **Off Hours (5 PM - 10 AM ET and weekends)**:
  - Cache expires every 4 hours
  - Reduced load on the website
  - Still maintains reasonable data freshness

## Event Monitoring

The bot checks for new events:
- Every 30 minutes during business hours
- Every hour during off-hours
- Automatically announces new shows in the designated announcements channel

## Output Format

Tour dates are displayed in a clean, readable format:
```
**September 17, 2025**
Kohl Center | Madison, WI
*Goose & Mt. Joy*
🎫 https://ticket-link.com
```

## Dependencies

- discord.py: Discord API interaction
- selenium: Web scraping
- python-dotenv: Environment variable management
- pytz: Timezone handling
- pandas: Data processing
- aiohttp: Async HTTP client
- python-dateutil: Date handling

## Error Handling

The bot includes comprehensive error handling for:
- Network issues
- Website changes
- Rate limiting
- Invalid dates
- Missing data
- Permission issues

## Logging

All operations are logged to `goose_tour_dates.log` for monitoring and debugging.

## Contributing

Feel free to submit issues and enhancement requests!