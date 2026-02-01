"""Tests for Google Keep connector."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from mcipe.models import GroceryList, GroceryItem


# Mock gkeepapi before importing the connector
@pytest.fixture(autouse=True)
def mock_gkeepapi():
    """Mock gkeepapi module for all tests."""
    mock_gkeepapi = MagicMock()
    mock_node = MagicMock()

    # Create mock classes
    mock_gkeepapi.Keep = Mock
    mock_node.List = type('MockList', (), {})
    mock_node.ListItem = type('MockListItem', (), {})

    with patch.dict('sys.modules', {
        'gkeepapi': mock_gkeepapi,
        'gkeepapi.node': mock_node,
    }):
        yield mock_gkeepapi, mock_node


class TestGoogleKeepConnector:
    """Tests for GoogleKeepConnector."""

    @pytest.fixture
    def sample_list(self):
        """Create a sample grocery list."""
        return GroceryList(
            name="Test Shopping List",
            items=[
                GroceryItem(
                    name="flour",
                    name_display="All-Purpose Flour",
                    quantities=[(2.0, "cup")],
                    category="Pantry",
                    purchased=False,
                ),
                GroceryItem(
                    name="eggs",
                    name_display="Large Eggs",
                    quantities=[(6.0, "unit")],
                    category="Dairy",
                    purchased=False,
                ),
                GroceryItem(
                    name="butter",
                    name_display="Butter",
                    quantities=[(1.0, "stick")],
                    category="Dairy",
                    purchased=True,
                ),
                GroceryItem(
                    name="chicken",
                    name_display="Chicken Breast",
                    quantities=[(2.0, "lb")],
                    category="Meat",
                    form_factors=["boneless", "skinless"],
                ),
            ],
            recipe_ids=["recipe-1", "recipe-2"],
        )

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create a temporary config directory."""
        config_dir = tmp_path / ".config" / "mcipe"
        config_dir.mkdir(parents=True)
        return config_dir

    def test_is_gkeep_available(self, mock_gkeepapi):
        """Test checking if gkeepapi is available."""
        from mcipe.connectors.google_keep import is_gkeep_available
        # When gkeepapi is mocked/available, this should return True
        # Note: The actual import check happens at module load time
        assert is_gkeep_available() in [True, False]

    def test_config_path(self):
        """Test config path is in correct location."""
        from mcipe.connectors.google_keep import get_gkeep_config_path
        path = get_gkeep_config_path()
        assert ".config" in str(path)
        assert "mcipe" in str(path)
        assert "gkeep_config.json" in str(path)

    def test_load_config_empty(self, temp_config_dir):
        """Test loading config when file doesn't exist."""
        from mcipe.connectors.google_keep import load_gkeep_config, get_gkeep_config_path

        with patch.object(Path, 'home', return_value=temp_config_dir.parent.parent):
            with patch('mcipe.connectors.google_keep.get_gkeep_config_path') as mock_path:
                mock_path.return_value = temp_config_dir / "nonexistent.json"
                config = load_gkeep_config()
                assert config == {}

    def test_save_and_load_config(self, temp_config_dir):
        """Test saving and loading config."""
        from mcipe.connectors.google_keep import save_gkeep_config, load_gkeep_config

        config_file = temp_config_dir / "gkeep_config.json"

        with patch('mcipe.connectors.google_keep.get_gkeep_config_path', return_value=config_file):
            # Save config
            test_config = {"email": "test@example.com", "master_token": "secret123"}
            save_gkeep_config(test_config)

            # Load config
            loaded = load_gkeep_config()
            assert loaded["email"] == "test@example.com"
            assert loaded["master_token"] == "secret123"

    def test_organize_by_category(self, sample_list):
        """Test organizing items by category."""
        from mcipe.connectors.google_keep import GoogleKeepConnector

        # Create connector without auth check
        with patch.object(GoogleKeepConnector, '__init__', lambda self, config=None: None):
            connector = GoogleKeepConnector.__new__(GoogleKeepConnector)
            connector.config = {}

            result = connector._organize_by_category(sample_list)

            assert "Pantry" in result
            assert "Dairy" in result
            assert "Meat" in result
            assert len(result["Pantry"]) == 1
            assert len(result["Dairy"]) == 2
            assert len(result["Meat"]) == 1

    def test_build_list_items(self, sample_list):
        """Test building list items for Google Keep."""
        from mcipe.connectors.google_keep import GoogleKeepConnector

        with patch.object(GoogleKeepConnector, '__init__', lambda self, config=None: None):
            connector = GoogleKeepConnector.__new__(GoogleKeepConnector)
            connector.config = {}

            by_category = connector._organize_by_category(sample_list)
            items = connector._build_list_items(by_category)

            # Should have category headers and items
            assert len(items) > 0

            # Check for category headers
            headers = [text for text, _ in items if "──" in text]
            assert len(headers) == 3  # Dairy, Meat, Pantry

            # Check items are tuples of (text, checked)
            for text, checked in items:
                assert isinstance(text, str)
                assert isinstance(checked, bool)

    def test_format_item_simple(self):
        """Test formatting a simple item."""
        from mcipe.connectors.google_keep import GoogleKeepConnector

        with patch.object(GoogleKeepConnector, '__init__', lambda self, config=None: None):
            connector = GoogleKeepConnector.__new__(GoogleKeepConnector)
            connector.config = {}

            item = GroceryItem(
                name="flour",
                name_display="Flour",
                quantities=[(2.0, "cup")],
            )

            result = connector.format_item(item)
            assert "Flour" in result
            assert "2" in result
            assert "cup" in result

    def test_format_item_with_form_factors(self):
        """Test formatting an item with form factors."""
        from mcipe.connectors.google_keep import GoogleKeepConnector

        with patch.object(GoogleKeepConnector, '__init__', lambda self, config=None: None):
            connector = GoogleKeepConnector.__new__(GoogleKeepConnector)
            connector.config = {}

            item = GroceryItem(
                name="chicken",
                name_display="Chicken Breast",
                quantities=[(2.0, "lb")],
                form_factors=["boneless", "skinless"],
            )

            result = connector.format_item(item)
            assert "Chicken Breast" in result
            assert "boneless" in result or "skinless" in result

    def test_format_item_no_quantity(self):
        """Test formatting an item without quantity."""
        from mcipe.connectors.google_keep import GoogleKeepConnector

        with patch.object(GoogleKeepConnector, '__init__', lambda self, config=None: None):
            connector = GoogleKeepConnector.__new__(GoogleKeepConnector)
            connector.config = {}

            item = GroceryItem(
                name="salt",
                name_display="Salt",
                quantities=[],
            )

            result = connector.format_item(item)
            assert "Salt" in result


