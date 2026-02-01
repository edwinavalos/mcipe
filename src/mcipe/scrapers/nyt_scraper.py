"""
NYT Cooking scraper using the nytc library.

This module provides authenticated access to NYT Cooking recipes
using the nytc library for fetching and parsing.
"""

from typing import Optional
from urllib.parse import urlparse

from ..models import Recipe

# Track if nytc is available
_nytc_available = False
_nytc_client = None
_nytc_parser = None

try:
    from nytc.client import NytcClient, AuthError, NotFoundError, NetworkError
    from nytc.parser import extract_next_data, parse_recipe, parse_search_results
    _nytc_available = True
except ImportError:
    pass


class NYTScraperError(Exception):
    """Error during NYT recipe scraping."""
    pass


class NYTAuthError(NYTScraperError):
    """Authentication error for NYT Cooking."""
    pass


def is_nyt_available() -> bool:
    """Check if NYT Cooking support is available."""
    return _nytc_available


def is_nyt_url(url: str) -> bool:
    """Check if a URL is from NYT Cooking."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return "cooking.nytimes.com" in host
    except Exception:
        return False


class NYTScraper:
    """
    Scraper for NYT Cooking recipes using the nytc library.

    Requires authentication via NYT-S cookie. Users should run
    'nytc auth' to configure their credentials.
    """

    def __init__(self, cookie: Optional[str] = None):
        """
        Initialize the NYT scraper.

        Args:
            cookie: Optional NYT-S cookie. If not provided, will use
                    the cookie from nytc config.
        """
        if not _nytc_available:
            raise NYTScraperError(
                "NYT Cooking support not available. "
                "Install with: pip install mcipe[nyt]"
            )

        self._cookie = cookie
        self._client: Optional[NytcClient] = None

    @property
    def client(self) -> NytcClient:
        """Lazy-initialized nytc client."""
        if self._client is None:
            self._client = NytcClient(cookie=self._cookie)
        return self._client

    def scrape(self, url: str) -> Recipe:
        """
        Scrape a recipe from NYT Cooking.

        Args:
            url: The NYT Cooking recipe URL

        Returns:
            A Recipe object with parsed data

        Raises:
            NYTAuthError: If authentication fails
            NYTScraperError: If scraping fails
        """
        try:
            # Fetch the page
            html = self.client.fetch_page(url)

            # Parse the recipe data
            next_data = extract_next_data(html)
            recipe_data = parse_recipe(next_data)

            # Convert to our Recipe model
            return self._convert_to_recipe(recipe_data, url)

        except AuthError as e:
            raise NYTAuthError(
                f"NYT Cooking authentication failed: {e}\n"
                "Run 'nytc auth' to configure your credentials."
            ) from e
        except NotFoundError as e:
            raise NYTScraperError(f"Recipe not found: {url}") from e
        except NetworkError as e:
            raise NYTScraperError(f"Network error fetching {url}: {e}") from e
        except Exception as e:
            raise NYTScraperError(f"Failed to scrape recipe from {url}: {e}") from e

    def search(self, query: str) -> list[dict]:
        """
        Search for recipes on NYT Cooking.

        Args:
            query: The search query

        Returns:
            List of search results with id, name, url, author

        Raises:
            NYTAuthError: If authentication fails
            NYTScraperError: If search fails
        """
        try:
            search_url = self.client.get_search_url(query)
            html = self.client.fetch_page(search_url)

            next_data = extract_next_data(html)
            results = parse_search_results(next_data)

            return results.get("results", [])

        except AuthError as e:
            raise NYTAuthError(
                f"NYT Cooking authentication failed: {e}\n"
                "Run 'nytc auth' to configure your credentials."
            ) from e
        except Exception as e:
            raise NYTScraperError(f"Search failed: {e}") from e

    def get_saved_recipes(self) -> list[dict]:
        """
        Get saved recipes from the user's recipe box.

        Returns:
            List of saved recipes with id, name, url, author

        Raises:
            NYTAuthError: If authentication fails
            NYTScraperError: If fetch fails
        """
        try:
            from nytc.parser import parse_saved_recipes

            api_data = self.client.fetch_saved_recipes()
            results = parse_saved_recipes(api_data)

            return results.get("results", [])

        except AuthError as e:
            raise NYTAuthError(
                f"NYT Cooking authentication failed: {e}\n"
                "Run 'nytc auth' to configure your credentials."
            ) from e
        except Exception as e:
            raise NYTScraperError(f"Failed to fetch saved recipes: {e}") from e

    def _convert_to_recipe(self, data: dict, url: str) -> Recipe:
        """
        Convert nytc recipe data to our Recipe model.

        Args:
            data: Recipe data from nytc parser
            url: The original URL

        Returns:
            A Recipe object
        """
        # Parse time information
        time_data = data.get("time", {})
        prep_time = self._parse_time_to_minutes(time_data.get("prep"))
        cook_time = self._parse_time_to_minutes(time_data.get("cook"))
        total_time = self._parse_time_to_minutes(time_data.get("total"))

        # Parse servings
        servings_text = data.get("servings")
        servings = self._parse_servings(servings_text)

        return Recipe(
            title=data.get("name", "Unknown Recipe"),
            url=url,
            source_site="cooking.nytimes.com",
            description=data.get("description"),
            servings=servings,
            servings_text=servings_text,
            prep_time_minutes=prep_time,
            cook_time_minutes=cook_time,
            total_time_minutes=total_time,
            ingredients_raw=data.get("ingredients", []),
            instructions=data.get("steps", []),
        )

    @staticmethod
    def _parse_time_to_minutes(time_str: Optional[str]) -> Optional[int]:
        """Parse a time string like '30 min' or '1 hr 15 min' to minutes."""
        if not time_str:
            return None

        import re
        total_minutes = 0

        # Match hours
        hr_match = re.search(r"(\d+)\s*hr", time_str)
        if hr_match:
            total_minutes += int(hr_match.group(1)) * 60

        # Match minutes
        min_match = re.search(r"(\d+)\s*min", time_str)
        if min_match:
            total_minutes += int(min_match.group(1))

        return total_minutes if total_minutes > 0 else None

    @staticmethod
    def _parse_servings(servings_text: Optional[str]) -> Optional[int]:
        """Parse servings text to an integer."""
        if not servings_text:
            return None

        import re
        match = re.search(r"(\d+)", servings_text)
        if match:
            return int(match.group(1))
        return None


def scrape_nyt_recipe(url: str) -> Recipe:
    """
    Convenience function to scrape a single NYT Cooking recipe.

    Args:
        url: The NYT Cooking recipe URL

    Returns:
        A Recipe object

    Raises:
        NYTScraperError: If scraping fails
    """
    scraper = NYTScraper()
    return scraper.scrape(url)
