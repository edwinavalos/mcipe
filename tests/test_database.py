"""Tests for database storage module."""

import pytest
import tempfile
from pathlib import Path

from mcipe.storage.database import Database, get_database
from mcipe.models import Recipe, ParsedIngredient, GroceryList, GroceryItem


class TestDatabase:
    """Tests for Database class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = Database(db_path)
            yield db

    @pytest.fixture
    def sample_recipe(self):
        """Create a sample recipe for testing."""
        return Recipe(
            title="Test Recipe",
            url="https://example.com/recipe",
            source_site="example.com",
            servings=4,
            ingredients=[
                ParsedIngredient(
                    original_text="1 cup flour",
                    name="flour",
                    quantity=1.0,
                    unit="cup",
                ),
                ParsedIngredient(
                    original_text="2 eggs",
                    name="eggs",
                    quantity=2.0,
                ),
            ],
            ingredients_raw=["1 cup flour", "2 eggs"],
        )

    def test_database_creation(self, temp_db):
        """Test that database is created successfully."""
        assert temp_db.db_path.exists()

    def test_save_and_get_recipe(self, temp_db, sample_recipe):
        """Test saving and retrieving a recipe."""
        recipe_id = temp_db.save_recipe(sample_recipe)
        assert recipe_id == sample_recipe.id

        retrieved = temp_db.get_recipe(recipe_id)
        assert retrieved is not None
        assert retrieved.title == sample_recipe.title
        assert retrieved.url == sample_recipe.url
        assert len(retrieved.ingredients) == 2

    def test_get_recipe_not_found(self, temp_db):
        """Test getting a non-existent recipe."""
        result = temp_db.get_recipe("nonexistent-id")
        assert result is None

    def test_get_recipe_by_url(self, temp_db, sample_recipe):
        """Test getting a recipe by URL."""
        temp_db.save_recipe(sample_recipe)

        retrieved = temp_db.get_recipe_by_url(sample_recipe.url)
        assert retrieved is not None
        assert retrieved.title == sample_recipe.title

    def test_get_recipe_by_url_not_found(self, temp_db):
        """Test getting a recipe by non-existent URL."""
        result = temp_db.get_recipe_by_url("https://nonexistent.com/recipe")
        assert result is None

    def test_get_all_recipes(self, temp_db, sample_recipe):
        """Test getting all recipes."""
        # Add multiple recipes
        temp_db.save_recipe(sample_recipe)

        recipe2 = Recipe(title="Second Recipe", url="https://example.com/recipe2")
        temp_db.save_recipe(recipe2)

        all_recipes = temp_db.get_all_recipes()
        assert len(all_recipes) == 2

    def test_delete_recipe(self, temp_db, sample_recipe):
        """Test deleting a recipe."""
        temp_db.save_recipe(sample_recipe)

        # Verify it exists
        assert temp_db.get_recipe(sample_recipe.id) is not None

        # Delete
        result = temp_db.delete_recipe(sample_recipe.id)
        assert result is True

        # Verify it's gone
        assert temp_db.get_recipe(sample_recipe.id) is None

    def test_delete_recipe_not_found(self, temp_db):
        """Test deleting a non-existent recipe."""
        result = temp_db.delete_recipe("nonexistent-id")
        assert result is False

    def test_session_operations(self, temp_db, sample_recipe):
        """Test session management."""
        temp_db.save_recipe(sample_recipe)

        # Initially empty
        assert temp_db.get_session_recipe_ids() == []

        # Add to session
        temp_db.add_to_session(sample_recipe.id)
        assert sample_recipe.id in temp_db.get_session_recipe_ids()

        # Add again (should not duplicate)
        temp_db.add_to_session(sample_recipe.id)
        ids = temp_db.get_session_recipe_ids()
        assert ids.count(sample_recipe.id) == 1

        # Remove from session
        temp_db.remove_from_session(sample_recipe.id)
        assert sample_recipe.id not in temp_db.get_session_recipe_ids()

        # Clear session
        temp_db.add_to_session(sample_recipe.id)
        temp_db.clear_session()
        assert temp_db.get_session_recipe_ids() == []

    def test_get_recipes_in_session(self, temp_db, sample_recipe):
        """Test getting recipes in current session."""
        temp_db.save_recipe(sample_recipe)
        temp_db.add_to_session(sample_recipe.id)

        recipes = temp_db.get_recipes_in_session()
        assert len(recipes) == 1
        assert recipes[0].title == sample_recipe.title

    def test_save_and_get_grocery_list(self, temp_db):
        """Test saving and retrieving a grocery list."""
        grocery_list = GroceryList(
            name="Weekly Shopping",
            items=[
                GroceryItem(
                    name="flour",
                    name_display="All-Purpose Flour",
                    quantities=[(2.0, "cup")],
                ),
            ],
            recipe_ids=["recipe-1"],
        )

        list_id = temp_db.save_grocery_list(grocery_list)
        assert list_id == grocery_list.id

        retrieved = temp_db.get_grocery_list(list_id)
        assert retrieved is not None
        assert retrieved.name == "Weekly Shopping"
        assert len(retrieved.items) == 1

    def test_get_current_grocery_list(self, temp_db):
        """Test getting the most recent grocery list."""
        # No lists yet
        assert temp_db.get_current_grocery_list() is None

        # Add a list
        grocery_list = GroceryList(name="First List")
        temp_db.save_grocery_list(grocery_list)

        current = temp_db.get_current_grocery_list()
        assert current is not None
        assert current.name == "First List"

    def test_delete_grocery_list(self, temp_db):
        """Test deleting a grocery list."""
        grocery_list = GroceryList(name="To Delete")
        temp_db.save_grocery_list(grocery_list)

        result = temp_db.delete_grocery_list(grocery_list.id)
        assert result is True
        assert temp_db.get_grocery_list(grocery_list.id) is None

    def test_export_and_import_json(self, temp_db, sample_recipe):
        """Test JSON export and import."""
        # Save some data
        temp_db.save_recipe(sample_recipe)
        temp_db.add_to_session(sample_recipe.id)

        # Export
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = Path(tmpdir) / "export.json"
            temp_db.export_to_json(export_path)

            assert export_path.exists()

            # Create new database and import
            new_db_path = Path(tmpdir) / "new.db"
            new_db = Database(new_db_path)
            new_db.import_from_json(export_path)

            # Verify data was imported
            recipes = new_db.get_all_recipes()
            assert len(recipes) == 1
            assert recipes[0].title == sample_recipe.title


class TestGetDatabase:
    """Tests for get_database function."""

    def test_get_database_singleton(self):
        """Test that get_database returns same instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db1 = get_database(db_path)
            db2 = get_database(db_path)
            assert db1 is db2
