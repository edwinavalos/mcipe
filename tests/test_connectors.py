"""Tests for connector modules."""

import pytest

from mcipe.connectors.base import (
    BaseConnector,
    PlainTextConnector,
    MarkdownConnector,
    ConnectorRegistry,
    ConnectorError,
    registry,
)
from mcipe.models import GroceryList, GroceryItem


class TestPlainTextConnector:
    """Tests for PlainTextConnector."""

    @pytest.fixture
    def connector(self):
        """Create a connector instance."""
        return PlainTextConnector()

    @pytest.fixture
    def sample_list(self):
        """Create a sample grocery list."""
        return GroceryList(
            name="Test List",
            items=[
                GroceryItem(
                    name="flour",
                    name_display="All-Purpose Flour",
                    quantities=[(2.0, "cup")],
                    category="pantry",
                ),
                GroceryItem(
                    name="eggs",
                    name_display="Eggs",
                    quantities=[(6.0, "unit")],
                    category="dairy",
                ),
            ],
        )

    def test_authenticate(self, connector):
        """Test authentication (always succeeds for plain text)."""
        assert connector.authenticate() is True

    def test_export(self, connector, sample_list):
        """Test exporting grocery list."""
        result = connector.export(sample_list)
        assert isinstance(result, str)
        assert "Flour" in result or "flour" in result
        assert "Eggs" in result or "eggs" in result

    def test_sync_raises_error(self, connector, sample_list):
        """Test that sync raises an error."""
        with pytest.raises(ConnectorError):
            connector.sync(sample_list, "some-id")

    def test_format_item(self, connector):
        """Test formatting a single item."""
        item = GroceryItem(
            name="flour",
            name_display="Flour",
            quantities=[(2.0, "cup")],
        )
        result = connector.format_item(item)
        assert "Flour" in result
        assert "2" in result

    def test_test_connection(self, connector):
        """Test connection testing."""
        assert connector.test_connection() is True


class TestMarkdownConnector:
    """Tests for MarkdownConnector."""

    @pytest.fixture
    def connector(self):
        """Create a connector instance."""
        return MarkdownConnector()

    @pytest.fixture
    def sample_list(self):
        """Create a sample grocery list."""
        return GroceryList(
            name="Weekly Shopping",
            items=[
                GroceryItem(
                    name="butter",
                    name_display="Butter",
                    quantities=[(1.0, "stick")],
                    category="dairy",
                    purchased=False,
                ),
                GroceryItem(
                    name="milk",
                    name_display="Milk",
                    quantities=[(1.0, "gallon")],
                    category="dairy",
                    purchased=True,
                ),
            ],
            recipe_ids=["recipe-1", "recipe-2"],
        )

    def test_authenticate(self, connector):
        """Test authentication."""
        assert connector.authenticate() is True

    def test_export_contains_markdown(self, connector, sample_list):
        """Test that export contains markdown formatting."""
        result = connector.export(sample_list)
        assert "# Weekly Shopping" in result
        assert "- [ ]" in result or "- [x]" in result  # Checkboxes
        assert "##" in result  # Category headers

    def test_export_checkbox_states(self, connector, sample_list):
        """Test that checkboxes reflect purchased state."""
        result = connector.export(sample_list)
        # Butter is not purchased
        assert "[ ] " in result
        # Milk is purchased
        assert "[x] " in result

    def test_format_item_unchecked(self, connector):
        """Test formatting unpurchased item."""
        item = GroceryItem(
            name="test",
            name_display="Test Item",
            purchased=False,
        )
        result = connector.format_item(item)
        assert "[ ]" in result

    def test_format_item_checked(self, connector):
        """Test formatting purchased item."""
        item = GroceryItem(
            name="test",
            name_display="Test Item",
            purchased=True,
        )
        result = connector.format_item(item)
        assert "[x]" in result

    def test_sync_raises_error(self, connector, sample_list):
        """Test that sync raises an error."""
        with pytest.raises(ConnectorError):
            connector.sync(sample_list, "some-id")


class TestConnectorRegistry:
    """Tests for ConnectorRegistry."""

    def test_builtin_connectors_registered(self):
        """Test that built-in connectors are registered."""
        connectors = registry.list_connectors()
        names = [c["name"] for c in connectors]
        assert "plaintext" in names
        assert "markdown" in names

    def test_get_connector_class(self):
        """Test getting a connector class."""
        cls = registry.get("plaintext")
        assert cls is PlainTextConnector

    def test_get_nonexistent_connector(self):
        """Test getting a non-existent connector."""
        cls = registry.get("nonexistent")
        assert cls is None

    def test_create_connector_instance(self):
        """Test creating a connector instance."""
        connector = registry.create("markdown")
        assert isinstance(connector, MarkdownConnector)

    def test_create_nonexistent_connector(self):
        """Test creating a non-existent connector."""
        connector = registry.create("nonexistent")
        assert connector is None

    def test_create_with_config(self):
        """Test creating a connector with config."""
        config = {"key": "value"}
        connector = registry.create("plaintext", config)
        assert connector.config == config

    def test_register_custom_connector(self):
        """Test registering a custom connector."""

        class CustomConnector(BaseConnector):
            name = "custom"
            display_name = "Custom"
            description = "A custom connector"

            def authenticate(self):
                return True

            def export(self, grocery_list):
                return "custom export"

            def sync(self, grocery_list, list_id):
                return True

        new_registry = ConnectorRegistry()
        new_registry.register(CustomConnector)

        cls = new_registry.get("custom")
        assert cls is CustomConnector

    def test_list_connectors_format(self):
        """Test format of listed connectors."""
        connectors = registry.list_connectors()
        assert len(connectors) > 0
        for c in connectors:
            assert "name" in c
            assert "display_name" in c
            assert "description" in c
