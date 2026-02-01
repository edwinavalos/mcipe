"""Output connectors for exporting grocery lists."""

from .base import BaseConnector, ConnectorRegistry, ConnectorError, registry
from .google_keep import (
    GoogleKeepConnector,
    GoogleKeepError,
    GoogleKeepAuthError,
    is_gkeep_available,
    load_gkeep_config,
    save_gkeep_config,
)

# Register Google Keep connector if available
if is_gkeep_available():
    registry.register(GoogleKeepConnector)

__all__ = [
    "BaseConnector",
    "ConnectorRegistry",
    "ConnectorError",
    "registry",
    "GoogleKeepConnector",
    "GoogleKeepError",
    "GoogleKeepAuthError",
    "is_gkeep_available",
    "load_gkeep_config",
    "save_gkeep_config",
]
