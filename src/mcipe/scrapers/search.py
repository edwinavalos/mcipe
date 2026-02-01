"""
Recipe search functionality.

This module provides the ability to search for recipes by query
and then scrape them from the results.
"""

from typing import Optional

from ..models import Recipe
from .url_scraper import URLScraper, ScraperError


class RecipeSearchError(Exception):
    """Error during recipe search."""

    pass


class RecipeSearcher:
    """
    Search for recipes using web search and scrape the results.
    """

    # Preferred recipe sites (in order of preference)
    PREFERRED_SITES = [
        "cooking.nytimes.com",
        "nytimes.com/recipes",
        "seriouseats.com",
        "bonappetit.com",
        "epicurious.com",
        "foodnetwork.com",
        "allrecipes.com",
        "simplyrecipes.com",
        "budgetbytes.com",
        "skinnytaste.com",
        "delish.com",
        "tasty.co",
        "food52.com",
        "thekitchn.com",
        "smittenkitchen.com",
    ]

    def __init__(self):
        """Initialize the searcher."""
        self._scraper = URLScraper()
        self._search_available = False
        self._duckduckgo = None

        # Try to import duckduckgo-search
        try:
            from duckduckgo_search import DDGS

            self._duckduckgo = DDGS
            self._search_available = True
        except ImportError:
            pass

    def is_available(self) -> bool:
        """Check if search functionality is available."""
        return self._search_available

    def search(
        self,
        query: str,
        max_results: int = 10,
        prefer_sites: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Search for recipes matching the query.

        Args:
            query: The search query (e.g., "chicken tikka masala")
            max_results: Maximum number of results to return
            prefer_sites: Optional list of preferred sites

        Returns:
            List of search results with url, title, description

        Raises:
            RecipeSearchError: If search fails or is not available
        """
        if not self._search_available:
            raise RecipeSearchError(
                "Search functionality not available. "
                "Install with: pip install mcipe[search]"
            )

        # Build search query
        search_query = f"recipe {query}"

        try:
            ddgs = self._duckduckgo()
            results = list(ddgs.text(search_query, max_results=max_results * 2))
        except Exception as e:
            raise RecipeSearchError(f"Search failed: {e}") from e

        # Filter and sort results
        recipe_results = []
        sites_to_prefer = prefer_sites or self.PREFERRED_SITES

        for result in results:
            url = result.get("href", "")
            title = result.get("title", "")
            description = result.get("body", "")

            # Check if it's from a known recipe site
            is_preferred = any(site in url.lower() for site in sites_to_prefer)

            # Check if it looks like a recipe
            looks_like_recipe = any(
                word in url.lower() + title.lower()
                for word in ["recipe", "recipes", "cooking", "cook", "make", "how-to"]
            )

            if is_preferred or looks_like_recipe:
                recipe_results.append(
                    {
                        "url": url,
                        "title": title,
                        "description": description,
                        "is_preferred": is_preferred,
                    }
                )

        # Sort: preferred sites first
        recipe_results.sort(key=lambda x: (not x["is_preferred"], x["title"]))

        return recipe_results[:max_results]

    def search_and_scrape(
        self,
        query: str,
        max_attempts: int = 3,
    ) -> Recipe:
        """
        Search for a recipe and scrape the first successful result.

        Args:
            query: The search query
            max_attempts: Maximum number of URLs to try scraping

        Returns:
            The scraped Recipe

        Raises:
            RecipeSearchError: If no recipe could be found or scraped
        """
        results = self.search(query, max_results=max_attempts * 2)

        if not results:
            raise RecipeSearchError(f"No recipes found for query: {query}")

        errors = []
        for result in results[:max_attempts]:
            try:
                recipe = self._scraper.scrape(result["url"])
                return recipe
            except ScraperError as e:
                errors.append(f"{result['url']}: {e}")
                continue

        raise RecipeSearchError(
            f"Could not scrape any recipes for query: {query}\n"
            f"Errors:\n" + "\n".join(errors)
        )

    def close(self):
        """Close resources."""
        self._scraper.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def search_recipes(query: str, max_results: int = 10) -> list[dict]:
    """
    Convenience function to search for recipes.

    Args:
        query: The search query
        max_results: Maximum results

    Returns:
        List of search results
    """
    with RecipeSearcher() as searcher:
        return searcher.search(query, max_results)


def search_and_scrape_recipe(query: str) -> Recipe:
    """
    Convenience function to search and scrape a recipe.

    Args:
        query: The search query

    Returns:
        The scraped Recipe
    """
    with RecipeSearcher() as searcher:
        return searcher.search_and_scrape(query)
