"""
Main CLI interface for MCIPE.

Provides commands for:
- Adding recipes from URLs or search queries
- Managing the current grocery list
- Exporting to various formats
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..models import Recipe
from ..scrapers import URLScraper, ScraperError, RecipeSearcher, RecipeSearchError
from ..parsers import IngredientParser
from ..storage import get_database
from ..aggregators import GroceryAggregator
from ..connectors import ConnectorRegistry
from ..connectors.base import registry as connector_registry

console = Console()


def get_db():
    """Get the database instance."""
    return get_database()


def parse_recipe_ingredients(recipe: Recipe) -> Recipe:
    """Parse all raw ingredients in a recipe."""
    parser = IngredientParser()
    recipe.ingredients = [parser.parse(raw) for raw in recipe.ingredients_raw]
    return recipe


@click.group()
@click.version_option()
def cli():
    """
    MCIPE - Recipe Scraper & Grocery List Manager

    Scrape recipes from the web, extract ingredients, and generate
    consolidated grocery lists. Export to various services.
    """
    pass


# ============================================================================
# Recipe Commands
# ============================================================================


@cli.command("add")
@click.argument("source")
@click.option("--scale", "-s", type=float, default=1.0, help="Scale factor for the recipe")
def add_recipe(source: str, scale: float):
    """
    Add a recipe from a URL.

    SOURCE can be a URL to a recipe page.

    Examples:
        mcipe add https://cooking.nytimes.com/recipes/...
        mcipe add https://www.allrecipes.com/recipe/...
    """
    db = get_db()

    # Check if it looks like a URL
    if not source.startswith(("http://", "https://")):
        console.print(
            "[yellow]That doesn't look like a URL. Use 'mcipe search' to find recipes.[/yellow]"
        )
        return

    # Check if already added
    existing = db.get_recipe_by_url(source)
    if existing:
        console.print(f"[yellow]Recipe already added: {existing.title}[/yellow]")
        if click.confirm("Add to current session anyway?"):
            db.add_to_session(existing.id)
            console.print(f"[green]Added '{existing.title}' to session.[/green]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Fetching recipe...", total=None)

        try:
            with URLScraper() as scraper:
                recipe = scraper.scrape(source)
        except ScraperError as e:
            console.print(f"[red]Error: {e}[/red]")
            return

        progress.add_task("Parsing ingredients...", total=None)
        recipe = parse_recipe_ingredients(recipe)
        recipe.scale_factor = scale

        # Save to database and add to session
        db.save_recipe(recipe)
        db.add_to_session(recipe.id)

    # Display the recipe
    _display_recipe(recipe)
    console.print(f"\n[green]✓ Added '{recipe.title}' to your grocery list![/green]")


@cli.command("search")
@click.argument("query", nargs=-1, required=True)
@click.option("--scale", "-s", type=float, default=1.0, help="Scale factor for the recipe")
@click.option("--auto", "-a", is_flag=True, help="Automatically select first result")
def search_recipe(query: tuple, scale: float, auto: bool):
    """
    Search for a recipe and add it.

    QUERY is what you want to cook (e.g., "chicken tikka masala").

    Examples:
        mcipe search chicken tikka masala
        mcipe search "beef stroganoff"
        mcipe search pasta carbonara --scale 2
    """
    query_str = " ".join(query)
    db = get_db()

    searcher = RecipeSearcher()
    if not searcher.is_available():
        console.print(
            "[yellow]Search requires the 'search' extra.[/yellow]\n"
            "Install with: [bold]pip install mcipe[search][/bold]"
        )
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Searching for '{query_str}'...", total=None)

        try:
            results = searcher.search(query_str, max_results=5)
        except RecipeSearchError as e:
            console.print(f"[red]Search error: {e}[/red]")
            return

        if not results:
            console.print(f"[yellow]No recipes found for '{query_str}'[/yellow]")
            return

    # Display results
    console.print(f"\n[bold]Found {len(results)} recipes:[/bold]\n")

    for i, result in enumerate(results, 1):
        site_badge = "[green]★[/green] " if result["is_preferred"] else ""
        console.print(f"  {i}. {site_badge}[bold]{result['title']}[/bold]")
        console.print(f"     [dim]{result['url'][:70]}...[/dim]" if len(result['url']) > 70 else f"     [dim]{result['url']}[/dim]")

    # Select a recipe
    if auto:
        choice = 1
    else:
        console.print()
        choice_str = click.prompt("Select a recipe (or 0 to cancel)", type=str, default="1")
        try:
            choice = int(choice_str)
        except ValueError:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    if choice == 0 or choice > len(results):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    selected = results[choice - 1]

    # Scrape the selected recipe
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Fetching recipe...", total=None)

        try:
            with URLScraper() as scraper:
                recipe = scraper.scrape(selected["url"])
        except ScraperError as e:
            console.print(f"[red]Error scraping recipe: {e}[/red]")
            return

        progress.add_task("Parsing ingredients...", total=None)
        recipe = parse_recipe_ingredients(recipe)
        recipe.scale_factor = scale

        db.save_recipe(recipe)
        db.add_to_session(recipe.id)

    _display_recipe(recipe)
    console.print(f"\n[green]✓ Added '{recipe.title}' to your grocery list![/green]")


@cli.command("recipes")
def list_recipes():
    """Show all recipes in the current session."""
    db = get_db()
    recipes = db.get_recipes_in_session()

    if not recipes:
        console.print("[yellow]No recipes in current session.[/yellow]")
        console.print("Use 'mcipe add <url>' or 'mcipe search <query>' to add recipes.")
        return

    console.print(f"\n[bold]Recipes in current session ({len(recipes)}):[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Recipe")
    table.add_column("Source")
    table.add_column("Ingredients", justify="right")
    table.add_column("Scale", justify="right")

    for i, recipe in enumerate(recipes, 1):
        table.add_row(
            str(i),
            recipe.title,
            recipe.source_site or "Unknown",
            str(len(recipe.ingredients)),
            f"{recipe.scale_factor}x" if recipe.scale_factor != 1.0 else "-",
        )

    console.print(table)


@cli.command("remove")
@click.argument("recipe_num", type=int)
def remove_recipe(recipe_num: int):
    """
    Remove a recipe from the current session.

    RECIPE_NUM is the recipe number from 'mcipe recipes'.
    """
    db = get_db()
    recipes = db.get_recipes_in_session()

    if not recipes:
        console.print("[yellow]No recipes in current session.[/yellow]")
        return

    if recipe_num < 1 or recipe_num > len(recipes):
        console.print(f"[red]Invalid recipe number. Choose 1-{len(recipes)}.[/red]")
        return

    recipe = recipes[recipe_num - 1]
    db.remove_from_session(recipe.id)
    console.print(f"[green]Removed '{recipe.title}' from session.[/green]")


# ============================================================================
# Grocery List Commands
# ============================================================================


@cli.command("list")
@click.option("--by-category", "-c", is_flag=True, help="Group items by category")
@click.option("--by-recipe", "-r", is_flag=True, help="Show which recipes need each item")
def show_list(by_category: bool, by_recipe: bool):
    """Show the current grocery list."""
    db = get_db()
    recipes = db.get_recipes_in_session()

    if not recipes:
        console.print("[yellow]No recipes added yet.[/yellow]")
        console.print("Use 'mcipe add <url>' or 'mcipe search <query>' to add recipes.")
        return

    # Generate grocery list
    aggregator = GroceryAggregator()
    grocery_list = aggregator.aggregate(recipes)

    if not grocery_list.items:
        console.print("[yellow]No ingredients found.[/yellow]")
        return

    # Display header
    console.print(
        Panel(
            f"[bold]{len(grocery_list.items)} items[/bold] from "
            f"[bold]{len(recipes)} recipes[/bold]",
            title="🛒 Grocery List",
        )
    )

    if by_category:
        _display_list_by_category(grocery_list, by_recipe)
    else:
        _display_list_simple(grocery_list, by_recipe)


def _display_list_simple(grocery_list, show_recipes: bool):
    """Display grocery list in a simple table."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Item")
    table.add_column("Amount")
    if show_recipes:
        table.add_column("For")

    for item in grocery_list.items:
        row = [
            item.name_display,
            item.display_quantity(),
        ]
        if show_recipes:
            row.append(", ".join(item.recipe_names[:2]) + ("..." if len(item.recipe_names) > 2 else ""))

        # Add form factor if present
        if item.form_factors:
            row[0] += f" [dim]({', '.join(item.form_factors)})[/dim]"

        table.add_row(*row)

    console.print(table)


