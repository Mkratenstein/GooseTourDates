"""
Tests for the ConcertComparator class.
"""

import pytest
import json
import csv
from pathlib import Path
from datetime import datetime
from concert_comparator import ConcertComparator
import time
from goose_scraper import GooseTourScraper

@pytest.fixture
def temp_data_dir(tmp_path):
    print("[TEST] Creating temporary data directory...")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir

@pytest.fixture
def comparator(temp_data_dir):
    print("[TEST] Initializing ConcertComparator fixture...")
    return ConcertComparator(str(temp_data_dir))

@pytest.fixture
def sample_concerts():
    print("[TEST] Creating sample concert data...")
    return [
        {
            "event_id": "abc123",
            "start_date": "2024-03-15",
            "end_date": "2024-03-15",
            "venue": "Test Venue 1",
            "location": "Test City, ST",
            "ticket_link": "https://tickets.com/1",
            "vip_link": None,
            "additional_info": []
        },
        {
            "event_id": "def456",
            "start_date": "2024-03-16",
            "end_date": "2024-03-16",
            "venue": "Test Venue 2",
            "location": "Test City, ST",
            "ticket_link": "https://tickets.com/2",
            "vip_link": "https://tickets.com/2/vip",
            "additional_info": ["VIP Available"]
        }
    ]

@pytest.fixture
def scraper():
    return GooseTourScraper()

def test_init_creates_new_concerts_dir(temp_data_dir):
    print("[TEST] Running test_init_creates_new_concerts_dir...")
    comparator = ConcertComparator(str(temp_data_dir))
    new_concerts_dir = temp_data_dir / "new_concerts"
    assert new_concerts_dir.exists()
    assert new_concerts_dir.is_dir()

def test_load_previous_concerts_empty(comparator):
    print("[TEST] Running test_load_previous_concerts_empty...")
    concerts = comparator.load_previous_concerts()
    assert concerts == []

def test_load_previous_concerts(comparator, sample_concerts):
    print("[TEST] Running test_load_previous_concerts...")
    # Create a previous concerts file
    json_path = comparator.data_dir / "tour_dates_20240315.json"
    with open(json_path, 'w') as f:
        json.dump(sample_concerts, f)
    loaded_concerts = comparator.load_previous_concerts()
    assert loaded_concerts == sample_concerts

def test_find_new_concerts(comparator, sample_concerts):
    print("[TEST] Running test_find_new_concerts...")
    previous_concerts = sample_concerts
    current_concerts = sample_concerts + [
        {
            "event_id": "ghi789",
            "start_date": "2024-03-17",
            "end_date": "2024-03-17",
            "venue": "Test Venue 3",
            "location": "Test City, ST",
            "ticket_link": "https://tickets.com/3",
            "vip_link": None,
            "additional_info": []
        }
    ]
    new_concerts = comparator.find_new_concerts(current_concerts, previous_concerts)
    assert len(new_concerts) == 1
    assert new_concerts[0]["event_id"] == "ghi789"

def test_save_new_concerts(comparator, sample_concerts):
    print("[TEST] Running test_save_new_concerts...")
    timestamp = "20240315_120000"
    comparator.save_new_concerts(sample_concerts, timestamp)
    # Check JSON file
    json_path = comparator.new_concerts_dir / f"new_concerts_{timestamp}.json"
    assert json_path.exists()
    with open(json_path, 'r') as f:
        saved_json = json.load(f)
    assert saved_json == sample_concerts
    # Check CSV file
    csv_path = comparator.new_concerts_dir / f"new_concerts_{timestamp}.csv"
    assert csv_path.exists()
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        saved_csv = list(reader)
    assert len(saved_csv) == len(sample_concerts)
    assert saved_csv[0]["event_id"] == sample_concerts[0]["event_id"]

def test_process_new_concerts(comparator, sample_concerts, scraper):
    print("[TEST] Running test_process_new_concerts...")
    print(f"[DEBUG] Data directory: {comparator.data_dir}")
    print(f"[DEBUG] New concerts directory: {comparator.new_concerts_dir}")
    # Create previous concerts file with real event IDs
    prev_concerts = []
    for concert in sample_concerts[:1]:
        date = datetime.fromisoformat(concert['start_date'])
        event_id = scraper.generate_event_id(date, concert['venue'])
        prev_concerts.append({**concert, 'event_id': event_id})
        print(f"[DEBUG] Previous concert event_id: {event_id}")
    prev_json_path = comparator.data_dir / "tour_dates_20240315.json"
    print(f"[DEBUG] Previous JSON path: {prev_json_path}")
    with open(prev_json_path, 'w') as f:
        json.dump(prev_concerts, f)
    time.sleep(1)  # Ensure the next file has a newer mtime
    # Create current concerts file with real event IDs
    current_concerts = []
    for concert in sample_concerts:
        date = datetime.fromisoformat(concert['start_date'])
        event_id = scraper.generate_event_id(date, concert['venue'])
        current_concerts.append({**concert, 'event_id': event_id})
        print(f"[DEBUG] Current concert event_id: {event_id}")
    current_json_path = comparator.data_dir / "tour_dates_20240316.json"
    print(f"[DEBUG] Current JSON path: {current_json_path}")
    with open(current_json_path, 'w') as f:
        json.dump(current_concerts, f)
    new_concerts = comparator.process_new_concerts(str(current_json_path))
    print(f"[DEBUG] Found {len(new_concerts)} new concerts")
    if new_concerts:
        print(f"[DEBUG] New concert event_id: {new_concerts[0]['event_id']}")
    assert len(new_concerts) == 1
    assert new_concerts[0]["event_id"] == current_concerts[1]["event_id"]
    # Check that files were created
    new_concerts_files = list(comparator.new_concerts_dir.glob("new_concerts_*.json"))
    assert len(new_concerts_files) == 1

def test_no_new_concerts(comparator, sample_concerts, scraper):
    print("[TEST] Running test_no_new_concerts...")
    print(f"[DEBUG] Data directory: {comparator.data_dir}")
    print(f"[DEBUG] New concerts directory: {comparator.new_concerts_dir}")
    # Create previous concerts file with real event IDs
    prev_concerts = []
    for concert in sample_concerts:
        date = datetime.fromisoformat(concert['start_date'])
        event_id = scraper.generate_event_id(date, concert['venue'])
        prev_concerts.append({**concert, 'event_id': event_id})
        print(f"[DEBUG] Previous concert event_id: {event_id}")
    prev_json_path = comparator.data_dir / "tour_dates_20240315.json"
    print(f"[DEBUG] Previous JSON path: {prev_json_path}")
    with open(prev_json_path, 'w') as f:
        json.dump(prev_concerts, f)
    time.sleep(1)  # Ensure the next file has a newer mtime
    # Create current concerts file with the same concerts (no new concerts)
    current_json_path = comparator.data_dir / "tour_dates_20240316.json"
    print(f"[DEBUG] Current JSON path: {current_json_path}")
    with open(current_json_path, 'w') as f:
        json.dump(prev_concerts, f)
    new_concerts = comparator.process_new_concerts(str(current_json_path))
    print(f"[DEBUG] Found {len(new_concerts)} new concerts")
    assert len(new_concerts) == 0
    # Check that no new concert files were created
    new_concerts_files = list(comparator.new_concerts_dir.glob("new_concerts_*.json"))
    assert len(new_concerts_files) == 0 