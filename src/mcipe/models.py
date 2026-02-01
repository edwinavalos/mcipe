"""
Core data models for MCIPE.

These models represent recipes, ingredients, and grocery list items
with full support for serialization and validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class Unit(str, Enum):
    """Standard units for ingredient measurements."""

    # Volume
    TEASPOON = "tsp"
    TABLESPOON = "tbsp"
    CUP = "cup"
    FLUID_OUNCE = "fl oz"
    PINT = "pint"
    QUART = "quart"
    GALLON = "gallon"
    MILLILITER = "ml"
    LITER = "L"

    # Weight
    OUNCE = "oz"
    POUND = "lb"
    GRAM = "g"
    KILOGRAM = "kg"

    # Count/Other
    PIECE = "piece"
    WHOLE = "whole"
    CLOVE = "clove"
    SLICE = "slice"
    PINCH = "pinch"
    DASH = "dash"
    BUNCH = "bunch"
    SPRIG = "sprig"
    CAN = "can"
    PACKAGE = "package"

    # Generic
    UNIT = "unit"
    TO_TASTE = "to taste"


class ParsedIngredient(BaseModel):
    """
    A parsed ingredient from a recipe.

    This represents a single ingredient line broken down into its components.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # The original text from the recipe
    original_text: str

    # Parsed components
    quantity: Optional[float] = None
    quantity_max: Optional[float] = None  # For ranges like "1-2 cups"
    unit: Optional[str] = None
    unit_normalized: Optional[Unit] = None

    # The main ingredient name (normalized)
    name: str
    name_normalized: Optional[str] = None  # Lowercase, singular form

    # Preparation notes (e.g., "chopped", "minced", "at room temperature")
    preparation: Optional[str] = None

    # Form factor (e.g., "shredded", "block", "sliced")
    form_factor: Optional[str] = None

    # Additional notes
    notes: Optional[str] = None

    # Is this optional?
    optional: bool = False

    def __str__(self) -> str:
        """Human-readable representation."""
        parts = []
        if self.quantity:
            qty_str = self._format_quantity(self.quantity)
            if self.quantity_max and self.quantity_max != self.quantity:
                qty_max_str = self._format_quantity(self.quantity_max)
                parts.append(f"{qty_str}-{qty_max_str}")
            else:
                parts.append(qty_str)
        if self.unit:
            parts.append(self.unit)
        parts.append(self.name)
        if self.form_factor:
            parts.append(f"({self.form_factor})")
        if self.preparation:
            parts.append(f", {self.preparation}")
        if self.optional:
            parts.append("(optional)")
        return " ".join(parts)

    @staticmethod
    def _format_quantity(qty: float) -> str:
        """Format a quantity value, showing integers without decimals."""
        if qty == int(qty):
            return str(int(qty))
        return f"{qty:.2f}".rstrip('0').rstrip('.')


class Recipe(BaseModel):
    """
    A recipe scraped from a URL or search.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Source information
    title: str
    url: Optional[str] = None
    source_site: Optional[str] = None  # e.g., "NYT Cooking", "AllRecipes"

    # Recipe details
    description: Optional[str] = None
    servings: Optional[int] = None
    servings_text: Optional[str] = None  # Original text like "4-6 servings"
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    total_time_minutes: Optional[int] = None

    # Ingredients
    ingredients: list[ParsedIngredient] = Field(default_factory=list)
    ingredients_raw: list[str] = Field(default_factory=list)  # Original text

    # Instructions (kept for reference)
    instructions: list[str] = Field(default_factory=list)

    # Metadata
    added_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)

    # Scaling
    scale_factor: float = 1.0  # For doubling/halving recipes

    def __str__(self) -> str:
        return f"{self.title} ({len(self.ingredients)} ingredients)"


class GroceryItem(BaseModel):
    """
    An aggregated grocery list item.

    This combines the same ingredient from multiple recipes,
    tracking total quantities needed.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # The normalized ingredient name
    name: str
    name_display: str  # User-friendly display name

    # Aggregated quantities (may have multiple units)
    quantities: list[tuple[float, str]] = Field(default_factory=list)  # [(amount, unit), ...]

    # Combined form factors needed
    form_factors: list[str] = Field(default_factory=list)

    # Which recipes need this ingredient
    recipe_ids: list[str] = Field(default_factory=list)
    recipe_names: list[str] = Field(default_factory=list)

    # Shopping notes
    notes: list[str] = Field(default_factory=list)

    # Status
    purchased: bool = False

    # Category for organizing (produce, dairy, meat, etc.)
    category: Optional[str] = None

    def display_quantity(self) -> str:
        """Format quantities for display."""
        if not self.quantities:
            return ""

        # Group by unit
        by_unit: dict[str, float] = {}
        for amount, unit in self.quantities:
            by_unit[unit] = by_unit.get(unit, 0) + amount

        parts = []
        for unit, amount in by_unit.items():
            # Format amount nicely
            if amount == int(amount):
                amount_str = str(int(amount))
            else:
                amount_str = f"{amount:.2f}".rstrip('0').rstrip('.')

            if unit and unit != "unit":
                parts.append(f"{amount_str} {unit}")
            else:
                parts.append(amount_str)

        return " + ".join(parts)

    def display_line(self) -> str:
        """Format as a single line for a shopping list."""
        parts = [self.name_display]

        qty = self.display_quantity()
        if qty:
            parts.insert(0, qty)

        if self.form_factors:
            parts.append(f"({', '.join(set(self.form_factors))})")

        return " ".join(parts)


class GroceryList(BaseModel):
    """
    A complete grocery list aggregating ingredients from multiple recipes.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Shopping List"

    # Items in the list
    items: list[GroceryItem] = Field(default_factory=list)

    # Source recipes
    recipe_ids: list[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"{self.name} ({len(self.items)} items from {len(self.recipe_ids)} recipes)"
