#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

from typing import Dict, Set, Tuple

from secure_endpoint_mcp.config.settings import settings


class FeatureFlagManager:
    """Manager for feature flags to enable/disable groups of APIs."""

    def __init__(self):
        # Get feature flags from environment variables with ABS_FEATURE_ prefix
        self._flags: Dict[str, bool] = settings.get_feature_flags_from_env()
        # Store API paths with their HTTP methods as (path, method) tuples
        self._api_groups: Dict[str, Set[Tuple[str, str]]] = {}

    def register_api_group(
        self, group_name: str, api_path: str, http_method: str
    ) -> None:
        """
        Register an API path with its HTTP method under a feature flag name.

        Args:
            group_name: The name of the feature flag group
            api_path: The API path to register
            http_method: The HTTP method (GET, POST, etc.) to register
        """
        if group_name not in self._api_groups:
            self._api_groups[group_name] = set()
        self._api_groups[group_name].add((api_path, http_method.upper()))

    def is_api_enabled(self, api_path: str, http_method: str) -> bool:
        """
        Check if an API path with the specified HTTP method is enabled based on feature flags.

        Args:
            api_path: The API path to check
            http_method: The HTTP method (GET, POST, etc.) to check

        Returns:
            True if the API is enabled, False otherwise
        """
        # If no feature flags are defined, all APIs are enabled
        if not self._flags and not self._api_groups:
            return True

        # Check if the API path with method belongs to any group
        for group_name, paths_with_methods in self._api_groups.items():
            if (api_path, http_method.upper()) in paths_with_methods:
                # If the group is not in flags, default to disabled
                return self._flags.get(group_name, False)

        # If the API doesn't belong to any group, it's enabled by default
        return True

    def get_enabled_api_groups(self) -> Set[str]:
        """Get the names of all enabled API groups."""
        return {group_name for group_name, enabled in self._flags.items() if enabled}

    def get_disabled_api_groups(self) -> Set[str]:
        """Get the names of all disabled API groups."""
        return {
            group_name for group_name, enabled in self._flags.items() if not enabled
        }


# Create a global instance for convenience
feature_flags = FeatureFlagManager()
