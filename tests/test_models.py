"""Tests for data models."""

import pytest
from mcipe.models import ParsedIngredient, Recipe, GroceryItem, GroceryList, Unit


class TestParsedIngredient:
    """Tests for ParsedIngredient model."""

    def test_create_basic_ingredient(self):
        """Test creating a basic ingredient."""
        ing = ParsedIngredient(
            original_text="1 cup flour",
            quantity=1.0,
            unit="cup",
            name="flour",
        )
        assert ing.quantity == 1.0
        assert ing.unit == "cup"
        assert ing.name == "flour"
        assert ing.id is not None

    def test_ingredient_str_representation(self):
        """Test string representation."""
        ing = ParsedIngredient(
            original_text="2 cups sugar, sifted",
            quantity=2.0,
            unit="cup",
            name="sugar",
            preparation="sifted",
        )
        s = str(ing)
        assert "2" in s
        assert "cup" in s
        assert "sugar" in s
        assert "sifted" in s

    def test_ingredient_with_range(self):
        """Test ingredient with quantity range."""
        ing = ParsedIngredient(
            original_text="2-3 cloves garlic",
            quantity=2.0,
            quantity_max=3.0,
            unit="clove",
            name="garlic",
        )
        s = str(ing)
        assert "2-3" in s

    def test_optional_ingredient(self):
        """Test optional ingredient."""
        ing = ParsedIngredient(
            original_text="parsley (optional)",
            name="parsley",
            optional=True,
        )
        s = str(ing)
        assert "optional" in s.lower()


class TestRecipe:
    """Tests for Recipe model."""

    def test_create_recipe(self):
        """Test creating a recipe."""
        recipe = Recipe(
            title="Test Recipe",
            url="https://example.com/recipe",
            source_site="example.com",
        )
        assert recipe.title == "Test Recipe"
        assert recipe.id is not None
        assert recipe.scale_factor == 1.0

    def test_recipe_with_ingredients(self):
        """Test recipe with ingredients list."""
        recipe = Recipe(
            title="Test Recipe",
            ingredients=[
                ParsedIngredient(original_text="1 cup flour", name="flour", quantity=1.0),
                ParsedIngredient(original_text="2 eggs", name="eggs", quantity=2.0),
            ],
        )
        assert len(recipe.ingredients) == 2

    def test_recipe_str_representation(self):
        """Test string representation."""
        recipe = Recipe(
            title="Chocolate Cake",
            ingredients=[
                ParsedIngredient(original_text="flour", name="flour"),
                ParsedIngredient(original_text="sugar", name="sugar"),
            ],
        )
        s = str(recipe)
        assert "Chocolate Cake" in s
        assert "2 ingredients" in s


class TestGroceryItem:
    """Tests for GroceryItem model."""

    def test_create_grocery_item(self):
        """Test creating a grocery item."""
        item = GroceryItem(
            name="flour",
            name_display="All-Purpose Flour",
            quantities=[(2.0, "cup")],
        )
        assert item.name == "flour"
        assert item.purchased is False

    def test_display_quantity_empty(self):
        """Test display_quantity with no quantities."""
        item = GroceryItem(
            name="salt",
            name_display="Salt",
            quantities=[],
        )
        assert item.display_quantity() == ""

    def test_display_quantity_aggregates_same_unit(self):
        """Test that same units are aggregated."""
        item = GroceryItem(
            name="flour",
            name_display="Flour",
            quantities=[(1.0, "cup"), (0.5, "cup")],
        )
        assert item.display_quantity() == "1.5 cup"


class TestGroceryList:
    """Tests for GroceryList model."""

    def test_create_grocery_list(self):
        """Test creating a grocery list."""
        glist = GroceryList(name="Weekly Shopping")
        assert glist.name == "Weekly Shopping"
        assert len(glist.items) == 0
        assert glist.id is not None

    def test_grocery_list_str(self):
        """Test string representation."""
        glist = GroceryList(
            name="Test List",
            items=[
                GroceryItem(name="flour", name_display="Flour"),
                GroceryItem(name="sugar", name_display="Sugar"),
            ],
            recipe_ids=["r1", "r2"],
        )
        s = str(glist)
        assert "2 items" in s
        assert "2 recipes" in s


class TestUnit:
    """Tests for Unit enum."""

    def test_unit_values(self):
        """Test unit enum values."""
        assert Unit.TEASPOON.value == "tsp"
        assert Unit.TABLESPOON.value == "tbsp"
        assert Unit.CUP.value == "cup"
        assert Unit.POUND.value == "lb"
        assert Unit.OUNCE.value == "oz"
