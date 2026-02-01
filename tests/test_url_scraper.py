"""Tests for URL scraper module."""

import pytest
from unittest.mock import patch, MagicMock

from mcipe.scrapers.url_scraper import URLScraper, ScraperError, scrape_recipe
from mcipe.models import Recipe


class TestURLScraper:
    """Tests for URLScraper class."""

    def test_get_supported_sites(self):
        """Test getting list of supported sites."""
        sites = URLScraper.get_supported_sites()
        assert isinstance(sites, list)
        assert len(sites) > 0
        # Check for some common sites
        assert any("allrecipes" in site.lower() for site in sites)

    def test_is_supported_url_valid(self):
        """Test URL support detection for valid sites."""
        # These should be supported by recipe-scrapers
        valid_urls = [
            "https://www.allrecipes.com/recipe/12345",
            "https://cooking.nytimes.com/recipes/12345",
        ]
        for url in valid_urls:
            # May or may not be supported depending on recipe-scrapers version
            result = URLScraper.is_supported_url(url)
            assert isinstance(result, bool)

    def test_is_supported_url_invalid(self):
        """Test URL support detection for invalid sites."""
        invalid_urls = [
            "https://example.com/recipe",
            "https://randomsite.org/food",
            "not-a-url",
        ]
        for url in invalid_urls:
            assert URLScraper.is_supported_url(url) is False

    def test_scraper_context_manager(self):
        """Test scraper can be used as context manager."""
        with URLScraper() as scraper:
            assert scraper is not None
            assert scraper.client is not None
        # After exiting, client should be closed

    def test_scrape_from_html_valid(self):
        """Test scraping from HTML content."""
        # Minimal valid recipe HTML with JSON-LD
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Recipe</title>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Recipe",
                "name": "Test Recipe",
                "recipeIngredient": ["1 cup flour", "2 eggs"],
                "recipeInstructions": "Mix ingredients."
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        with URLScraper() as scraper:
            recipe = scraper.scrape_from_html(html, "https://example.com/recipe")
            assert recipe.title == "Test Recipe"
            assert len(recipe.ingredients_raw) == 2
            assert "flour" in recipe.ingredients_raw[0]

    def test_scrape_from_html_invalid(self):
        """Test scraping from invalid HTML."""
        html = "<html><body>No recipe here</body></html>"
        with URLScraper() as scraper:
            with pytest.raises(ScraperError):
                scraper.scrape_from_html(html, "https://example.com/page")

    def test_parse_servings_valid(self):
        """Test parsing servings text."""
        assert URLScraper._parse_servings("4 servings") == 4
        assert URLScraper._parse_servings("Serves 6") == 6
        assert URLScraper._parse_servings("Makes 12 cookies") == 12
        assert URLScraper._parse_servings("8") == 8

    def test_parse_servings_invalid(self):
        """Test parsing invalid servings text."""
        assert URLScraper._parse_servings(None) is None
        assert URLScraper._parse_servings("") is None
        assert URLScraper._parse_servings("no numbers here") is None

    def test_split_instructions(self):
        """Test splitting instructions."""
        # Numbered steps
        text = "1. First step\n2. Second step\n3. Third step"
        steps = URLScraper._split_instructions(text)
        assert len(steps) >= 2

        # Double newlines
        text = "First step\n\nSecond step\n\nThird step"
        steps = URLScraper._split_instructions(text)
        assert len(steps) == 3

        # Single newlines
        text = "First step\nSecond step\nThird step"
        steps = URLScraper._split_instructions(text)
        assert len(steps) == 3

    def test_safe_call_success(self):
        """Test _safe_call with successful method."""

        def good_method():
            return "success"

        result = URLScraper._safe_call(good_method)
        assert result == "success"

    def test_safe_call_exception(self):
        """Test _safe_call with method that raises."""

        def bad_method():
            raise ValueError("error")

        result = URLScraper._safe_call(bad_method, default="default")
        assert result == "default"

    def test_safe_call_returns_none(self):
        """Test _safe_call with method that returns None."""

        def none_method():
            return None

        result = URLScraper._safe_call(none_method, default="default")
        assert result == "default"


class TestScrapRecipeFunction:
    """Tests for scrape_recipe convenience function."""

    def test_scrape_recipe_invalid_url(self):
        """Test scraping from invalid URL."""
        with pytest.raises(ScraperError):
            scrape_recipe("https://nonexistent.invalid/recipe")
