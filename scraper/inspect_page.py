"""
Script to inspect the Goose tour page HTML structure
"""

from goose_scraper import GooseTourScraper
from bs4 import BeautifulSoup
import json

def inspect_page_structure():
    scraper = GooseTourScraper()
    content = scraper.fetch_tour_page()
    
    if not content:
        print("Failed to fetch page content")
        return
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Print all div classes to understand the structure
    print("\nAll div classes found:")
    print("=" * 50)
    div_classes = set()
    for div in soup.find_all('div', class_=True):
        div_classes.update(div.get('class', []))
    print("\n".join(sorted(div_classes)))
    
    # Look for common tour-related terms
    print("\nSearching for tour-related elements:")
    print("=" * 50)
    
    # Search for elements containing tour-related text
    tour_related = soup.find_all(string=lambda text: text and any(term in text.lower() 
        for term in ['tour', 'date', 'venue', 'ticket', 'show']))
    
    for element in tour_related:
        print(f"\nFound element with text: {element.strip()}")
        print(f"Parent tag: {element.parent.name}")
        print(f"Parent classes: {element.parent.get('class', [])}")
        print("-" * 30)
    
    # Look for any table structures
    print("\nChecking for table structures:")
    print("=" * 50)
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables")
    
    if tables:
        print("\nFirst table structure:")
        print(tables[0].prettify())

    # Look for any <script> tags that might contain JSON or data
    print("\nInspecting <script> tags for embedded JSON/data:")
    print("=" * 50)
    scripts = soup.find_all('script')[:10]  # Limit to first 10 script tags
    for idx, script in enumerate(scripts):
        script_content = script.string
        if script_content:
            preview = script_content.strip()[:500]
            print(f"\nScript tag #{idx+1} (first 500 chars):\n{preview}\n---")
            # Highlight if it looks like JSON
            if preview.startswith('{') or preview.startswith('['):
                print("^^^ Possible JSON detected ^^^\n")

if __name__ == "__main__":
    inspect_page_structure() 