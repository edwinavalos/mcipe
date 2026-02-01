"""
Google Keep connector for exporting grocery lists.

This connector uses the unofficial gkeepapi library to create and sync
checklist notes in Google Keep.

Authentication requires a Google account master token, which provides full
account access. Users should generate an App Password if 2FA is enabled.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..models import GroceryList, GroceryItem
from .base import BaseConnector, ConnectorError


# Try to import gkeepapi
_gkeepapi_available = False
try:
    import gkeepapi
    from gkeepapi import node as keep_node
    _gkeepapi_available = True
except ImportError:
    gkeepapi = None
    keep_node = None


def is_gkeep_available() -> bool:
    """Check if Google Keep support is available."""
    return _gkeepapi_available


class GoogleKeepError(ConnectorError):
    """Error during Google Keep operations."""
    pass


class GoogleKeepAuthError(GoogleKeepError):
    """Authentication error with Google Keep."""
    pass


def get_gkeep_config_path() -> Path:
    """Get the path to the Google Keep config file."""
    return Path.home() / ".config" / "mcipe" / "gkeep_config.json"


def load_gkeep_config() -> dict[str, Any]:
    """Load Google Keep configuration.

    Returns:
        Configuration dict with 'email' and 'master_token' keys, or empty dict.
    """
    config_path = get_gkeep_config_path()
    if not config_path.exists():
        return {}

    try:
        return json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_gkeep_config(config: dict[str, Any]) -> None:
    """Save Google Keep configuration.

    Args:
        config: Configuration dict to save.
    """
    config_path = get_gkeep_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))


def get_gkeep_state_path() -> Path:
    """Get the path to the Google Keep state file (for session persistence)."""
    return Path.home() / ".config" / "mcipe" / "gkeep_state.json"


class GoogleKeepConnector(BaseConnector):
    """
    Connector for exporting grocery lists to Google Keep.

    This creates a checklist note in Google Keep with all items organized
    by category. The list can be synced back to update item status.

    Authentication requires:
    - Google account email
    - Master token (or app password for 2FA accounts)

    The master token provides full account access, so keep it secure.
    """

    name = "googlekeep"
    display_name = "Google Keep"
    description = "Export to Google Keep as a checklist"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize the Google Keep connector.

        Args:
            config: Optional configuration with 'email' and 'master_token'.
                   If not provided, will attempt to load from config file.
        """
        super().__init__(config)

        if not _gkeepapi_available:
            raise GoogleKeepError(
                "Google Keep support not available. "
                "Install with: pip install gkeepapi"
            )

        self._keep: Optional[gkeepapi.Keep] = None
        self._authenticated = False

        # Load config from file if not provided
        if not self.config:
            self.config = load_gkeep_config()

    @property
    def keep(self) -> gkeepapi.Keep:
        """Get the Keep client, authenticating if needed."""
        if self._keep is None:
            self._keep = gkeepapi.Keep()
            self._load_state_or_authenticate()
        return self._keep

    def _load_state_or_authenticate(self) -> None:
        """Try to load saved state, or authenticate fresh."""
        state_path = get_gkeep_state_path()

        # Try to resume from saved state
        if state_path.exists() and self.config.get("email"):
            try:
                state = json.loads(state_path.read_text())
                self._keep.resume(
                    self.config["email"],
                    state,
                    sync=False
                )
                self._keep.sync()
                self._authenticated = True
                return
            except Exception:
                # State invalid or expired, need fresh auth
                pass

        # Fresh authentication
        self._authenticate_fresh()

    def _authenticate_fresh(self) -> None:
        """Perform fresh authentication."""
        email = self.config.get("email")
        master_token = self.config.get("master_token")

        if not email or not master_token:
            raise GoogleKeepAuthError(
                "Google Keep authentication not configured. "
                "Run: mcipe gkeep auth"
            )

        try:
            self._keep.authenticate(email, master_token)
            self._authenticated = True

            # Save state for future sessions
            self._save_state()
        except Exception as e:
            raise GoogleKeepAuthError(f"Failed to authenticate: {e}")

    def _save_state(self) -> None:
        """Save Keep state for session persistence."""
        if self._keep and self._authenticated:
            try:
                state = self._keep.dump()
                state_path = get_gkeep_state_path()
                state_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.write_text(json.dumps(state))
            except Exception:
                # State saving is optional, don't fail
                pass

    def authenticate(self) -> bool:
        """
        Authenticate with Google Keep.

        Returns:
            True if authentication successful.

        Raises:
            GoogleKeepAuthError: If authentication fails.
        """
        try:
            _ = self.keep  # This triggers authentication
            return self._authenticated
        except GoogleKeepAuthError:
            raise
        except Exception as e:
            raise GoogleKeepAuthError(f"Authentication failed: {e}")

    def export(self, grocery_list: GroceryList) -> str:
        """
        Export a grocery list to Google Keep as a checklist.

        Args:
            grocery_list: The grocery list to export.

        Returns:
            The ID of the created Keep note.

        Raises:
            GoogleKeepError: If export fails.
        """
        try:
            # Build list items organized by category
            items_by_category = self._organize_by_category(grocery_list)
            list_items = self._build_list_items(items_by_category)

            # Create the list in Keep
            glist = self.keep.createList(
                grocery_list.name,
                list_items
            )

            # Sync to save
            self.keep.sync()
            self._save_state()

            return glist.id

        except Exception as e:
            raise GoogleKeepError(f"Failed to export to Google Keep: {e}")

    def sync(self, grocery_list: GroceryList, list_id: str) -> bool:
        """
        Sync/update an existing Google Keep checklist.

        This will update the list contents to match the current grocery list.

        Args:
            grocery_list: The grocery list to sync.
            list_id: The Keep note ID.

        Returns:
            True if sync successful.

        Raises:
            GoogleKeepError: If sync fails.
        """
        try:
            # Find the existing note
            note = self.keep.get(list_id)
            if note is None:
                raise GoogleKeepError(f"Note not found: {list_id}")

            if not isinstance(note, keep_node.List):
                raise GoogleKeepError(f"Note {list_id} is not a list")

            # Update title
            note.title = grocery_list.name

            # Clear existing items
            for item in list(note.items):
                item.delete()

            # Add new items
            items_by_category = self._organize_by_category(grocery_list)
            list_items = self._build_list_items(items_by_category)

            for text, checked in list_items:
                item = note.add(text, checked)

            # Sync changes
            self.keep.sync()
            self._save_state()

            return True

        except GoogleKeepError:
            raise
        except Exception as e:
            raise GoogleKeepError(f"Failed to sync: {e}")

    def find_list(self, name: str) -> Optional[str]:
        """
        Find an existing grocery list by name.

        Args:
            name: The list name to search for.

        Returns:
            The note ID if found, None otherwise.
        """
        try:
            self.keep.sync()

            # Search for lists with matching title
            for note in self.keep.all():
                if isinstance(note, keep_node.List) and not note.trashed:
                    if note.title.lower() == name.lower():
                        return note.id

            return None

        except Exception:
            return None

    def get_list_status(self, list_id: str) -> Optional[dict[str, Any]]:
        """
        Get the status of items in a Keep list.

        Args:
            list_id: The Keep note ID.

        Returns:
            Dict with item statuses, or None if not found.
        """
        try:
            self.keep.sync()
            note = self.keep.get(list_id)

            if note is None or not isinstance(note, keep_node.List):
                return None

            items = []
            for item in note.items:
                items.append({
                    "text": item.text,
                    "checked": item.checked,
                })

            return {
                "id": note.id,
                "title": note.title,
                "items": items,
                "checked_count": sum(1 for i in items if i["checked"]),
                "total_count": len(items),
            }

        except Exception:
            return None

    def _organize_by_category(
        self, grocery_list: GroceryList
    ) -> dict[str, list[GroceryItem]]:
        """Organize items by category."""
        by_category: dict[str, list[GroceryItem]] = {}

        for item in grocery_list.items:
            category = item.category or "Other"
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(item)

        return by_category

    def _build_list_items(
        self, items_by_category: dict[str, list[GroceryItem]]
    ) -> list[tuple[str, bool]]:
        """
        Build list items for Google Keep.

        Returns:
            List of (text, checked) tuples for createList.
        """
        list_items = []

        # Sort categories for consistent ordering
        categories = sorted(items_by_category.keys())

        for category in categories:
            items = items_by_category[category]

            # Add category header (unchecked, acts as separator)
            list_items.append((f"── {category.upper()} ──", False))

            # Add items
            for item in sorted(items, key=lambda x: x.name_display):
                text = self.format_item(item)
                list_items.append((text, item.purchased))

        return list_items

    def format_item(self, item: GroceryItem) -> str:
        """
        Format a grocery item for Google Keep.

        Args:
            item: The grocery item.

        Returns:
            Formatted string.
        """
        parts = []

        # Add quantity if present
        qty = item.display_quantity()
        if qty:
            parts.append(qty)

        # Add name
        parts.append(item.name_display)

        # Add form factors if any
        if item.form_factors:
            unique_forms = list(set(item.form_factors))
            parts.append(f"({', '.join(unique_forms)})")

        return " ".join(parts)
