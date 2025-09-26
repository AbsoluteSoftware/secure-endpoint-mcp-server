#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import os
from enum import Enum
from typing import Dict

from pydantic_settings import BaseSettings, SettingsConfigDict


class TransportMode(str, Enum):
    """Transport modes supported by the MCP server."""

    HTTP = "http"
    STDIO = "stdio"
    # deprecated!
    SSE = "sse"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API host configuration
    # see https://api.absolute.com/api-doc/doc.html for available options.
    API_HOST: str = "https://api.absolute.com"

    # HTTP client configuration
    API_KEY: str = ""
    API_SECRET: str = ""
    HTTP_TIMEOUT_SECONDS: int = 30

    # Server configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    LOG_LEVEL: str = "info"
    TRANSPORT_MODE: TransportMode = TransportMode.HTTP

    # Blocklist configuration
    # If set to True, the blocklist for advanced APIs will be disabled
    DISABLE_ADVANCED_API_BLOCKLIST: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    def get_feature_flags_from_env(self) -> Dict[str, bool]:
        """
        Get feature flags from environment variables with ABS_FEATURE_ prefix.

        For example:
        ABS_FEATURE_DEVICE_REPORTING=enabled -> {"device-reporting": True}
        ABS_FEATURE_DEVICE_REPORTING=disabled -> {"device-reporting": False}

        If a feature isn't explicitly enabled/disabled, only enable "device-reporting" feature.
        """
        result = {}
        prefix = "ABS_FEATURE_"

        # Get all environment variables with the ABS_FEATURE_ prefix
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert from UPPER_SNAKE_CASE to lower-case-with-dashes
                feature_name = key[len(prefix) :].lower().replace("_", "-")
                # Check if the value is "enabled" or "disabled"
                result[feature_name] = value.lower() == "enabled"

        # If no feature flags are set, enable only device-reporting by default
        if not result and "device-reporting" not in result:
            result["device-reporting"] = True

        return result


# Create a global settings instance
settings = Settings()
