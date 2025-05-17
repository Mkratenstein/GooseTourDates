# Goose Tour Dates

A Python-based web scraper that collects tour dates and information from [goosetheband.com/tour](https://goosetheband.com/tour).

## Features

- Scrapes tour dates, venues, locations, and ticket information
- Handles both single-day and multi-day events
- Captures additional information like supporting acts and VIP availability
- Exports data in both CSV and JSON formats
- Uses Selenium for JavaScript-enabled web scraping

## Data Format

The scraper generates two output files in the `data` directory:

### CSV Format (`data/tour_dates.csv`)
- `start_date`: Event start date (YYYY-MM-DD)
- `end_date`: Event end date (YYYY-MM-DD)
- `venue`: Venue name
- `location`: City, State/Province
- `ticket_link`: URL for ticket purchase
- `vip_link`: URL for VIP ticket purchase (if available)
- `additional_info`: Additional show information (e.g., supporting acts)

### JSON Format (`data/tour_dates.json`)
```json
{
  "start_date": "2025-05-23T00:00:00",
  "end_date": "2025-05-25T00:00:00",
  "venue": "BottleRock Napa Valley",
  "location": "Napa, CA",
  "ticket_link": "https://link.seated.com/...",
  "vip_link": null,
  "additional_info": []
}
```

## Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Chrome browser (required for Selenium)

3. Run the scraper:
```bash
python scraper/goose_scraper.py
```

## Project Structure

```
GooseTourDates/
├── data/                  # Output directory for scraped data
│   ├── tour_dates.csv    # CSV format
│   └── tour_dates.json   # JSON format
├── scraper/
│   └── goose_scraper.py  # Main scraper script
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Dependencies

- Python 3.6+
- Selenium
- BeautifulSoup4
- Chrome WebDriver
- dateutil

## License

MIT License 