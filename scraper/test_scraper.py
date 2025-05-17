"""
Tests for the Goose Tour Scraper
"""

import pytest
from datetime import datetime
from goose_scraper import GooseTourScraper

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

def test_fetch_tour_page(scraper):
    """Test fetching the tour page"""
    content = scraper.fetch_tour_page()
    assert content is not None
    assert isinstance(content, str)
    assert len(content) > 0

def test_extract_ticket_link(scraper):
    """Test extracting ticket links"""
    from bs4 import BeautifulSoup
    
    # Test HTML with standard and VIP links
    html = """
    <div class="show">
        <a href="https://tickets.com/standard">Standard Tickets</a>
        <a href="https://tickets.com/vip">VIP Tickets</a>
    </div>
    """
    soup = BeautifulSoup(html, 'html.parser')
    show_element = soup.find('div', class_='show')
    
    ticket_link = scraper.extract_ticket_link(show_element)
    assert ticket_link == "https://tickets.com/standard" 