"""Client for interacting with Microsoft Update Catalog."""

import re
from datetime import datetime
from typing import Iterator, Optional

import requests
from bs4 import BeautifulSoup

from .models import WindowsUpdate


class UpdateCatalogClient:
    """Client for searching and downloading from Microsoft Update Catalog."""

    BASE_URL = "https://www.catalog.update.microsoft.com"
    SEARCH_URL = f"{BASE_URL}/Search.aspx"
    DOWNLOAD_URL = f"{BASE_URL}/DownloadDialog.aspx"

    def __init__(self, session: Optional[requests.Session] = None):
        """Initialize the catalog client.

        Args:
            session: Optional requests session for connection pooling
        """
        self.session = session or requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def search(
        self,
        kb: Optional[str] = None,
        query: Optional[str] = None,
        os_filter: Optional[str] = None,
        arch_filter: Optional[str] = None,
    ) -> Iterator[WindowsUpdate]:
        """Search for updates in the Microsoft Update Catalog.

        Args:
            kb: KB number to search for (e.g., 'KB5034441' or '5034441')
            query: Free-text search query
            os_filter: OS filter (e.g., 'Windows 10', 'Windows Server 2022')
            arch_filter: Architecture filter (e.g., 'x64', 'x86', 'ARM64')

        Yields:
            WindowsUpdate objects matching the search criteria
        """
        # Construct search query
        search_query = self._build_search_query(kb, query, os_filter, arch_filter)

        # Perform search
        params = {"q": search_query}
        response = self.session.get(self.SEARCH_URL, params=params)
        response.raise_for_status()

        # Parse results
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the results table
        results_table = soup.find("table", {"id": "ctl00_catalogBody_updateMatches"})
        if not results_table:
            return

        # Parse each row
        for row in results_table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            # Extract update data
            update = self._parse_update_row(cells)
            if update and self._matches_filters(update, os_filter, arch_filter):
                yield update

    def _build_search_query(
        self,
        kb: Optional[str],
        query: Optional[str],
        os_filter: Optional[str],
        arch_filter: Optional[str],
    ) -> str:
        """Build search query string."""
        parts = []

        if kb:
            # Normalize KB number
            kb_normalized = kb.upper()
            if not kb_normalized.startswith("KB"):
                kb_normalized = f"KB{kb_normalized}"
            parts.append(kb_normalized)

        if query:
            parts.append(query)

        if os_filter and not any(os_filter.lower() in p.lower() for p in parts):
            parts.append(os_filter)

        if arch_filter and not any(arch_filter.lower() in p.lower() for p in parts):
            parts.append(arch_filter)

        return " ".join(parts) if parts else ""

    def _parse_update_row(self, cells: list) -> Optional[WindowsUpdate]:
        """Parse a table row into a WindowsUpdate object."""
        try:
            # Extract title and KB
            title_cell = cells[1]
            title = title_cell.get_text(strip=True)

            # Extract KB number from title or ID
            kb_match = re.search(r"KB\d+", title, re.IGNORECASE)
            kb = kb_match.group(0) if kb_match else None

            # Extract products
            products = cells[2].get_text(strip=True)

            # Extract classification
            classification = cells[3].get_text(strip=True)

            # Extract date
            date_str = cells[4].get_text(strip=True)
            last_updated = datetime.strptime(date_str, "%m/%d/%Y")

            # Extract version
            version = cells[5].get_text(strip=True) or None

            # Extract size
            size = cells[6].get_text(strip=True)

            # Extract update ID from the input element
            input_elem = cells[0].find("input")
            update_id = input_elem.get("id", "").replace("_checkbox", "") if input_elem else ""

            # Try to extract architecture from title
            arch = self._extract_architecture(title)

            return WindowsUpdate(
                title=title,
                kb=kb,
                products=products,
                classification=classification,
                last_updated=last_updated,
                version=version,
                size=size,
                update_id=update_id,
                architecture=arch,
            )
        except (IndexError, ValueError, AttributeError):
            return None

    def _extract_architecture(self, title: str) -> Optional[str]:
        """Extract architecture from update title."""
        title_lower = title.lower()
        if "x64" in title_lower or "amd64" in title_lower:
            return "x64"
        if "arm64" in title_lower:
            return "ARM64"
        if "x86" in title_lower or "32-bit" in title_lower:
            return "x86"
        return None

    def _matches_filters(
        self,
        update: WindowsUpdate,
        os_filter: Optional[str],
        arch_filter: Optional[str],
    ) -> bool:
        """Check if update matches the specified filters."""
        if os_filter and os_filter.lower() not in update.products.lower():
            return False

        if arch_filter and update.architecture:
            if arch_filter.lower() != update.architecture.lower():
                return False

        return True

    def get_download_url(self, update_id: str) -> Optional[str]:
        """Get the download URL for a specific update.

        Args:
            update_id: The update ID from the catalog

        Returns:
            Download URL or None if not found
        """
        # Post request to get download dialog
        response = self.session.post(
            self.DOWNLOAD_URL,
            data={"updateIDs": f'[{{"size":0,"updateID":"{update_id}","uidInfo":"{update_id}"}}]'},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        # Extract download URL using regex
        # Pattern matches URLs from various Microsoft download domains
        url_pattern = r"https?://[a-zA-Z0-9\-\.]+\.?(download\.)?windowsupdate\.com/[^\s'\"]+"
        matches = re.findall(url_pattern, response.text)

        if matches:
            return matches[0]

        return None

    def download_update(
        self,
        update: WindowsUpdate,
        output_path: str,
        progress_callback: Optional[callable] = None,
    ) -> str:
        """Download an update file.

        Args:
            update: The WindowsUpdate to download
            output_path: Path to save the downloaded file
            progress_callback: Optional callback for progress updates

        Returns:
            Path to the downloaded file
        """
        # Get download URL if not already set
        if not update.download_url:
            update.download_url = self.get_download_url(update.update_id)

        if not update.download_url:
            raise ValueError(f"No download URL found for update {update.update_id}")

        # Download the file
        response = self.session.get(update.download_url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

        return output_path
