#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import os
from unittest import mock

from secure_endpoint_mcp.config.settings import Settings


def test_settings_with_required_values():
    """Test that settings can be created with required values."""
    with mock.patch.dict(
        os.environ,
        {
            "API_KEY": "foo",
            "API_SECRET": "bar",
            "API_HOST": "https://api1.absolute.com",
        },
    ):
        settings = Settings()
        assert settings.API_KEY == "foo"
        assert settings.API_SECRET == "bar"
        assert settings.HTTP_TIMEOUT_SECONDS == 30
        assert settings.SERVER_HOST == "0.0.0.0"
        assert settings.SERVER_PORT == 8000
        assert settings.LOG_LEVEL == "info"
        assert settings.API_HOST == "https://api1.absolute.com"


def test_get_feature_flags_from_env_default():
    """Test that get_feature_flags_from_env returns default values when no env vars are set."""
    with mock.patch.dict(
        os.environ,
        {
            "API_KEY": "foo",
            "API_SECRET": "bar",
        },
        clear=True,
    ):
        settings = Settings()
        flags = settings.get_feature_flags_from_env()
        # By default, only device-reporting should be enabled
        assert flags == {"device-reporting": True}


def test_get_feature_flags_from_env_enabled():
    """Test that get_feature_flags_from_env returns enabled flags."""
    with mock.patch.dict(
        os.environ,
        {
            "API_KEY": "foo",
            "API_SECRET": "bar",
            "ABS_FEATURE_DEVICE_REPORTING": "enabled",
        },
        clear=True,
    ):
        settings = Settings()
        flags = settings.get_feature_flags_from_env()
        assert flags == {"device-reporting": True}


def test_get_feature_flags_from_env_disabled():
    """Test that get_feature_flags_from_env returns disabled flags."""
    with mock.patch.dict(
        os.environ,
        {
            "API_KEY": "foo",
            "API_SECRET": "bar",
            "ABS_FEATURE_DEVICE_REPORTING": "disabled",
        },
        clear=True,
    ):
        settings = Settings()
        flags = settings.get_feature_flags_from_env()
        assert flags == {"device-reporting": False}


def test_get_feature_flags_from_env_multiple():
    """Test that get_feature_flags_from_env returns multiple flags."""
    with mock.patch.dict(
        os.environ,
        {
            "API_KEY": "foo",
            "API_SECRET": "bar",
            "ABS_FEATURE_DEVICE_REPORTING": "enabled",
            "ABS_FEATURE_SOFTWARE_REPORTING": "disabled",
        },
        clear=True,
    ):
        settings = Settings()
        flags = settings.get_feature_flags_from_env()
        assert flags == {"device-reporting": True, "software-reporting": False}
