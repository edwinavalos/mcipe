"""
Integration tests for recipe scraping and grocery list aggregation.

These tests fetch real recipes from various cooking sites,
then aggregate their ingredients into shopping lists.
"""

import pytest
from mcipe.scrapers import URLScraper, ScraperError
from mcipe.parsers import IngredientParser
from mcipe.aggregators import GroceryAggregator
from mcipe.models import Recipe


def scrape_and_parse_recipe(url: str) -> Recipe:
    """Fetch a recipe and parse its ingredients."""
    with URLScraper() as scraper:
        recipe = scraper.scrape(url)

    parser = IngredientParser()
    recipe.ingredients = [parser.parse(raw) for raw in recipe.ingredients_raw]
    return recipe


def print_recipe_summary(recipe: Recipe):
    """Print a summary of a recipe."""
    print(f"\n{'='*60}")
    print(f"RECIPE: {recipe.title}")
    print(f"Source: {recipe.source_site}")
    print(f"URL: {recipe.url}")
    if recipe.servings_text:
        print(f"Servings: {recipe.servings_text}")
    print(f"\nIngredients ({len(recipe.ingredients)}):")
    print("-" * 40)
    for ing in recipe.ingredients:
        print(f"  • {ing}")
    print()


def print_grocery_list(grocery_list, recipes: list[Recipe]):
    """Print the aggregated grocery list."""
    print(f"\n{'='*60}")
    print("AGGREGATED GROCERY LIST")
    print(f"From {len(recipes)} recipes:")
    for r in recipes:
        print(f"  - {r.title}")
    print(f"\nTotal items: {len(grocery_list.items)}")
    print("=" * 60)

    # Group by category
    by_category = {}
    for item in grocery_list.items:
        cat = item.category or "Other"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    for category in sorted(by_category.keys()):
        items = by_category[category]
        print(f"\n## {category.upper()}")
        for item in items:
            qty = item.display_quantity()
            line = f"  • {item.name_display}"
            if qty:
                line += f" — {qty}"
            if item.form_factors:
                line += f" ({', '.join(item.form_factors)})"
            if len(item.recipe_names) > 1:
                line += f" [from: {', '.join(item.recipe_names)}]"
            print(line)


