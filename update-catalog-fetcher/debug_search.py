"""Debug script to inspect catalog HTML structure."""

import requests
from bs4 import BeautifulSoup

# Search for KB5066835
search_url = "https://www.catalog.update.microsoft.com/Search.aspx"
params = {"q": "KB5066835 Windows 11 x64"}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

response = session.get(search_url, params=params)
soup = BeautifulSoup(response.text, "html.parser")

# Find the results table
results_table = soup.find("table", {"id": "ctl00_catalogBody_updateMatches"})

if not results_table:
    print("Results table not found!")
    print("\nSearching for any table with 'update' in ID:")
    for table in soup.find_all("table"):
        table_id = table.get("id", "")
        if "update" in table_id.lower():
            print(f"Found table: {table_id}")
else:
    print("Results table found!")

    # Look at first few rows
    rows = results_table.find_all("tr")
    print(f"\nFound {len(rows)} rows")

    for i, row in enumerate(rows[:3]):
        print(f"\n--- Row {i} ---")
        cells = row.find_all("td")
        print(f"Number of cells: {len(cells)}")

        if len(cells) >= 1:
            # Look at first cell for checkbox/input
            first_cell = cells[0]
            print(f"\nFirst cell HTML: {first_cell.prettify()[:500]}")

            input_elem = first_cell.find("input")
            if input_elem:
                print("Input found!")
                print(f"  ID: {input_elem.get('id')}")
                print(f"  Value: {input_elem.get('value')}")
                print(f"  Type: {input_elem.get('type')}")
