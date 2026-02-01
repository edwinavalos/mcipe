# Google Keep Setup Guide

This guide walks you through configuring MCIPE to export grocery lists to Google Keep.

## Prerequisites

1. **Google Account** - A standard Google account
2. **Python 3.10+** installed
3. **MCIPE installed** with Google Keep support:

```bash
cd /home/user/mcipe
pip install -e ".[gkeep]"
```

## Important Security Note

The `gkeepapi` library uses an unofficial Google Keep API that requires a **master token** for your account. This token has full account access, similar to your password.

**Recommendations:**
- Use an App Password if you have 2-Step Verification enabled
- Only use this on trusted devices
- Never share your master token

## Step 1: Create an App Password (Recommended)

If you have 2-Step Verification enabled (recommended), you need to create an App Password:

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Sign in if prompted
3. Under "Select app", choose **Other (Custom name)**
4. Enter a name like "MCIPE" or "gkeepapi"
5. Click **Generate**
6. **Copy the 16-character password** (it will only be shown once)

This app password will be used as your "master token".

## Step 2: Configure Authentication

Run the auth command:

```bash
mcipe gkeep auth
```

You'll be prompted to enter:
1. Your **Google account email** (e.g., yourname@gmail.com)
2. Your **master token** (the app password from Step 1)

The credentials are saved to `~/.config/mcipe/gkeep_config.json`

## Step 3: Verify Authentication

```bash
mcipe gkeep status
```

You should see:
```
✓ Google Keep authentication configured.
  Email: yourname@gmail.com

To update credentials, run: mcipe gkeep auth
```

## Step 4: Test with a Recipe

### Add a Recipe

```bash
# Add any recipe URL
mcipe add https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/

# Or search for one
mcipe search chocolate chip cookies
```

### Push to Google Keep

```bash
# Create a new list in Google Keep
mcipe gkeep push

# Or with a custom name
mcipe gkeep push --name "Weekend Baking"

# Update an existing list with the same name
mcipe gkeep push --name "Weekly Shopping" --update
```

### View Your Lists

```bash
# See all lists in your Google Keep
mcipe gkeep lists
```

## Step 5: Full Workflow Example

```bash
# Check auth status
$ mcipe gkeep status
✓ Google Keep authentication configured.

# Add some recipes
$ mcipe add https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/
✓ Added 'Best Chocolate Chip Cookies' to your grocery list!

$ mcipe add https://www.allrecipes.com/recipe/23891/grilled-cheese-sandwich/
✓ Added 'Grilled Cheese Sandwich' to your grocery list!

# View what we're making
$ mcipe recipes
Recipes in current session (2):
  1. Best Chocolate Chip Cookies    AllRecipes    10 ingredients
  2. Grilled Cheese Sandwich        AllRecipes    4 ingredients

# Generate grocery list
$ mcipe list --by-category

## DAIRY
  • butter — 1 cup
  • cheese — 4 slices

## PANTRY
  • flour — 2.25 cup
  • sugar — 0.75 cup
  • brown sugar — 0.75 cup
  ...

# Push to Google Keep
$ mcipe gkeep push --name "Weekend Cooking"
✓ Created 'Weekend Cooking' in Google Keep!
  Items: 12
  Recipes: 2

Open Google Keep to see your shopping list.
```

## Troubleshooting

### "Google Keep support not installed" error

Install the Google Keep extra:
```bash
pip install -e ".[gkeep]"
```

### "Authentication failed" error

1. **If using 2-Step Verification**: Make sure you created an App Password (not your regular password)
2. **Check the email**: Ensure you're using the correct Google account email
3. **Regenerate App Password**: If it's not working, create a new App Password and try again
4. **Less Secure Apps**: If not using 2-Step Verification, you may need to enable "Less secure app access" in your Google account (not recommended)

### Lists not appearing in Google Keep

- Wait a few seconds and refresh Google Keep
- Try running `mcipe gkeep lists` to verify the connection
- Check if the list was created with a different name

### "Session expired" errors

The library saves session state to resume connections. If you get session errors:

```bash
# Re-authenticate
mcipe gkeep auth
```

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Config | `~/.config/mcipe/gkeep_config.json` | Email and master token |
| State | `~/.config/mcipe/gkeep_state.json` | Session state (auto-managed) |
| Database | `~/.mcipe/mcipe.db` | Recipes and grocery lists |

## Notes

- Credentials are stored at `~/.config/mcipe/gkeep_config.json` (outside repo)
- The session state is cached to avoid frequent re-authentication
- Google Keep doesn't have an official API, so `gkeepapi` uses the internal mobile API
- The library is actively maintained but not officially supported by Google

## Available Commands

| Command | Description |
|---------|-------------|
| `mcipe gkeep status` | Check authentication status |
| `mcipe gkeep auth` | Configure authentication |
| `mcipe gkeep push` | Push grocery list to Google Keep |
| `mcipe gkeep push --name "Name"` | Push with custom list name |
| `mcipe gkeep push --update` | Update existing list with same name |
| `mcipe gkeep lists` | Show your Google Keep lists |

## Combining with NYT Cooking

If you also have NYT Cooking set up, you can pull recipes from NYT and push to Google Keep:

```bash
# Add NYT Cooking recipes
mcipe add https://cooking.nytimes.com/recipes/1015819-marcella-hazans-tomato-sauce
mcipe add https://cooking.nytimes.com/recipes/1017089-roasted-broccoli-with-garlic

# Push to Google Keep
mcipe gkeep push --name "Italian Dinner"
```
