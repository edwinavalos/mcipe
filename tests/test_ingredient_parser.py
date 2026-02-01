"""Tests for the ingredient parser."""

import pytest
from mcipe.parsers.ingredient_parser import IngredientParser, parse_ingredient


class TestIngredientParser:
    """Tests for IngredientParser."""

    @pytest.fixture
    def parser(self):
        return IngredientParser()

    def test_simple_ingredient(self, parser):
        """Test parsing a simple ingredient."""
        result = parser.parse("1 cup flour")
        assert result.quantity == 1.0
        assert result.unit == "cup"
        assert result.name == "flour"

    def test_ingredient_with_fraction(self, parser):
        """Test parsing an ingredient with a fraction."""
        result = parser.parse("1/2 cup sugar")
        assert result.quantity == 0.5
        assert result.unit == "cup"
        assert result.name == "sugar"

    def test_mixed_number(self, parser):
        """Test parsing a mixed number like 1 1/2."""
        result = parser.parse("1 1/2 cups milk")
        assert result.quantity == 1.5
        assert result.unit == "cup"
        assert result.name == "milk"

    def test_quantity_range(self, parser):
        """Test parsing a quantity range."""
        result = parser.parse("2-3 cloves garlic")
        assert result.quantity == 2.0
        assert result.quantity_max == 3.0
        assert result.unit == "clove"
        assert result.name == "garlic"

    def test_ingredient_with_preparation(self, parser):
        """Test parsing an ingredient with preparation notes."""
        result = parser.parse("1 onion, diced")
        assert result.quantity == 1.0
        assert result.name == "onion"
        assert "diced" in result.preparation.lower()

    def test_ingredient_with_form_factor(self, parser):
        """Test parsing an ingredient with form factor."""
        result = parser.parse("2 cups shredded cheese")
        assert result.quantity == 2.0
        assert result.unit == "cup"
        assert result.form_factor == "shredded"
        assert result.name == "cheese"

    def test_optional_ingredient(self, parser):
        """Test parsing an optional ingredient."""
        result = parser.parse("1/4 cup parsley, optional")
        assert result.quantity == 0.25
        assert result.optional is True

    def test_unicode_fraction(self, parser):
        """Test parsing unicode fractions."""
        result = parser.parse("½ cup butter")
        assert result.quantity == 0.5
        assert result.unit == "cup"
        assert result.name == "butter"

    def test_tablespoon_variations(self, parser):
        """Test various tablespoon spellings."""
        for text in ["1 tablespoon oil", "1 tbsp oil", "1 Tbsp oil"]:
            result = parser.parse(text)
            assert result.unit == "tbsp"
            assert result.name == "oil"

    def test_ingredient_with_parentheses(self, parser):
        """Test parsing ingredient with parenthetical info."""
        result = parser.parse("1 can (15 oz) black beans")
        assert result.quantity == 1.0
        assert "can" in result.unit or "black beans" in result.name
        # The parenthetical weight info should be captured

    def test_no_quantity(self, parser):
        """Test parsing ingredient without quantity."""
        result = parser.parse("salt and pepper to taste")
        assert result.quantity is None
        assert "salt" in result.name.lower()

    def test_pound_unit(self, parser):
        """Test parsing pounds."""
        result = parser.parse("2 lbs ground beef")
        assert result.quantity == 2.0
        assert result.unit == "lb"
        assert "ground beef" in result.name or "beef" in result.name

    def test_preserve_original_text(self, parser):
        """Test that original text is preserved."""
        original = "2 cups all-purpose flour, sifted"
        result = parser.parse(original)
        assert result.original_text == original


class TestParseIngredientFunction:
    """Tests for the convenience function."""

    def test_convenience_function(self):
        """Test the parse_ingredient convenience function."""
        result = parse_ingredient("1 cup sugar")
        assert result.quantity == 1.0
        assert result.unit == "cup"
        assert result.name == "sugar"
