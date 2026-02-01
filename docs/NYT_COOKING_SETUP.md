# NYT Cooking Setup Guide

This guide walks you through authenticating with NYT Cooking and using MCIPE to pull recipes and generate grocery lists.

## Prerequisites

1. **NYT Cooking subscription** - You need an active subscription to cooking.nytimes.com
2. **Python 3.10+** installed
3. **MCIPE installed** with NYT support:

```bash
cd /home/user/mcipe
pip install -e ".[nyt]"
```

## Step 1: Get Your NYT Credentials

You need to extract two pieces of information from your browser:

### 1.1 Get the NYT-S Cookie

1. Open your browser and log into https://cooking.nytimes.com
2. Open Developer Tools:
   - **Chrome/Edge**: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
   - **Firefox**: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
3. Go to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox)
4. In the left sidebar, expand **Cookies** → click on `https://cooking.nytimes.com`
5. Find the cookie named **`NYT-S`**
6. Copy the entire **Value** (it's a long string)

### 1.2 Get Your User ID

1. In the same cookies list, find the cookie named **`regi_cookie`**
2. Look at its value - find the part that says `regi_id=XXXXXXXX`
3. Copy just the number (e.g., `12345678`)

## Step 2: Configure Authentication

Run the nytc auth command:

```bash
nytc auth
```

You'll be prompted to enter:
1. Your **NYT-S cookie value** (paste the long string)
2. Your **User ID** (the number from regi_id)

The credentials are saved to `~/.config/nytc/config.json`

## Step 3: Verify Authentication

```bash
mcipe nyt status
```

You should see:
```
✓ NYT Cooking authentication configured.
  User ID: 12345678

To update credentials, run: nytc auth
```

## Step 4: Test Recipe Fetching

### Search NYT Cooking

```bash
mcipe nyt search chicken parmesan
```

This should show a list of recipes.

### View Your Saved Recipes

```bash
mcipe nyt saved
```

This shows recipes from your NYT Cooking recipe box.

### Add a Recipe to Your Grocery List

```bash
# Using a specific NYT Cooking URL
mcipe add https://cooking.nytimes.com/recipes/1015819-marcella-hazans-tomato-sauce

# Or try another recipe
mcipe add https://cooking.nytimes.com/recipes/1022076-vegetable-fried-rice
```

## Step 5: Build a Grocery List

### Add Multiple Recipes

```bash
# Add a few recipes for a meal plan
mcipe add https://cooking.nytimes.com/recipes/1015819-marcella-hazans-tomato-sauce
mcipe add https://cooking.nytimes.com/recipes/1017089-roasted-broccoli-with-garlic
mcipe add https://cooking.nytimes.com/recipes/1021934-peanut-butter-cookies
```

### View Your Recipes

```bash
mcipe recipes
```

### Generate the Grocery List

```bash
# Simple list
mcipe list

# Grouped by category (produce, dairy, meat, etc.)
mcipe list --by-category

# Show which recipe needs each ingredient
mcipe list --by-recipe
```

### Export the Grocery List

```bash
# Export to markdown (great for notes apps)
mcipe export --format markdown -o shopping.md

# Export to plain text
mcipe export --format text -o shopping.txt

# Export to JSON (includes all data)
mcipe export --format json -o shopping.json
```

## Step 6: Clear and Start Over

```bash
# Clear current session (keeps recipes in database)
mcipe clear

# Start adding new recipes for next shopping trip
mcipe add https://cooking.nytimes.com/recipes/...
```

## Troubleshooting

### "NYT Authentication required" error

Your cookie may have expired. Re-run:
```bash
nytc auth
```

### "NYT Cooking support not installed" error

Install the NYT extra:
```bash
pip install -e ".[nyt]"
```

### Recipe not found or 404 error

- Make sure the URL is a valid NYT Cooking recipe URL
- Check that you're logged into NYT Cooking in your browser
- Try refreshing your cookie if it's been a while

## Example Session

```bash
# Check auth
$ mcipe nyt status
✓ NYT Cooking authentication configured.

# Search for recipes
$ mcipe nyt search pasta carbonara
Found 8 recipes on NYT Cooking:
  1. Pasta Carbonara - Kay Chun
  2. Spaghetti Carbonara - ...

# Add recipes for Italian dinner night
$ mcipe add https://cooking.nytimes.com/recipes/12965-spaghetti-carbonara
✓ Added 'Spaghetti Carbonara' to your grocery list!

$ mcipe add https://cooking.nytimes.com/recipes/1015178-classic-caesar-salad
✓ Added 'Classic Caesar Salad' to your grocery list!

# View what we're making
$ mcipe recipes
Recipes in current session (2):
  1. Spaghetti Carbonara    cooking.nytimes.com    8 ingredients
  2. Classic Caesar Salad   cooking.nytimes.com    11 ingredients

# Generate shopping list
$ mcipe list --by-category

## DAIRY
  • eggs — 4
  • Parmesan cheese — 1 cup (grated)
  • Pecorino Romano — 0.5 cup

## MEAT
  • guanciale — 8 oz
  • anchovy fillets — 2

## PANTRY
  • spaghetti — 1 lb
  • olive oil — 3 tbsp
  • black pepper — to taste
  ...

# Export for shopping
$ mcipe export --format markdown -o italian_dinner.md
Exported to italian_dinner.md
```

## Notes

- Credentials are stored at `~/.config/nytc/config.json`
- Recipes are cached in `~/.mcipe/mcipe.db`
- The NYT-S cookie typically expires after a few weeks
