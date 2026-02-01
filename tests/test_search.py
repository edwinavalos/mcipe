"""Tests for recipe search module."""

import pytest
from unittest.mock import patch, MagicMock

from mcipe.scrapers.search import RecipeSearcher, RecipeSearchError


class TestRecipeSearcher:
    """Tests for RecipeSearcher class."""

    def test_is_available_without_package(self):
        """Test availability when duckduckgo-search is not installed."""
        searcher = RecipeSearcher()
        # Will be True or False depending on environment
        assert isinstance(searcher.is_available(), bool)

    def test_searcher_context_manager(self):
        """Test searcher can be used as context manager."""
        with RecipeSearcher() as searcher:
            assert searcher is not None

    def test_preferred_sites_defined(self):
        """Test that preferred sites are defined."""
        assert len(RecipeSearcher.PREFERRED_SITES) > 0
        assert "cooking.nytimes.com" in RecipeSearcher.PREFERRED_SITES
        assert "allrecipes.com" in RecipeSearcher.PREFERRED_SITES

    def test_search_not_available_raises_error(self):
        """Test that search raises error when not available."""
        searcher = RecipeSearcher()
        searcher._search_available = False

        with pytest.raises(RecipeSearchError) as exc_info:
            searcher.search("chicken")

        assert "not available" in str(exc_info.value)

    def test_search_with_mocked_ddgs(self):
        """Test search with mocked DuckDuckGo search."""
        searcher = RecipeSearcher()
        searcher._search_available = True

        mock_ddgs = MagicMock()
        mock_ddgs.return_value.text.return_value = [
            {
                "href": "https://cooking.nytimes.com/recipes/12345",
                "title": "Chicken Recipe",
                "body": "A delicious chicken recipe",
            },
            {
                "href": "https://example.com/random",
                "title": "Random Page",
                "body": "Not a recipe",
            },
        ]
        searcher._duckduckgo = mock_ddgs

        results = searcher.search("chicken", max_results=5)

        assert len(results) >= 1
        # Preferred site should be included
        assert any("nytimes" in r["url"] for r in results)

    def test_search_filters_non_recipe_results(self):
        """Test that non-recipe results are filtered."""
        searcher = RecipeSearcher()
        searcher._search_available = True

        mock_ddgs = MagicMock()
        mock_ddgs.return_value.text.return_value = [
            {
                "href": "https://news.example.com/article",
                "title": "News Article",
                "body": "This is news, not food",
            },
        ]
        searcher._duckduckgo = mock_ddgs

        results = searcher.search("chicken", max_results=5)

        # Should filter out non-recipe results
        assert len(results) == 0

    def test_search_marks_preferred_sites(self):
        """Test that preferred sites are marked."""
        searcher = RecipeSearcher()
        searcher._search_available = True

        mock_ddgs = MagicMock()
        mock_ddgs.return_value.text.return_value = [
            {
                "href": "https://www.allrecipes.com/recipe/12345",
                "title": "Test Recipe",
                "body": "Recipe description",
            },
        ]
        searcher._duckduckgo = mock_ddgs

        results = searcher.search("test", max_results=5)

        assert len(results) == 1
        assert results[0]["is_preferred"] is True

    def test_search_and_scrape_no_results(self):
        """Test search_and_scrape with no results."""
        searcher = RecipeSearcher()
        searcher._search_available = True

        mock_ddgs = MagicMock()
        mock_ddgs.return_value.text.return_value = []
        searcher._duckduckgo = mock_ddgs

        with pytest.raises(RecipeSearchError) as exc_info:
            searcher.search_and_scrape("nonexistent recipe xyz")

        assert "No recipes found" in str(exc_info.value)

    def test_search_handles_exception(self):
        """Test that search handles exceptions gracefully."""
        searcher = RecipeSearcher()
        searcher._search_available = True

        mock_ddgs = MagicMock()
        mock_ddgs.return_value.text.side_effect = Exception("Network error")
        searcher._duckduckgo = mock_ddgs

        with pytest.raises(RecipeSearchError) as exc_info:
            searcher.search("chicken")

        assert "Search failed" in str(exc_info.value)