def _display_list_by_category(grocery_list, show_recipes: bool):
    """Display grocery list grouped by category."""
    # Group by category
    by_category: dict[str, list] = {}
    for item in grocery_list.items:
        cat = item.category or "Other"
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(item)

    for category in sorted(by_category.keys()):
        items = by_category[category]
        console.print(f"\n[bold blue]{category.upper()}[/bold blue]")

        for item in items:
            qty = item.display_quantity()
            line = f"  • {item.name_display}"
            if qty:
                line += f" — {qty}"
            if item.form_factors:
                line += f" [dim]({', '.join(item.form_factors)})[/dim]"
            if show_recipes:
                recipes = ", ".join(item.recipe_names[:2])
                if len(item.recipe_names) > 2:
                    recipes += "..."
                line += f" [dim italic]for {recipes}[/dim italic]"

            console.print(line)


@cli.command("clear")
@click.confirmation_option(prompt="Clear all recipes from current session?")
def clear_session():
    """Clear all recipes from the current session."""
    db = get_db()
    db.clear_session()
    console.print("[green]Session cleared.[/green]")


# ============================================================================
# Export Commands
# ============================================================================


@cli.command("export")
@click.option(
    "--format",
    "-f",
    "export_format",
    type=click.Choice(["text", "markdown", "json"]),
    default="text",
    help="Export format",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_list(export_format: str, output: Optional[str]):
    """
    Export the grocery list.

    Formats:
        text     - Plain text (default)
        markdown - Markdown with checkboxes
        json     - Full JSON export
    """
    db = get_db()
    recipes = db.get_recipes_in_session()

    if not recipes:
        console.print("[yellow]No recipes to export.[/yellow]")
        return

    # Generate grocery list
    aggregator = GroceryAggregator()
    grocery_list = aggregator.aggregate(recipes)

    if export_format == "json":
        # Full JSON export
        output_path = Path(output) if output else Path("grocery_list.json")
        db.export_to_json(output_path)
        console.print(f"[green]Exported to {output_path}[/green]")

    elif export_format == "markdown":
        connector = connector_registry.create("markdown")
        content = connector.export(grocery_list)

        if output:
            Path(output).write_text(content)
            console.print(f"[green]Exported to {output}[/green]")
        else:
            console.print(content)

    else:  # text
        connector = connector_registry.create("plaintext")
        content = connector.export(grocery_list)

        if output:
            Path(output).write_text(content)
            console.print(f"[green]Exported to {output}[/green]")
        else:
            console.print(content)


@cli.command("connectors")
def list_connectors():
    """List available export connectors."""
    connectors = connector_registry.list_connectors()

    console.print("\n[bold]Available Connectors:[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Description")

    for c in connectors:
        table.add_row(c["display_name"], c["description"])

    console.print(table)
    console.print("\n[dim]More connectors coming soon (Google Keep, etc.)[/dim]")


# ============================================================================
# Utility Commands
# ============================================================================


@cli.command("info")
@click.argument("url")
def recipe_info(url: str):
    """
    Show information about a recipe without adding it.

    URL is the recipe URL to inspect.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Fetching recipe...", total=None)

        try:
            with URLScraper() as scraper:
                recipe = scraper.scrape(url)
        except ScraperError as e:
            console.print(f"[red]Error: {e}[/red]")
            return

        progress.add_task("Parsing ingredients...", total=None)
        recipe = parse_recipe_ingredients(recipe)

    _display_recipe(recipe, show_instructions=True)


def _display_recipe(recipe: Recipe, show_instructions: bool = False):
    """Display a recipe in a nice format."""
    # Header
    console.print(Panel(f"[bold]{recipe.title}[/bold]", subtitle=recipe.source_site))

    # Metadata
    meta_parts = []
    if recipe.servings_text:
        meta_parts.append(f"Servings: {recipe.servings_text}")
    if recipe.prep_time_minutes:
        meta_parts.append(f"Prep: {recipe.prep_time_minutes}min")
    if recipe.cook_time_minutes:
        meta_parts.append(f"Cook: {recipe.cook_time_minutes}min")
    if recipe.total_time_minutes:
        meta_parts.append(f"Total: {recipe.total_time_minutes}min")

    if meta_parts:
        console.print("[dim]" + " | ".join(meta_parts) + "[/dim]")

    # Ingredients
    console.print(f"\n[bold]Ingredients ({len(recipe.ingredients)}):[/bold]")

    for ing in recipe.ingredients:
        parts = []
        if ing.quantity:
            if ing.quantity_max and ing.quantity_max != ing.quantity:
                parts.append(f"{ing.quantity}-{ing.quantity_max}")
            else:
                # Format nicely
                if ing.quantity == int(ing.quantity):
                    parts.append(str(int(ing.quantity)))
                else:
                    parts.append(str(ing.quantity))

        if ing.unit:
            parts.append(ing.unit)

        parts.append(ing.name)

        if ing.form_factor:
            parts.append(f"[dim]({ing.form_factor})[/dim]")

        if ing.preparation:
            parts.append(f"[italic dim], {ing.preparation}[/italic dim]")

        if ing.optional:
            parts.append("[yellow](optional)[/yellow]")

        console.print(f"  • {' '.join(parts)}")

    # Instructions (optional)
    if show_instructions and recipe.instructions:
        console.print(f"\n[bold]Instructions:[/bold]")
        for i, step in enumerate(recipe.instructions, 1):
            console.print(f"  {i}. {step[:200]}{'...' if len(step) > 200 else ''}")


if __name__ == "__main__":
    cli()
