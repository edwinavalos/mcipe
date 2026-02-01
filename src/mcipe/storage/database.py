"""
Data storage layer using SQLite and JSON.

This module handles persisting recipes, ingredients, and grocery lists
to a local SQLite database with JSON export capabilities.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import GroceryItem, GroceryList, ParsedIngredient, Recipe


class Database:
    """
    SQLite database for storing recipes and grocery lists.
    """

    DEFAULT_DB_PATH = Path.home() / ".mcipe" / "mcipe.db"

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the database.

        Args:
            db_path: Path to the SQLite database file. Defaults to ~/.mcipe/mcipe.db
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                -- Recipes table
                CREATE TABLE IF NOT EXISTS recipes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT,
                    source_site TEXT,
                    description TEXT,
                    servings INTEGER,
                    servings_text TEXT,
                    prep_time_minutes INTEGER,
                    cook_time_minutes INTEGER,
                    total_time_minutes INTEGER,
                    scale_factor REAL DEFAULT 1.0,
                    added_at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );

                -- Ingredients table (linked to recipes)
                CREATE TABLE IF NOT EXISTS ingredients (
                    id TEXT PRIMARY KEY,
                    recipe_id TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    name TEXT NOT NULL,
                    name_normalized TEXT,
                    quantity REAL,
                    quantity_max REAL,
                    unit TEXT,
                    form_factor TEXT,
                    preparation TEXT,
                    optional INTEGER DEFAULT 0,
                    data_json TEXT NOT NULL,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
                );

                -- Grocery lists table
                CREATE TABLE IF NOT EXISTS grocery_lists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );

                -- Grocery items table (linked to lists)
                CREATE TABLE IF NOT EXISTS grocery_items (
                    id TEXT PRIMARY KEY,
                    list_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    name_display TEXT NOT NULL,
                    category TEXT,
                    purchased INTEGER DEFAULT 0,
                    data_json TEXT NOT NULL,
                    FOREIGN KEY (list_id) REFERENCES grocery_lists(id) ON DELETE CASCADE
                );

                -- Active session table (tracks current shopping session)
                CREATE TABLE IF NOT EXISTS session (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_ingredients_recipe_id ON ingredients(recipe_id);
                CREATE INDEX IF NOT EXISTS idx_ingredients_name_normalized ON ingredients(name_normalized);
                CREATE INDEX IF NOT EXISTS idx_grocery_items_list_id ON grocery_items(list_id);
                CREATE INDEX IF NOT EXISTS idx_recipes_url ON recipes(url);
            """
            )

    @contextmanager
    def _get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # Recipe operations

    def save_recipe(self, recipe: Recipe) -> str:
        """
        Save a recipe to the database.

        Args:
            recipe: The Recipe to save

        Returns:
            The recipe ID
        """
        with self._get_connection() as conn:
            # Save recipe
            conn.execute(
                """
                INSERT OR REPLACE INTO recipes
                (id, title, url, source_site, description, servings, servings_text,
                 prep_time_minutes, cook_time_minutes, total_time_minutes, scale_factor,
                 added_at, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    recipe.id,
                    recipe.title,
                    recipe.url,
                    recipe.source_site,
                    recipe.description,
                    recipe.servings,
                    recipe.servings_text,
                    recipe.prep_time_minutes,
                    recipe.cook_time_minutes,
                    recipe.total_time_minutes,
                    recipe.scale_factor,
                    recipe.added_at.isoformat(),
                    recipe.model_dump_json(),
                ),
            )

            # Delete existing ingredients and re-save
            conn.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe.id,))

            # Save ingredients
            for ingredient in recipe.ingredients:
                conn.execute(
                    """
                    INSERT INTO ingredients
                    (id, recipe_id, original_text, name, name_normalized, quantity,
                     quantity_max, unit, form_factor, preparation, optional, data_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        ingredient.id,
                        recipe.id,
                        ingredient.original_text,
                        ingredient.name,
                        ingredient.name_normalized,
                        ingredient.quantity,
                        ingredient.quantity_max,
                        ingredient.unit,
                        ingredient.form_factor,
                        ingredient.preparation,
                        1 if ingredient.optional else 0,
                        ingredient.model_dump_json(),
                    ),
                )

        return recipe.id

    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """
        Get a recipe by ID.

        Args:
            recipe_id: The recipe ID

        Returns:
            The Recipe or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM recipes WHERE id = ?", (recipe_id,)
            ).fetchone()
            if row:
                return Recipe.model_validate_json(row["data_json"])
            return None

    def get_recipe_by_url(self, url: str) -> Optional[Recipe]:
        """
        Get a recipe by URL.

        Args:
            url: The recipe URL

        Returns:
            The Recipe or None if not found
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM recipes WHERE url = ?", (url,)
            ).fetchone()
            if row:
                return Recipe.model_validate_json(row["data_json"])
            return None

    def get_all_recipes(self) -> list[Recipe]:
        """Get all recipes."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT data_json FROM recipes ORDER BY added_at DESC"
            ).fetchall()
            return [Recipe.model_validate_json(row["data_json"]) for row in rows]

    def delete_recipe(self, recipe_id: str) -> bool:
        """
        Delete a recipe.

        Args:
            recipe_id: The recipe ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
            return cursor.rowcount > 0

    def get_recipes_in_session(self) -> list[Recipe]:
        """Get all recipes in the current session."""
        recipe_ids = self.get_session_recipe_ids()
        recipes = []
        for rid in recipe_ids:
            recipe = self.get_recipe(rid)
            if recipe:
                recipes.append(recipe)
        return recipes

    # Session operations

    def get_session_recipe_ids(self) -> list[str]:
        """Get recipe IDs in the current session."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM session WHERE key = 'recipe_ids'"
            ).fetchone()
            if row:
                return json.loads(row["value"])
            return []

    def add_to_session(self, recipe_id: str):
        """Add a recipe to the current session."""
        ids = self.get_session_recipe_ids()
        if recipe_id not in ids:
            ids.append(recipe_id)
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO session (key, value) VALUES ('recipe_ids', ?)",
                    (json.dumps(ids),),
                )

    def remove_from_session(self, recipe_id: str):
        """Remove a recipe from the current session."""
        ids = self.get_session_recipe_ids()
        if recipe_id in ids:
            ids.remove(recipe_id)
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO session (key, value) VALUES ('recipe_ids', ?)",
                    (json.dumps(ids),),
                )

    def clear_session(self):
        """Clear the current session."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM session WHERE key = 'recipe_ids'")

    # Grocery list operations

    def save_grocery_list(self, grocery_list: GroceryList) -> str:
        """Save a grocery list."""
        grocery_list.updated_at = datetime.now()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO grocery_lists
                (id, name, created_at, updated_at, data_json)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    grocery_list.id,
                    grocery_list.name,
                    grocery_list.created_at.isoformat(),
                    grocery_list.updated_at.isoformat(),
                    grocery_list.model_dump_json(),
                ),
            )

            # Delete existing items and re-save
            conn.execute("DELETE FROM grocery_items WHERE list_id = ?", (grocery_list.id,))

            for item in grocery_list.items:
                conn.execute(
                    """
                    INSERT INTO grocery_items
                    (id, list_id, name, name_display, category, purchased, data_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        item.id,
                        grocery_list.id,
                        item.name,
                        item.name_display,
                        item.category,
                        1 if item.purchased else 0,
                        item.model_dump_json(),
                    ),
                )

        return grocery_list.id

    def get_grocery_list(self, list_id: str) -> Optional[GroceryList]:
        """Get a grocery list by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM grocery_lists WHERE id = ?", (list_id,)
            ).fetchone()
            if row:
                return GroceryList.model_validate_json(row["data_json"])
            return None

    def get_current_grocery_list(self) -> Optional[GroceryList]:
        """Get the current (most recent) grocery list."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json FROM grocery_lists ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            if row:
                return GroceryList.model_validate_json(row["data_json"])
            return None

    def delete_grocery_list(self, list_id: str) -> bool:
        """Delete a grocery list."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM grocery_lists WHERE id = ?", (list_id,))
            return cursor.rowcount > 0

    # Export operations

    def export_to_json(self, filepath: Path):
        """
        Export all data to a JSON file.

        Args:
            filepath: Path to export to
        """
        data = {
            "recipes": [r.model_dump() for r in self.get_all_recipes()],
            "session_recipe_ids": self.get_session_recipe_ids(),
            "grocery_list": None,
        }

        current_list = self.get_current_grocery_list()
        if current_list:
            data["grocery_list"] = current_list.model_dump()

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def import_from_json(self, filepath: Path):
        """
        Import data from a JSON file.

        Args:
            filepath: Path to import from
        """
        with open(filepath) as f:
            data = json.load(f)

        # Import recipes
        for recipe_data in data.get("recipes", []):
            recipe = Recipe.model_validate(recipe_data)
            self.save_recipe(recipe)

        # Import session
        for rid in data.get("session_recipe_ids", []):
            self.add_to_session(rid)

        # Import grocery list
        if data.get("grocery_list"):
            grocery_list = GroceryList.model_validate(data["grocery_list"])
            self.save_grocery_list(grocery_list)


# Global database instance
_db: Optional[Database] = None


def get_database(db_path: Optional[Path] = None) -> Database:
    """
    Get the database instance (singleton pattern).

    Args:
        db_path: Optional path to the database file

    Returns:
        The Database instance
    """
    global _db
    if _db is None or (db_path and _db.db_path != db_path):
        _db = Database(db_path)
    return _db
