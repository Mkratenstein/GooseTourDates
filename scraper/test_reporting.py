"""Test cases for the reporting module."""

import pytest
from datetime import datetime
from pathlib import Path
from reporting import ScraperReporter

@pytest.fixture
def reporter():
    print("[TEST] Initializing ScraperReporter fixture...")
    return ScraperReporter(data_dir="test_data", log_dir="test_logs")

@pytest.fixture
def sample_shows():
    print("[TEST] Creating sample show data...")
    return [
        {
            "event_id": "test123",
            "start_date": "2025-05-23T00:00:00",
            "end_date": "2025-05-25T00:00:00",
            "venue": "BottleRock Napa Valley",
            "location": "Napa, CA",
            "ticket_link": "https://example.com/tickets1",
            "vip_link": None,
            "additional_info": ["Festival"]
        },
        {
            "event_id": "test456",
            "start_date": "2025-05-27T00:00:00",
            "end_date": "2025-05-27T00:00:00",
            "venue": "The Masonic",
            "location": "San Francisco, CA",
            "ticket_link": "https://example.com/tickets2",
            "vip_link": "https://example.com/vip2",
            "additional_info": ["VIP Available"]
        }
    ]

def test_monthly_stats_calculation(reporter, sample_shows):
    print("[TEST] Running test_monthly_stats_calculation...")
    stats = reporter._calculate_monthly_stats(sample_shows)
    assert isinstance(stats, dict)
    assert 'labels' in stats
    assert 'values' in stats
    assert len(stats['labels']) == 1  # All shows in May 2025
    assert stats['labels'][0] == '2025-05'
    assert stats['values'][0] == 2  # Two shows in May 2025

def test_venue_stats_calculation(reporter, sample_shows):
    print("[TEST] Running test_venue_stats_calculation...")
    stats = reporter._calculate_venue_stats(sample_shows)
    assert isinstance(stats, dict)
    assert 'total_venues' in stats
    assert 'venue_counts' in stats
    assert 'most_common_venue' in stats
    assert stats['total_venues'] == 2
    assert len(stats['venue_counts']) == 2
    assert stats['venue_counts']['BottleRock Napa Valley'] == 1
    assert stats['venue_counts']['The Masonic'] == 1

def test_date_range_calculation(reporter, sample_shows):
    print("[TEST] Running test_date_range_calculation...")
    date_range = reporter._calculate_date_range(sample_shows)
    assert isinstance(date_range, dict)
    assert 'start' in date_range
    assert 'end' in date_range
    assert 'days' in date_range
    assert date_range['start'] == '2025-05-23'
    assert date_range['end'] == '2025-05-27'
    assert date_range['days'] == 5

def test_venue_location_geocoding(reporter):
    print("[TEST] Running test_venue_location_geocoding...")
    location = reporter._get_venue_location(
        "The Masonic",
        "San Francisco, CA"
    )
    assert isinstance(location, dict)
    assert 'venue' in location
    assert 'lat' in location
    assert 'lng' in location
    assert 'shows' in location
    assert location['venue'] == "The Masonic"
    assert isinstance(location['lat'], float)
    assert isinstance(location['lng'], float)
    assert location['shows'] == 1

def test_venue_locations_calculation(reporter, sample_shows):
    print("[TEST] Running test_venue_locations_calculation...")
    # Mock the _get_venue_location method to always return a unique location
    def mock_get_venue_location(venue, location):
        if venue == "BottleRock Napa Valley":
            return {'venue': venue, 'lat': 38.2975, 'lng': -122.2869, 'shows': 1}
        elif venue == "The Masonic":
            return {'venue': venue, 'lat': 37.7912, 'lng': -122.4129, 'shows': 1}
        return None
    reporter._get_venue_location = mock_get_venue_location
    locations = reporter._calculate_venue_locations(sample_shows)
    assert isinstance(locations, list)
    assert len(locations) == 2  # Two unique venues
    for location in locations:
        assert isinstance(location, dict)
        assert 'venue' in location
        assert 'lat' in location
        assert 'lng' in location
        assert 'shows' in location
        assert isinstance(location['shows'], int)

def test_html_report_generation(reporter, sample_shows, tmp_path):
    print("[TEST] Running test_html_report_generation...")
    reporter.data_dir = tmp_path / "data"
    reporter.reports_dir = reporter.data_dir / "reports"
    reporter.data_dir.mkdir(exist_ok=True)
    reporter.reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reporter.generate_html_report(sample_shows, [], timestamp)
    assert report_path.exists()
    content = report_path.read_text()
    assert "Goose Tour Scraper Report" in content
    assert "BottleRock Napa Valley" in content
    assert "The Masonic" in content
    assert "chart.js" in content
    assert "leaflet" in content

def test_console_report_generation(reporter, sample_shows, capsys):
    print("[TEST] Running test_console_report_generation...")
    reporter.generate_console_report(sample_shows, [])
    captured = capsys.readouterr()
    assert "Goose Tour Scraper Report" in captured.out
    assert "Total concerts found: 2" in captured.out
    assert "BottleRock Napa Valley" in captured.out
    assert "The Masonic" in captured.out

def test_error_handling(reporter):
    print("[TEST] Running test_error_handling...")
    location = reporter._get_venue_location("Invalid Venue", "Invalid Location")
    assert location is None
    stats = reporter._calculate_venue_stats([])
    assert stats['total_venues'] == 0
    assert len(stats['venue_counts']) == 0
    assert stats['most_common_venue'] is None
    date_range = reporter._calculate_date_range([])
    assert date_range['start'] is None
    assert date_range['end'] is None
    assert date_range['days'] == 0 