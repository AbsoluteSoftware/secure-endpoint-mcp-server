#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import os
from unittest import mock

from secure_endpoint_mcp.feature_flags.manager import FeatureFlagManager


@mock.patch.dict(os.environ, {}, clear=True)
def test_feature_flag_manager_init_default():
    """Test that FeatureFlagManager initializes with default values when no env vars are set."""
    manager = FeatureFlagManager()
    # By default, only device-reporting should be enabled
    assert manager._flags == {"device-reporting": True}
    assert manager._api_groups == {}


@mock.patch.dict(os.environ, {"ABS_FEATURE_DEVICE_REPORTING": "enabled"}, clear=True)
def test_feature_flag_manager_init_with_enabled_flag():
    """Test that FeatureFlagManager initializes with an enabled feature flag."""
    manager = FeatureFlagManager()
    assert manager._flags == {"device-reporting": True}
    assert manager._api_groups == {}


@mock.patch.dict(os.environ, {"ABS_FEATURE_DEVICE_REPORTING": "disabled"}, clear=True)
def test_feature_flag_manager_init_with_disabled_flag():
    """Test that FeatureFlagManager initializes with a disabled feature flag."""
    manager = FeatureFlagManager()
    assert manager._flags == {"device-reporting": False}
    assert manager._api_groups == {}


@mock.patch.dict(os.environ, {
    "ABS_FEATURE_DEVICE_REPORTING": "enabled",
    "ABS_FEATURE_SOFTWARE_REPORTING": "disabled"
}, clear=True)
def test_feature_flag_manager_init_with_multiple_flags():
    """Test that FeatureFlagManager initializes with multiple feature flags."""
    manager = FeatureFlagManager()
    assert manager._flags == {"device-reporting": True, "software-reporting": False}
    assert manager._api_groups == {}


def test_register_api_group():
    """Test registering an API group."""
    manager = FeatureFlagManager()
    manager.register_api_group("test_group", "/api/test1", "GET")
    manager.register_api_group("test_group", "/api/test2", "POST")

    assert "test_group" in manager._api_groups
    assert manager._api_groups["test_group"] == {("/api/test1", "GET"), ("/api/test2", "POST")}


def test_is_api_enabled_no_flags():
    """Test that all APIs are enabled when no feature flags are defined."""
    manager = FeatureFlagManager()
    assert manager.is_api_enabled("/api/test", "GET") is True


def test_is_api_enabled_with_group():
    """Test that APIs are enabled/disabled based on their group."""
    manager = FeatureFlagManager()
    manager._flags = {"test_group": True, "disabled_group": False}
    manager.register_api_group("test_group", "/api/test1", "GET")
    manager.register_api_group("test_group", "/api/test2", "POST")
    manager.register_api_group("disabled_group", "/api/disabled", "GET")

    assert manager.is_api_enabled("/api/test1", "GET") is True
    assert manager.is_api_enabled("/api/test2", "POST") is True
    assert manager.is_api_enabled("/api/disabled", "GET") is False
    # API not in any group should be enabled by default
    assert manager.is_api_enabled("/api/other", "GET") is True

    # Test that different methods on the same path can have different enabled states
    assert manager.is_api_enabled("/api/test1", "POST") is True  # Not in any group, so enabled by default
    assert manager.is_api_enabled("/api/test2", "GET") is True   # Not in any group, so enabled by default


def test_get_enabled_api_groups():
    """Test getting enabled API groups."""
    manager = FeatureFlagManager()
    manager._flags = {"group1": True, "group2": False, "group3": True}

    enabled_groups = manager.get_enabled_api_groups()
    assert enabled_groups == {"group1", "group3"}


def test_get_disabled_api_groups():
    """Test getting disabled API groups."""
    manager = FeatureFlagManager()
    manager._flags = {"group1": True, "group2": False, "group3": True}

    disabled_groups = manager.get_disabled_api_groups()
    assert disabled_groups == {"group2"}
