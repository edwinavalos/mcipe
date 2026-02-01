"""
Grocery list aggregation.

This module combines ingredients from multiple recipes into a consolidated
grocery list, handling unit conversions and ingredient matching.
"""

from collections import defaultdict
from typing import Optional

from ..models import GroceryItem, GroceryList, ParsedIngredient, Recipe


class GroceryAggregator:
    """
    Aggregates ingredients from multiple recipes into a grocery list.
    """

    # Ingredient categories for organization
    CATEGORIES = {
        # Produce
        "produce": [
            "onion",
            "garlic",
            "tomato",
            "potato",
            "carrot",
            "celery",
            "pepper",
            "lettuce",
            "spinach",
            "kale",
            "broccoli",
            "cauliflower",
            "zucchini",
            "squash",
            "cucumber",
            "mushroom",
            "corn",
            "pea",
            "bean",
            "asparagus",
            "artichoke",
            "avocado",
            "lemon",
            "lime",
            "orange",
            "apple",
            "banana",
            "berry",
            "grape",
            "melon",
            "ginger",
            "cilantro",
            "parsley",
            "basil",
            "mint",
            "thyme",
            "rosemary",
            "sage",
            "dill",
            "chive",
            "green onion",
            "scallion",
            "shallot",
            "leek",
            "cabbage",
            "bok choy",
            "eggplant",
            "beet",
            "radish",
            "turnip",
            "sweet potato",
            "yam",
            "jalapeño",
            "serrano",
            "habanero",
            "poblano",
        ],
        # Dairy
        "dairy": [
            "milk",
            "cream",
            "butter",
            "cheese",
            "yogurt",
            "sour cream",
            "cream cheese",
            "cottage cheese",
            "ricotta",
            "mozzarella",
            "parmesan",
            "cheddar",
            "feta",
            "goat cheese",
            "brie",
            "gruyere",
            "swiss",
            "provolone",
            "half and half",
            "half-and-half",
            "whipping cream",
            "heavy cream",
            "buttermilk",
            "egg",
            "eggs",
        ],
        # Meat & Seafood
        "meat": [
            "chicken",
            "beef",
            "pork",
            "lamb",
            "turkey",
            "duck",
            "bacon",
            "sausage",
            "ham",
            "prosciutto",
            "pancetta",
            "ground beef",
            "ground pork",
            "ground turkey",
            "ground chicken",
            "steak",
            "roast",
            "chop",
            "tenderloin",
            "ribs",
            "brisket",
            "fish",
            "salmon",
            "tuna",
            "cod",
            "tilapia",
            "halibut",
            "trout",
            "shrimp",
            "crab",
            "lobster",
            "scallop",
            "mussel",
            "clam",
            "oyster",
            "anchovy",
            "sardine",
        ],
        # Pantry
        "pantry": [
            "flour",
            "sugar",
            "salt",
            "pepper",
            "oil",
            "olive oil",
            "vegetable oil",
            "canola oil",
            "sesame oil",
            "coconut oil",
            "vinegar",
            "balsamic",
            "rice vinegar",
            "wine vinegar",
            "apple cider vinegar",
            "soy sauce",
            "fish sauce",
            "worcestershire",
            "hot sauce",
            "sriracha",
            "ketchup",
            "mustard",
            "mayonnaise",
            "honey",
            "maple syrup",
            "molasses",
            "vanilla",
            "cinnamon",
            "nutmeg",
            "cumin",
            "paprika",
            "chili powder",
            "cayenne",
            "oregano",
            "basil",
            "thyme",
            "rosemary",
            "bay leaf",
            "curry",
            "turmeric",
            "ginger",
            "garlic powder",
            "onion powder",
            "black pepper",
            "white pepper",
            "red pepper flakes",
            "italian seasoning",
            "taco seasoning",
            "rice",
            "pasta",
            "noodle",
            "bread",
            "breadcrumb",
            "cracker",
            "tortilla",
            "pita",
            "broth",
            "stock",
            "bouillon",
            "tomato paste",
            "tomato sauce",
            "diced tomatoes",
            "crushed tomatoes",
            "coconut milk",
            "evaporated milk",
            "condensed milk",
            "peanut butter",
            "almond butter",
            "jam",
            "jelly",
            "oat",
            "oatmeal",
            "cereal",
            "granola",
            "nut",
            "almond",
            "walnut",
            "pecan",
            "cashew",
            "peanut",
            "pistachio",
            "seed",
            "sesame",
            "sunflower",
            "pumpkin seed",
            "chia",
            "flax",
            "baking powder",
            "baking soda",
            "yeast",
            "cornstarch",
            "cocoa",
            "chocolate",
            "chocolate chip",
        ],
        # Canned & Jarred
        "canned": [
            "canned",
            "can of",
            "beans",
            "black beans",
            "kidney beans",
            "chickpeas",
            "garbanzo",
            "lentil",
            "corn",
            "peas",
            "olives",
            "pickles",
            "capers",
            "artichoke hearts",
            "roasted peppers",
            "sun-dried tomatoes",
            "tuna",
            "salmon",
            "sardines",
            "anchovies",
            "coconut cream",
        ],
        # Frozen
        "frozen": [
            "frozen",
            "ice cream",
            "frozen vegetables",
            "frozen fruit",
            "frozen pizza",
            "frozen meal",
        ],
        # Beverages
        "beverages": [
            "wine",
            "beer",
            "vodka",
            "rum",
            "whiskey",
            "bourbon",
            "tequila",
            "gin",
            "brandy",
            "sherry",
            "marsala",
            "sake",
            "mirin",
            "coffee",
            "tea",
            "juice",
            "soda",
            "water",
            "sparkling water",
            "club soda",
            "tonic",
        ],
    }

    def __init__(self):
        """Initialize the aggregator."""
        # Build reverse category lookup
        self._category_lookup: dict[str, str] = {}
        for category, ingredients in self.CATEGORIES.items():
            for ingredient in ingredients:
                self._category_lookup[ingredient.lower()] = category

    def aggregate(self, recipes: list[Recipe]) -> GroceryList:
        """
        Aggregate ingredients from multiple recipes into a grocery list.

        Args:
            recipes: List of recipes to aggregate

        Returns:
            A GroceryList with combined ingredients
        """
        # Group ingredients by normalized name
        ingredient_groups: dict[str, list[tuple[Recipe, ParsedIngredient]]] = defaultdict(list)

        for recipe in recipes:
            for ingredient in recipe.ingredients:
                # Use normalized name if available, otherwise use regular name
                key = (ingredient.name_normalized or ingredient.name).lower()
                ingredient_groups[key].append((recipe, ingredient))

        # Create grocery items from groups
        items: list[GroceryItem] = []

        for name_key, group in ingredient_groups.items():
            item = self._create_grocery_item(name_key, group)
            items.append(item)

        # Sort items by category then name
        items.sort(key=lambda x: (x.category or "zzz", x.name_display.lower()))

        return GroceryList(
            items=items,
            recipe_ids=[r.id for r in recipes],
        )

    def _create_grocery_item(
        self, name_key: str, group: list[tuple[Recipe, ParsedIngredient]]
    ) -> GroceryItem:
        """
        Create a grocery item from a group of matching ingredients.

        Args:
            name_key: The normalized ingredient name
            group: List of (recipe, ingredient) tuples

        Returns:
            A GroceryItem
        """
        # Collect quantities
        quantities: list[tuple[float, str]] = []
        form_factors: list[str] = []
        recipe_ids: list[str] = []
        recipe_names: list[str] = []
        notes: list[str] = []

        # Use the first ingredient's name for display (usually has best capitalization)
        display_name = group[0][1].name

        for recipe, ingredient in group:
            # Add quantity if present
            if ingredient.quantity:
                unit = ingredient.unit or "unit"
                # Apply recipe scale factor
                qty = ingredient.quantity * recipe.scale_factor
                quantities.append((qty, unit))

                # Handle quantity ranges
                if ingredient.quantity_max and ingredient.quantity_max != ingredient.quantity:
                    qty_max = ingredient.quantity_max * recipe.scale_factor
                    # Use average for simplicity
                    quantities[-1] = ((qty + qty_max) / 2, unit)

            # Collect form factors
            if ingredient.form_factor and ingredient.form_factor not in form_factors:
                form_factors.append(ingredient.form_factor)

            # Track which recipes need this
            if recipe.id not in recipe_ids:
                recipe_ids.append(recipe.id)
                recipe_names.append(recipe.title)

            # Collect notes
            if ingredient.preparation and ingredient.preparation not in notes:
                notes.append(ingredient.preparation)
            if ingredient.notes and ingredient.notes not in notes:
                notes.append(ingredient.notes)

        # Determine category
        category = self._get_category(name_key)

        return GroceryItem(
            name=name_key,
            name_display=display_name,
            quantities=quantities,
            form_factors=form_factors,
            recipe_ids=recipe_ids,
            recipe_names=recipe_names,
            notes=notes,
            category=category,
        )

    def _get_category(self, ingredient_name: str) -> Optional[str]:
        """
        Determine the category for an ingredient.

        Args:
            ingredient_name: The ingredient name (lowercase)

        Returns:
            The category name or None
        """
        name_lower = ingredient_name.lower()

        # Direct lookup
        if name_lower in self._category_lookup:
            return self._category_lookup[name_lower]

        # Partial match (ingredient contains category keyword)
        for keyword, category in self._category_lookup.items():
            if keyword in name_lower or name_lower in keyword:
                return category

        return None

    def merge_lists(self, lists: list[GroceryList]) -> GroceryList:
        """
        Merge multiple grocery lists into one.

        Args:
            lists: List of GroceryLists to merge

        Returns:
            A merged GroceryList
        """
        # Group items by name
        item_groups: dict[str, list[GroceryItem]] = defaultdict(list)

        all_recipe_ids: list[str] = []

        for glist in lists:
            for item in glist.items:
                item_groups[item.name].append(item)
            for rid in glist.recipe_ids:
                if rid not in all_recipe_ids:
                    all_recipe_ids.append(rid)

        # Merge items
        merged_items: list[GroceryItem] = []

        for name, items in item_groups.items():
            merged = self._merge_items(items)
            merged_items.append(merged)

        merged_items.sort(key=lambda x: (x.category or "zzz", x.name_display.lower()))

        return GroceryList(
            items=merged_items,
            recipe_ids=all_recipe_ids,
        )

    def _merge_items(self, items: list[GroceryItem]) -> GroceryItem:
        """Merge multiple grocery items with the same name."""
        if len(items) == 1:
            return items[0]

        first = items[0]

        # Combine all quantities
        all_quantities: list[tuple[float, str]] = []
        all_form_factors: list[str] = []
        all_recipe_ids: list[str] = []
        all_recipe_names: list[str] = []
        all_notes: list[str] = []

        for item in items:
            all_quantities.extend(item.quantities)

            for ff in item.form_factors:
                if ff not in all_form_factors:
                    all_form_factors.append(ff)

            for rid in item.recipe_ids:
                if rid not in all_recipe_ids:
                    all_recipe_ids.append(rid)

            for rname in item.recipe_names:
                if rname not in all_recipe_names:
                    all_recipe_names.append(rname)

            for note in item.notes:
                if note not in all_notes:
                    all_notes.append(note)

        return GroceryItem(
            name=first.name,
            name_display=first.name_display,
            quantities=all_quantities,
            form_factors=all_form_factors,
            recipe_ids=all_recipe_ids,
            recipe_names=all_recipe_names,
            notes=all_notes,
            category=first.category,
            purchased=all(item.purchased for item in items),
        )


def aggregate_groceries(recipes: list[Recipe]) -> GroceryList:
    """
    Convenience function to aggregate recipes into a grocery list.

    Args:
        recipes: List of recipes

    Returns:
        A GroceryList
    """
    aggregator = GroceryAggregator()
    return aggregator.aggregate(recipes)
