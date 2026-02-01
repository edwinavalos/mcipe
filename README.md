# MCIPE - Recipe Scraper & Grocery List Manager

A command-line tool for scraping recipes from the web, extracting and parsing ingredients, and generating consolidated grocery lists. Designed for meal planning with support for multiple output connectors (Google Keep, Target, etc. coming soon).

## Features

- **Recipe Scraping**: Fetch recipes from 400+ supported websites including:
  - NYT Cooking
  - AllRecipes
  - Food Network
  - Serious Eats
  - Epicurious
  - And many more...

- **Smart Ingredient Parsing**: Automatically extracts:
  - Quantities (including fractions and ranges)
  - Units (normalized for consistency)
  - Ingredient names
  - Preparation notes (diced, minced, etc.)
  - Form factors (shredded, block, etc.)

- **Grocery List Aggregation**:
  - Combines ingredients from multiple recipes
  - Tracks form factor differences (shredded vs block cheese)
  - Categorizes items (produce, dairy, meat, pantry, etc.)
  - Shows which recipes need each ingredient

- **Recipe Search**: Search for recipes by name and automatically scrape them

- **Multiple Export Formats**:
  - Plain text
  - Markdown (with checkboxes)
  - JSON (full data export)
  - Connector interface for future integrations

## Installation

```bash
# Basic installation
pip install -e .

# With search capability
pip install -e ".[search]"

# With development tools
pip install -e ".[dev]"
```

## Quick Start

### Add a recipe from a URL

```bash
mcipe add https://cooking.nytimes.com/recipes/1234-chicken-tikka-masala
```

### Search for a recipe

```bash
mcipe search chicken tikka masala
```

### View your grocery list

```bash
# Simple list
mcipe list

# Grouped by category
mcipe list --by-category

# Show which recipes need each item
mcipe list --by-recipe
```

### See recipes in your session

```bash
mcipe recipes
```

### Export your list

```bash
# To clipboard-friendly text
mcipe export

# As markdown
mcipe export --format markdown

# To a file
mcipe export --format markdown -o shopping.md

# Full JSON export
mcipe export --format json -o data.json
```

### Clear your session

```bash
mcipe clear
```

## Commands

| Command | Description |
|---------|-------------|
| `mcipe add <url>` | Add a recipe from a URL |
| `mcipe search <query>` | Search for and add a recipe |
| `mcipe recipes` | List recipes in current session |
| `mcipe remove <num>` | Remove a recipe from session |
| `mcipe list` | Show the grocery list |
| `mcipe export` | Export the grocery list |
| `mcipe clear` | Clear the current session |
| `mcipe info <url>` | Show recipe info without adding |
| `mcipe connectors` | List available export connectors |

## Options

### Scaling Recipes

Double a recipe:
```bash
mcipe add https://example.com/recipe --scale 2
mcipe search "lasagna" --scale 1.5
```

### List Display Options

```bash
# Group by grocery store section
mcipe list --by-category

# Show which recipes need each ingredient
mcipe list --by-recipe

# Both
mcipe list -c -r
```

## Architecture

```
mcipe/
├── src/mcipe/
│   ├── models.py          # Data models (Recipe, Ingredient, GroceryList)
│   ├── scrapers/          # Recipe scraping (URL and search)
│   ├── parsers/           # Ingredient parsing and normalization
│   ├── storage/           # SQLite database persistence
│   ├── aggregators/       # Grocery list generation
│   ├── connectors/        # Export connectors (text, markdown, future: Keep)
│   └── cli/               # Command-line interface
├── tests/                 # Test suite
└── data/                  # Local database storage
```

## Data Storage

MCIPE stores data in `~/.mcipe/mcipe.db` (SQLite). You can export/import data as JSON for backup or sharing.

## Future Plans

- [ ] Google Keep connector (unofficial API)
- [ ] Target.com integration
- [ ] Todoist connector
- [ ] Unit conversion and aggregation
- [ ] Pantry tracking (what you already have)
- [ ] Meal planning calendar
- [ ] Cost estimation

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
ruff check src tests
```

## License

MIT
