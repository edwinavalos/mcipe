"""
URL-based recipe scraper using the recipe-scrapers library.

This module handles fetching recipes from URLs using the recipe-scrapers
library which supports 400+ recipe websites including NYT Cooking,
AllRecipes, Food Network, etc.
"""

import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from recipe_scrapers import scrape_html, SCRAPERS

from ..models import Recipe


class ScraperError(Exception):
    """Error during recipe scraping."""

    pass


class URLScraper:
    """
    Scrapes recipes from URLs using the recipe-scrapers library.
    """

    # Custom headers to avoid being blocked
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, timeout: float = 30.0):
        """
        Initialize the scraper.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialized HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def get_supported_sites() -> list[str]:
        """Get list of supported recipe sites."""
        return list(SCRAPERS.keys())

    @staticmethod
    def is_supported_url(url: str) -> bool:
        """Check if a URL is from a supported recipe site."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            # Remove www. prefix
            if host.startswith("www."):
                host = host[4:]
            # Check against supported scrapers
            for scraper_host in SCRAPERS.keys():
                if host == scraper_host or host.endswith(f".{scraper_host}"):
                    return True
            return False
        except Exception:
            return False

    def fetch_html(self, url: str) -> str:
        """
        Fetch HTML content from a URL.

        Args:
            url: The URL to fetch

        Returns:
            The HTML content as a string

        Raises:
            ScraperError: If the fetch fails
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            raise ScraperError(f"HTTP error {e.response.status_code} fetching {url}") from e
        except httpx.RequestError as e:
            raise ScraperError(f"Request error fetching {url}: {e}") from e

    def scrape(self, url: str) -> Recipe:
        """
        Scrape a recipe from a URL.

        Args:
            url: The recipe URL

        Returns:
            A Recipe object with parsed data

        Raises:
            ScraperError: If scraping fails
        """
        try:
            html = self.fetch_html(url)
            return self.scrape_from_html(html, url)
        except ScraperError:
            raise
        except Exception as e:
            raise ScraperError(f"Failed to scrape recipe from {url}: {e}") from e

    def scrape_from_html(self, html: str, url: str) -> Recipe:
        """
        Scrape a recipe from HTML content.

        Args:
            html: The HTML content
            url: The source URL (needed for site detection)

        Returns:
            A Recipe object with parsed data

        Raises:
            ScraperError: If parsing fails
        """
        try:
            scraper = scrape_html(html, org_url=url)
        except Exception as e:
            raise ScraperError(f"Could not parse recipe from {url}: {e}") from e

        # Extract source site from URL
        parsed_url = urlparse(url)
        source_site = parsed_url.netloc
        if source_site.startswith("www."):
            source_site = source_site[4:]

        # Parse times
        prep_time = self._safe_call(scraper.prep_time)
        cook_time = self._safe_call(scraper.cook_time)
        total_time = self._safe_call(scraper.total_time)

        # Parse servings
        servings_text = self._safe_call(scraper.yields)
        servings = self._parse_servings(servings_text)

        # Get ingredients
        ingredients_raw = self._safe_call(scraper.ingredients, default=[])
        if not isinstance(ingredients_raw, list):
            ingredients_raw = []

        # Get instructions
        instructions_raw = self._safe_call(scraper.instructions)
        if isinstance(instructions_raw, str):
            # Split on newlines or numbered steps
            instructions = self._split_instructions(instructions_raw)
        elif isinstance(instructions_raw, list):
            instructions = instructions_raw
        else:
            instructions = []

        return Recipe(
            title=self._safe_call(scraper.title, default="Unknown Recipe"),
            url=url,
            source_site=source_site,
            description=self._safe_call(scraper.description),
            servings=servings,
            servings_text=servings_text,
            prep_time_minutes=prep_time,
            cook_time_minutes=cook_time,
            total_time_minutes=total_time,
            ingredients_raw=ingredients_raw,
            instructions=instructions,
        )

    @staticmethod
    def _safe_call(method, default=None):
        """Safely call a scraper method that might raise or return None."""
        try:
            result = method()
            return result if result is not None else default
        except Exception:
            return default

    @staticmethod
    def _parse_servings(servings_text: Optional[str]) -> Optional[int]:
        """Parse servings text into an integer."""
        if not servings_text:
            return None

        # Try to extract first number
        match = re.search(r"(\d+)", servings_text)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _split_instructions(text: str) -> list[str]:
        """Split instruction text into steps."""
        # Try splitting on numbered steps first
        steps = re.split(r"\n\s*\d+[\.\)]\s*", text)
        if len(steps) > 1:
            return [s.strip() for s in steps if s.strip()]

        # Try splitting on double newlines
        steps = text.split("\n\n")
        if len(steps) > 1:
            return [s.strip() for s in steps if s.strip()]

        # Fall back to single newlines
        steps = text.split("\n")
        return [s.strip() for s in steps if s.strip()]


def scrape_recipe(url: str) -> Recipe:
    """
    Convenience function to scrape a single recipe.

    Args:
        url: The recipe URL

    Returns:
        A Recipe object

    Raises:
        ScraperError: If scraping fails
    """
    with URLScraper() as scraper:
        return scraper.scrape(url)
