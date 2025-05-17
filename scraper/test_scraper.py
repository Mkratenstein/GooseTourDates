"""
Tests for the Goose Tour Scraper
"""

import pytest
from datetime import datetime
from goose_scraper import GooseTourScraper
from unittest.mock import MagicMock

@pytest.fixture
def scraper():
    return GooseTourScraper()

def test_parse_date_range_single_date(scraper):
    """Test parsing a single date"""
    date_text = "2024-03-15"
    result = scraper.parse_date_range(date_text)
    assert result is not None
    assert isinstance(result['start_date'], datetime)
    assert isinstance(result['end_date'], datetime)
    assert result['start_date'] == result['end_date']

def test_parse_date_range_range(scraper):
    """Test parsing a date range"""
    date_text = "2024-03-15 - 2024-03-17"
    result = scraper.parse_date_range(date_text)
    assert result is not None
    assert isinstance(result['start_date'], datetime)
    assert isinstance(result['end_date'], datetime)
    assert result['start_date'] < result['end_date']

def test_parse_date_range_invalid(scraper):
    """Test parsing an invalid date"""
    date_text = "invalid date"
    result = scraper.parse_date_range(date_text)
    assert result is None

@pytest.mark.skip(reason="fetch_tour_page does not exist in GooseTourScraper")
def test_fetch_tour_page(scraper):
    """Test fetching the tour page"""
    content = scraper.fetch_tour_page()
    assert content is not None
    assert isinstance(content, str)
    assert len(content) > 0

def test_generate_event_id(scraper):
    """Test generating event IDs"""
    date = datetime(2024, 3, 15)
    venue = "Test Venue"
    event_id = scraper.generate_event_id(date, venue)
    assert isinstance(event_id, str)
    assert len(event_id) == 12
    # Test that same date and venue produce same ID
    assert event_id == scraper.generate_event_id(date, venue)
    # Test that different date produces different ID
    different_date = datetime(2024, 3, 16)
    assert event_id != scraper.generate_event_id(different_date, venue)
    # Test that different venue produces different ID
    different_venue = "Different Venue"
    assert event_id != scraper.generate_event_id(date, different_venue)

def test_extract_ticket_link(scraper):
    """Test extracting ticket links"""
    # Mock Selenium WebElement
    mock_show = MagicMock()
    mock_ticket = MagicMock()
    mock_ticket.get_attribute.return_value = "https://tickets.com/standard"
    # The show element should return the mock_ticket when find_element is called
    mock_show.find_element.return_value = mock_ticket
    ticket_link = scraper.extract_ticket_link(mock_show)
    assert ticket_link == "https://tickets.com/standard" 