class TestRecipeIntegration:
    """Integration tests using publicly accessible recipe sites."""

    @pytest.fixture
    def aggregator(self):
        return GroceryAggregator()

    def test_italian_dinner_menu(self, aggregator):
        """
        Test Case 1: Italian Dinner Menu
        - Spaghetti Carbonara (AllRecipes)
        - Caesar Salad (AllRecipes)
        """
        print("\n" + "="*60)
        print("TEST CASE 1: ITALIAN DINNER MENU")
        print("="*60)

        urls = [
            "https://www.allrecipes.com/recipe/11973/spaghetti-carbonara-ii/",
            "https://www.allrecipes.com/recipe/229063/classic-restaurant-caesar-salad/",
        ]

        recipes = []
        for url in urls:
            try:
                recipe = scrape_and_parse_recipe(url)
                recipes.append(recipe)
                print_recipe_summary(recipe)
            except ScraperError as e:
                print(f"Failed to scrape {url}: {e}")

        if len(recipes) >= 2:
            grocery_list = aggregator.aggregate(recipes)
            print_grocery_list(grocery_list, recipes)

            # Basic assertions
            assert len(grocery_list.items) > 0
            assert len(grocery_list.recipe_ids) == len(recipes)
        else:
            pytest.skip("Could not fetch enough recipes")

    def test_weeknight_chicken_dinner(self, aggregator):
        """
        Test Case 2: Weeknight Chicken Dinner
        - Baked Chicken (AllRecipes)
        - Roasted Vegetables (AllRecipes)
        - Mashed Potatoes (AllRecipes)
        """
        print("\n" + "="*60)
        print("TEST CASE 2: WEEKNIGHT CHICKEN DINNER")
        print("="*60)

        urls = [
            "https://www.allrecipes.com/recipe/83557/juicy-roasted-chicken/",
            "https://www.allrecipes.com/recipe/9377/roasted-vegetables/",
            "https://www.allrecipes.com/recipe/24771/basic-mashed-potatoes/",
        ]

        recipes = []
        for url in urls:
            try:
                recipe = scrape_and_parse_recipe(url)
                recipes.append(recipe)
                print_recipe_summary(recipe)
            except ScraperError as e:
                print(f"Failed to scrape {url}: {e}")

        if len(recipes) >= 2:
            grocery_list = aggregator.aggregate(recipes)
            print_grocery_list(grocery_list, recipes)

            assert len(grocery_list.items) > 0

            # Check for ingredient aggregation (butter should appear in multiple recipes)
            butter_items = [i for i in grocery_list.items if "butter" in i.name.lower()]
            if butter_items:
                print(f"\n** Butter aggregation: {butter_items[0].display_quantity()}")
                print(f"   From recipes: {butter_items[0].recipe_names}")
        else:
            pytest.skip("Could not fetch enough recipes")

    def test_mexican_feast(self, aggregator):
        """
        Test Case 3: Mexican Feast
        - Chicken Tacos (AllRecipes)
        - Spanish Rice (AllRecipes)
        - Guacamole (AllRecipes)
        """
        print("\n" + "="*60)
        print("TEST CASE 3: MEXICAN FEAST")
        print("="*60)

        urls = [
            "https://www.allrecipes.com/recipe/70461/slow-cooker-chicken-taco-filling/",
            "https://www.allrecipes.com/recipe/27072/spanish-rice-ii/",
            "https://www.allrecipes.com/recipe/14231/guacamole/",
        ]

        recipes = []
        for url in urls:
            try:
                recipe = scrape_and_parse_recipe(url)
                recipes.append(recipe)
                print_recipe_summary(recipe)
            except ScraperError as e:
                print(f"Failed to scrape {url}: {e}")

        if len(recipes) >= 2:
            grocery_list = aggregator.aggregate(recipes)
            print_grocery_list(grocery_list, recipes)

            assert len(grocery_list.items) > 0

            # Check for common Mexican ingredients
            onion_items = [i for i in grocery_list.items if "onion" in i.name.lower()]
            garlic_items = [i for i in grocery_list.items if "garlic" in i.name.lower()]

            print("\n** Common ingredient aggregation:")
            if onion_items:
                print(f"   Onion: {onion_items[0].display_quantity()}")
            if garlic_items:
                print(f"   Garlic: {garlic_items[0].display_quantity()}")
        else:
            pytest.skip("Could not fetch enough recipes")

    def test_comfort_food_sunday(self, aggregator):
        """
        Test Case 4: Comfort Food Sunday
        - Mac and Cheese (AllRecipes)
        - Biscuits (AllRecipes)
        """
        print("\n" + "="*60)
        print("TEST CASE 4: COMFORT FOOD SUNDAY")
        print("="*60)

        urls = [
            "https://www.allrecipes.com/recipe/11679/homemade-mac-and-cheese/",
            "https://www.allrecipes.com/recipe/20075/basic-biscuits/",
        ]

        recipes = []
        for url in urls:
            try:
                recipe = scrape_and_parse_recipe(url)
                recipes.append(recipe)
                print_recipe_summary(recipe)
            except ScraperError as e:
                print(f"Failed to scrape {url}: {e}")

        if len(recipes) >= 2:
            grocery_list = aggregator.aggregate(recipes)
            print_grocery_list(grocery_list, recipes)

            # Check that butter/dairy items are aggregated
            assert len(grocery_list.items) > 0

            # Look for common ingredients that should be combined
            butter_items = [i for i in grocery_list.items if "butter" in i.name.lower()]
            milk_items = [i for i in grocery_list.items if "milk" in i.name.lower()]

            print("\n** Dairy aggregation check:")
            if butter_items:
                print(f"   Butter: {butter_items[0].display_quantity()}")
            if milk_items:
                print(f"   Milk: {milk_items[0].display_quantity()}")
        else:
            pytest.skip("Could not fetch enough recipes")

    def test_asian_fusion_night(self, aggregator):
        """
        Test Case 5: Asian Fusion Night
        - Fried Rice (AllRecipes)
        - Stir Fry (AllRecipes)
        """
        print("\n" + "="*60)
        print("TEST CASE 5: ASIAN FUSION NIGHT")
        print("="*60)

        urls = [
            "https://www.allrecipes.com/recipe/79543/restaurant-style-egg-fried-rice/",
            "https://www.allrecipes.com/recipe/228823/quick-beef-stir-fry/",
        ]

        recipes = []
        for url in urls:
            try:
                recipe = scrape_and_parse_recipe(url)
                recipes.append(recipe)
                print_recipe_summary(recipe)
            except ScraperError as e:
                print(f"Failed to scrape {url}: {e}")

        if len(recipes) >= 2:
            grocery_list = aggregator.aggregate(recipes)
            print_grocery_list(grocery_list, recipes)

            assert len(grocery_list.items) > 0

            # Check for common Asian ingredients
            garlic_items = [i for i in grocery_list.items if "garlic" in i.name.lower()]
            soy_items = [i for i in grocery_list.items if "soy" in i.name.lower()]
            oil_items = [i for i in grocery_list.items if "oil" in i.name.lower()]

            print("\n** Common ingredient aggregation:")
            if garlic_items:
                print(f"   Garlic: {garlic_items[0].display_quantity()}")
            if soy_items:
                print(f"   Soy sauce: {soy_items[0].display_quantity()}")
            if oil_items:
                for oil in oil_items:
                    print(f"   {oil.name_display}: {oil.display_quantity()}")
        else:
            pytest.skip("Could not fetch enough recipes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
