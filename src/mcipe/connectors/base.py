"""
Base connector interface for exporting grocery lists.

This module defines the abstract base class that all connectors must implement,
as well as a registry for managing available connectors.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from ..models import GroceryList


class ConnectorError(Exception):
    """Error during connector operation."""

    pass


class BaseConnector(ABC):
    """
    Abstract base class for grocery list export connectors.

    Implement this class to create new connectors for services like
    Google Keep, Target, Todoist, etc.
    """

    # Connector metadata (override in subclasses)
    name: str = "base"
    display_name: str = "Base Connector"
    description: str = "Base connector class"

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize the connector.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the service.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            ConnectorError: If authentication fails
        """
        pass

    @abstractmethod
    def export(self, grocery_list: GroceryList) -> str:
        """
        Export a grocery list to the service.

        Args:
            grocery_list: The grocery list to export

        Returns:
            A URL or identifier for the exported list

        Raises:
            ConnectorError: If export fails
        """
        pass

    @abstractmethod
    def sync(self, grocery_list: GroceryList, list_id: str) -> bool:
        """
        Sync/update an existing list on the service.

        Args:
            grocery_list: The grocery list to sync
            list_id: The ID of the list on the service

        Returns:
            True if sync successful

        Raises:
            ConnectorError: If sync fails
        """
        pass

    def format_item(self, item) -> str:
        """
        Format a grocery item for display in the service.

        Override this method to customize item formatting.

        Args:
            item: A GroceryItem

        Returns:
            Formatted string representation
        """
        return item.display_line()

    def format_list(self, grocery_list: GroceryList) -> list[str]:
        """
        Format the entire grocery list for the service.

        Args:
            grocery_list: The grocery list

        Returns:
            List of formatted item strings
        """
        lines = []

        # Group by category
        by_category: dict[str, list] = {}
        for item in grocery_list.items:
            cat = item.category or "Other"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

        # Format with category headers
        for category in sorted(by_category.keys()):
            items = by_category[category]
            lines.append(f"## {category.title()}")
            for item in items:
                lines.append(f"  {self.format_item(item)}")
            lines.append("")

        return lines

    def test_connection(self) -> bool:
        """
        Test the connection to the service.

        Returns:
            True if connection is working
        """
        try:
            return self.authenticate()
        except Exception:
            return False


class PlainTextConnector(BaseConnector):
    """
    Simple connector that outputs plain text.

    This is useful for clipboard copying or file export.
    """

    name = "plaintext"
    display_name = "Plain Text"
    description = "Export as plain text (for clipboard or file)"

    def authenticate(self) -> bool:
        """No authentication needed for plain text."""
        return True

    def export(self, grocery_list: GroceryList) -> str:
        """
        Export the grocery list as plain text.

        Args:
            grocery_list: The grocery list

        Returns:
            The formatted text
        """
        lines = self.format_list(grocery_list)
        return "\n".join(lines)

    def sync(self, grocery_list: GroceryList, list_id: str) -> bool:
        """Plain text doesn't support syncing."""
        raise ConnectorError("Plain text connector does not support syncing")


class MarkdownConnector(BaseConnector):
    """
    Connector that outputs Markdown format.
    """

    name = "markdown"
    display_name = "Markdown"
    description = "Export as Markdown with checkboxes"

    def authenticate(self) -> bool:
        """No authentication needed for Markdown."""
        return True

    def format_item(self, item) -> str:
        """Format as Markdown checkbox."""
        checkbox = "[x]" if item.purchased else "[ ]"
        return f"- {checkbox} {item.display_line()}"

    def format_list(self, grocery_list: GroceryList) -> list[str]:
        """Format as Markdown with headers."""
        lines = [f"# {grocery_list.name}", ""]

        # Add recipe sources
        if grocery_list.recipe_ids:
            lines.append("**Recipes:**")
            # We don't have recipe names here, but could add them
            lines.append(f"- {len(grocery_list.recipe_ids)} recipe(s)")
            lines.append("")

        # Group by category
        by_category: dict[str, list] = {}
        for item in grocery_list.items:
            cat = item.category or "Other"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

        # Format with category headers
        for category in sorted(by_category.keys()):
            items = by_category[category]
            lines.append(f"## {category.title()}")
            lines.append("")
            for item in items:
                lines.append(self.format_item(item))
            lines.append("")

        return lines

    def export(self, grocery_list: GroceryList) -> str:
        """Export as Markdown."""
        lines = self.format_list(grocery_list)
        return "\n".join(lines)

    def sync(self, grocery_list: GroceryList, list_id: str) -> bool:
        """Markdown doesn't support syncing."""
        raise ConnectorError("Markdown connector does not support syncing")


class ConnectorRegistry:
    """
    Registry for managing available connectors.
    """

    def __init__(self):
        """Initialize the registry with built-in connectors."""
        self._connectors: dict[str, type[BaseConnector]] = {}

        # Register built-in connectors
        self.register(PlainTextConnector)
        self.register(MarkdownConnector)

    def register(self, connector_class: type[BaseConnector]):
        """
        Register a connector class.

        Args:
            connector_class: The connector class to register
        """
        self._connectors[connector_class.name] = connector_class

    def get(self, name: str) -> Optional[type[BaseConnector]]:
        """
        Get a connector class by name.

        Args:
            name: The connector name

        Returns:
            The connector class or None if not found
        """
        return self._connectors.get(name)

    def create(
        self, name: str, config: Optional[dict[str, Any]] = None
    ) -> Optional[BaseConnector]:
        """
        Create a connector instance by name.

        Args:
            name: The connector name
            config: Optional configuration

        Returns:
            A connector instance or None if not found
        """
        connector_class = self.get(name)
        if connector_class:
            return connector_class(config)
        return None

    def list_connectors(self) -> list[dict[str, str]]:
        """
        List all available connectors.

        Returns:
            List of connector info dicts
        """
        return [
            {
                "name": c.name,
                "display_name": c.display_name,
                "description": c.description,
            }
            for c in self._connectors.values()
        ]


# Global registry instance
registry = ConnectorRegistry()
