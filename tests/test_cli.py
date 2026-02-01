"""Tests for CLI module."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from mcipe.cli.main import cli, parse_recipe_ingredients
from mcipe.models import Recipe, ParsedIngredient
from mcipe.storage.database import Database


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            with patch("mcipe.cli.main.get_db", return_value=db):
                yield db

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "MCIPE" in result.output
        assert "Recipe Scraper" in result.output

    def test_cli_version(self, runner):
        """Test CLI version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_recipes_empty(self, runner, temp_db):
        """Test recipes command with no recipes."""
        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            result = runner.invoke(cli, ["recipes"])
            assert result.exit_code == 0
            assert "No recipes" in result.output

    def test_list_empty(self, runner, temp_db):
        """Test list command with no recipes."""
        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0
            assert "No recipes added" in result.output

    def test_clear_session(self, runner, temp_db):
        """Test clearing the session."""
        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            result = runner.invoke(cli, ["clear"], input="y\n")
            assert result.exit_code == 0
            assert "cleared" in result.output.lower()

    def test_connectors_list(self, runner):
        """Test listing connectors."""
        result = runner.invoke(cli, ["connectors"])
        assert result.exit_code == 0
        assert "Plain Text" in result.output
        assert "Markdown" in result.output

    def test_add_invalid_url(self, runner, temp_db):
        """Test adding with non-URL input."""
        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            result = runner.invoke(cli, ["add", "not-a-url"])
            assert result.exit_code == 0
            assert "doesn't look like a URL" in result.output

    def test_export_empty(self, runner, temp_db):
        """Test export with no recipes."""
        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            result = runner.invoke(cli, ["export"])
            assert result.exit_code == 0
            assert "No recipes to export" in result.output

    def test_remove_empty_session(self, runner, temp_db):
        """Test remove command with no recipes."""
        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            result = runner.invoke(cli, ["remove", "1"])
            assert result.exit_code == 0
            assert "No recipes" in result.output

    def test_add_with_scraping(self, runner, temp_db):
        """Test add command with mocked scraping."""
        mock_recipe = Recipe(
            title="Test Recipe",
            url="https://example.com/recipe",
            ingredients_raw=["1 cup flour", "2 eggs"],
        )

        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            with patch("mcipe.cli.main.URLScraper") as MockScraper:
                instance = MockScraper.return_value.__enter__.return_value
                instance.scrape.return_value = mock_recipe

                result = runner.invoke(cli, ["add", "https://example.com/recipe"])
                assert result.exit_code == 0
                assert "Test Recipe" in result.output

    def test_list_with_recipes(self, runner, temp_db):
        """Test list command with recipes in session."""
        # Add a recipe to the session
        recipe = Recipe(
            title="Chocolate Cake",
            ingredients=[
                ParsedIngredient(
                    original_text="2 cups flour",
                    name="flour",
                    quantity=2.0,
                    unit="cup",
                ),
            ],
        )
        temp_db.save_recipe(recipe)
        temp_db.add_to_session(recipe.id)

        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            result = runner.invoke(cli, ["list"])
            assert result.exit_code == 0
            assert "flour" in result.output.lower()

    def test_list_by_category(self, runner, temp_db):
        """Test list command with category grouping."""
        recipe = Recipe(
            title="Test Recipe",
            ingredients=[
                ParsedIngredient(
                    original_text="1 lb chicken",
                    name="chicken",
                    quantity=1.0,
                    unit="lb",
                ),
            ],
        )
        temp_db.save_recipe(recipe)
        temp_db.add_to_session(recipe.id)

        with patch("mcipe.cli.main.get_db", return_value=temp_db):
            result = runner.invoke(cli, ["list", "--by-category"])
            assert result.exit_code == 0


class TestParseRecipeIngredients:
    """Tests for parse_recipe_ingredients function."""

    def test_parse_ingredients(self):
        """Test parsing ingredients in a recipe."""
        recipe = Recipe(
            title="Test",
            ingredients_raw=["1 cup flour", "2 tablespoons sugar"],
        )

        result = parse_recipe_ingredients(recipe)
        assert len(result.ingredients) == 2
        assert result.ingredients[0].quantity == 1.0
        assert result.ingredients[0].unit == "cup"

    def test_parse_empty_ingredients(self):
        """Test parsing recipe with no ingredients."""
        recipe = Recipe(title="Empty Recipe")
        result = parse_recipe_ingredients(recipe)
        assert len(result.ingredients) == 0