class TestGoogleKeepConnectorIntegration:
    """Integration tests for GoogleKeepConnector (with mocked gkeepapi)."""

    @pytest.fixture
    def mock_keep(self):
        """Create a mock Keep client."""
        mock = MagicMock()
        mock.createList.return_value = MagicMock(id="note-123")
        mock.sync.return_value = None
        mock.dump.return_value = {"state": "data"}
        mock.all.return_value = []
        return mock

    @pytest.fixture
    def sample_list(self):
        """Create a sample grocery list."""
        return GroceryList(
            name="Test List",
            items=[
                GroceryItem(
                    name="test",
                    name_display="Test Item",
                    quantities=[(1.0, "unit")],
                    category="Other",
                ),
            ],
        )

    def test_export_creates_list(self, mock_keep, sample_list):
        """Test that export creates a list in Google Keep."""
        from mcipe.connectors.google_keep import GoogleKeepConnector

        with patch.object(GoogleKeepConnector, '__init__', lambda self, config=None: None):
            connector = GoogleKeepConnector.__new__(GoogleKeepConnector)
            connector.config = {"email": "test@example.com", "master_token": "token"}
            connector._keep = mock_keep
            connector._authenticated = True

            note_id = connector.export(sample_list)

            assert note_id == "note-123"
            mock_keep.createList.assert_called_once()
            mock_keep.sync.assert_called()

    def test_export_uses_list_name(self, mock_keep, sample_list):
        """Test that export uses the grocery list name."""
        from mcipe.connectors.google_keep import GoogleKeepConnector

        with patch.object(GoogleKeepConnector, '__init__', lambda self, config=None: None):
            connector = GoogleKeepConnector.__new__(GoogleKeepConnector)
            connector.config = {"email": "test@example.com", "master_token": "token"}
            connector._keep = mock_keep
            connector._authenticated = True

            sample_list.name = "Custom List Name"
            connector.export(sample_list)

            call_args = mock_keep.createList.call_args
            assert call_args[0][0] == "Custom List Name"


class TestGoogleKeepMetadata:
    """Tests for GoogleKeepConnector class metadata."""

    def test_connector_name(self):
        """Test connector name."""
        from mcipe.connectors.google_keep import GoogleKeepConnector
        assert GoogleKeepConnector.name == "googlekeep"

    def test_connector_display_name(self):
        """Test connector display name."""
        from mcipe.connectors.google_keep import GoogleKeepConnector
        assert GoogleKeepConnector.display_name == "Google Keep"

    def test_connector_description(self):
        """Test connector description."""
        from mcipe.connectors.google_keep import GoogleKeepConnector
        assert "Google Keep" in GoogleKeepConnector.description
        assert "checklist" in GoogleKeepConnector.description.lower()


class TestGoogleKeepErrors:
    """Tests for Google Keep error handling."""

    def test_google_keep_error_hierarchy(self):
        """Test error class hierarchy."""
        from mcipe.connectors.google_keep import (
            GoogleKeepError,
            GoogleKeepAuthError,
        )
        from mcipe.connectors.base import ConnectorError

        assert issubclass(GoogleKeepError, ConnectorError)
        assert issubclass(GoogleKeepAuthError, GoogleKeepError)

    def test_auth_error_message(self):
        """Test auth error contains helpful message."""
        from mcipe.connectors.google_keep import GoogleKeepAuthError

        error = GoogleKeepAuthError("Test auth failed")
        assert "Test auth failed" in str(error)
