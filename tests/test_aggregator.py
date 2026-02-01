"""Tests for the grocery aggregator."""

import pytest
from mcipe.models import Recipe, ParsedIngredient
from mcipe.aggregators.grocery_aggregator import GroceryAggregator, aggregate_groceries


class TestGroceryAggregator:
    """Tests for GroceryAggregator."""

    @pytest.fixture
    def aggregator(self):
        return GroceryAggregator()

    @pytest.fixture
    def sample_recipes(self):
        """Create sample recipes for testing."""
        recipe1 = Recipe(
            title="Pasta Carbonara",
            ingredients=[
                ParsedIngredient(
                    original_text="1 lb pasta",
                    quantity=1.0,
                    unit="lb",
                    name="pasta",
                    name_normalized="pasta",
                ),
                ParsedIngredient(
                    original_text="4 eggs",
                    quantity=4.0,
                    unit="whole",
                    name="eggs",
                    name_normalized="eggs",
                ),
                ParsedIngredient(
                    original_text="1 cup parmesan, grated",
                    quantity=1.0,
                    unit="cup",
                    name="parmesan",
                    name_normalized="parmesan",
                    form_factor="grated",
                ),
            ],
        )

        recipe2 = Recipe(
            title="Caesar Salad",
            ingredients=[
                ParsedIngredient(
                    original_text="1/2 cup parmesan, shredded",
                    quantity=0.5,
                    unit="cup",
                    name="parmesan",
                    name_normalized="parmesan",
                    form_factor="shredded",
                ),
                ParsedIngredient(
                    original_text="2 eggs",
                    quantity=2.0,
                    unit="whole",
                    name="eggs",
                    name_normalized="eggs",
                ),
                ParsedIngredient(
                    original_text="1 head romaine lettuce",
                    quantity=1.0,
                    unit="head",
                    name="romaine lettuce",
                    name_normalized="romaine lettuce",
                ),
            ],
        )

        return [recipe1, recipe2]

    def test_aggregate_basic(self, aggregator, sample_recipes):
        """Test basic aggregation."""
        result = aggregator.aggregate(sample_recipes)

        assert len(result.items) > 0
        assert len(result.recipe_ids) == 2

    def test_aggregate_combines_same_ingredient(self, aggregator, sample_recipes):
        """Test that same ingredients are combined."""
        result = aggregator.aggregate(sample_recipes)

        # Find eggs in the list
        eggs_item = next((item for item in result.items if "eggs" in item.name.lower()), None)
        assert eggs_item is not None

        # Should have combined quantities from both recipes
        total_qty = sum(qty for qty, _ in eggs_item.quantities)
        assert total_qty == 6.0  # 4 + 2

    def test_aggregate_tracks_form_factors(self, aggregator, sample_recipes):
        """Test that form factors are tracked."""
        result = aggregator.aggregate(sample_recipes)

        # Find parmesan in the list
        parm_item = next(
            (item for item in result.items if "parmesan" in item.name.lower()), None
        )
        assert parm_item is not None

        # Should have both form factors
        assert len(parm_item.form_factors) == 2
        assert "grated" in parm_item.form_factors
        assert "shredded" in parm_item.form_factors

    def test_aggregate_tracks_recipe_sources(self, aggregator, sample_recipes):
        """Test that recipe sources are tracked."""
        result = aggregator.aggregate(sample_recipes)

        # Find parmesan (used in both recipes)
        parm_item = next(
            (item for item in result.items if "parmesan" in item.name.lower()), None
        )
        assert parm_item is not None
        assert len(parm_item.recipe_ids) == 2

    def test_aggregate_assigns_categories(self, aggregator, sample_recipes):
        """Test that categories are assigned."""
        result = aggregator.aggregate(sample_recipes)

        # Eggs should be in dairy category
        eggs_item = next((item for item in result.items if "eggs" in item.name.lower()), None)
        assert eggs_item is not None
        assert eggs_item.category == "dairy"

    def test_convenience_function(self, sample_recipes):
        """Test the aggregate_groceries convenience function."""
        result = aggregate_groceries(sample_recipes)
        assert len(result.items) > 0


class TestGroceryItemDisplay:
    """Tests for GroceryItem display methods."""

    def test_display_quantity_single(self):
        """Test quantity display for single unit."""
        from mcipe.models import GroceryItem

        item = GroceryItem(
            name="flour",
            name_display="Flour",
            quantities=[(2.0, "cup")],
        )
        assert item.display_quantity() == "2 cup"

    def test_display_quantity_multiple_units(self):
        """Test quantity display for multiple units."""
        from mcipe.models import GroceryItem

        item = GroceryItem(
            name="cheese",
            name_display="Cheese",
            quantities=[(1.0, "cup"), (0.5, "cup"), (2.0, "oz")],
        )
        display = item.display_quantity()
        assert "1.5 cup" in display
        assert "2 oz" in display

    def test_display_line(self):
        """Test full line display."""
        from mcipe.models import GroceryItem

        item = GroceryItem(
            name="cheese",
            name_display="Cheddar Cheese",
            quantities=[(2.0, "cup")],
            form_factors=["shredded"],
        )
        line = item.display_line()
        assert "Cheddar Cheese" in line
        assert "2 cup" in line
        assert "shredded" in line
