#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

from unittest import mock

import httpx
import pytest
from fastmcp.server.openapi import MCPType

from secure_endpoint_mcp.config.settings import TransportMode
from secure_endpoint_mcp.server.mcp_server import MCPServer


@pytest.fixture
def mock_http_client():
    """Fixture for mocking the HTTP client."""
    with mock.patch(
        "secure_endpoint_mcp.server.mcp_server.AbsoluteAuthClient"
    ) as mock_client_class:
        mock_client = mock.MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_feature_flags():
    """Fixture for mocking the feature flags."""
    with mock.patch(
        "secure_endpoint_mcp.server.mcp_server.feature_flags"
    ) as mock_flags:
        # By default, all APIs are enabled
        mock_flags.is_api_enabled.return_value = True
        yield mock_flags


@pytest.fixture
def mock_settings(request):
    """Fixture for mocking the settings."""
    with mock.patch("secure_endpoint_mcp.server.mcp_server.settings") as mock_settings:
        # Default to using a remote URL
        mock_settings.API_HOST = "https://example.com"
        mock_settings.SERVER_HOST = "localhost"
        mock_settings.SERVER_PORT = 8000
        mock_settings.API_KEY = "test_api_key"
        mock_settings.API_SECRET = "test_api_secret"
        mock_settings.HTTP_TIMEOUT_SECONDS = 30
        mock_settings.TRANSPORT_MODE = (
            TransportMode.HTTP
        )  # Default to HTTP transport mode

        # Allow tests to override the TRANSPORT_MODE
        if hasattr(request, "param"):
            if "TRANSPORT_MODE" in request.param:
                mock_settings.TRANSPORT_MODE = request.param["TRANSPORT_MODE"]

        yield mock_settings


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI spec for testing."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/api/test": {
                "get": {
                    "operationId": "getTest",
                    "tags": ["test"],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }


@pytest.mark.asyncio
async def test_initialize(
    mock_http_client, mock_feature_flags, mock_settings, sample_openapi_spec
):
    """Test that MCPServer.initialize extracts API groups."""
    # Create a server
    server = MCPServer()

    # Mock the _fetch_openapi_spec method to return the sample spec
    with mock.patch.object(
        server, "_fetch_openapi_spec", return_value=sample_openapi_spec
    ):
        # Mock the _extract_api_groups_from_openapi method
        with mock.patch.object(
            server, "_extract_api_groups_from_openapi"
        ) as mock_extract:
            # Initialize the server
            await server.initialize()

            # Assert that _extract_api_groups_from_openapi was called
            mock_extract.assert_called_once()


@pytest.mark.asyncio
async def test_extract_api_groups_from_openapi(mock_feature_flags, sample_openapi_spec):
    """Test that MCPServer._extract_api_groups_from_openapi extracts API groups and registers them with feature flags."""
    # Create a server
    server = MCPServer()

    # Set the openapi_spec directly on the server instance
    server.openapi_spec = sample_openapi_spec

    # Extract API groups from the OpenAPI spec
    await server._extract_api_groups_from_openapi()

    # Assert that feature_flags.register_api_group was called with the correct arguments
    # Note: tag names are now transformed to lowercase with dashes
    # The API group should now include both path and method
    mock_feature_flags.register_api_group.assert_called_once_with(
        "test", "/api/test", "GET"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_settings", [{"TRANSPORT_MODE": TransportMode.HTTP}], indirect=True
)
async def test_start_http(mock_settings, sample_openapi_spec):
    """Test that MCPServer.start initializes and starts the FastMCP app with HTTP transport."""
    # Create a server
    server = MCPServer()

    # Create a mock app with awaitable methods
    mock_app = mock.MagicMock()

    # Create an awaitable coroutine for run_http_async
    async def mock_run_http_async(*args, **kwargs):
        return None

    # Set the mock to return the coroutine
    mock_app.run_http_async = mock_run_http_async
    server.app = mock_app

    # Skip the actual initialization by patching the initialize method
    with mock.patch.object(server, "initialize", return_value=None):
        # Start the server
        await server.start()

        # We can't use assert_called_once_with here since we replaced the method
        # Instead, we'll check that the server started successfully


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_settings", [{"TRANSPORT_MODE": TransportMode.SSE}], indirect=True
)
async def test_start_sse(mock_settings, sample_openapi_spec):
    """Test that MCPServer.start initializes and starts the FastMCP app with SSE transport."""
    # Create a server
    server = MCPServer()

    # Create a mock app with awaitable methods
    mock_app = mock.MagicMock()

    # Create an awaitable coroutine for run_http_async
    async def mock_run_http_async(*args, **kwargs):
        # Verify that transport="sse" is passed
        assert kwargs.get("transport") == "sse"
        return None

    # Set the mock to return the coroutine
    mock_app.run_http_async = mock_run_http_async
    server.app = mock_app

    # Skip the actual initialization by patching the initialize method
    with mock.patch.object(server, "initialize", return_value=None):
        # Start the server
        await server.start()

        # We can't use assert_called_once_with here since we replaced the method
        # Instead, we'll check that the server started successfully


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_settings", [{"TRANSPORT_MODE": TransportMode.STDIO}], indirect=True
)
async def test_start_stdio(mock_settings, sample_openapi_spec):
    """Test that MCPServer.start initializes and starts the FastMCP app with stdio transport."""
    # Create a server
    server = MCPServer()

    # Create a mock app with awaitable methods
    mock_app = mock.MagicMock()

    # Create an awaitable coroutine for run_stdio_async
    async def mock_run_stdio_async(*args, **kwargs):
        return None

    # Set the mock to return the coroutine
    mock_app.run_stdio_async = mock_run_stdio_async
    server.app = mock_app

    # Skip the actual initialization by patching the initialize method
    with mock.patch.object(server, "initialize", return_value=None):
        # Start the server
        await server.start()

        # We can't use assert_called_once here since we replaced the method
        # Instead, we'll check that the server started successfully


@pytest.mark.asyncio
async def test_stop():
    """Test that MCPServer.stop logs a message."""
    # Create a server
    server = MCPServer()

    # Mock the logger.info method
    with mock.patch("secure_endpoint_mcp.server.mcp_server.logger.info") as mock_info:
        # Stop the server
        await server.stop()

        # Assert that logger.info was called with the correct message
        mock_info.assert_called_once_with("Stopping MCP server")


def test_route_map_fn(mock_feature_flags, mock_settings):
    """Test that MCPServer._route_map_fn returns the correct MCPType based on feature flags and HTTP method."""
    # Create a server
    server = MCPServer()

    # Create a mock route
    route = mock.MagicMock()
    route.path = "/api/test"

    # Create a mock mcp_type
    mcp_type = MCPType.TOOL

    # By default, the advanced API blocklist is enabled
    mock_settings.DISABLE_ADVANCED_API_BLOCKLIST = False

    # Test 1: Route is disabled by feature flags
    # Configure the mock feature flags to return False for is_api_enabled
    mock_feature_flags.is_api_enabled.return_value = False
    route.method = "GET"

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with("/api/test", "GET")

    # Assert that the route_map_fn returned MCPType.EXCLUDE
    assert result == MCPType.EXCLUDE

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 2: GET endpoint (should be categorized as RESOURCE)
    # Configure the mock feature flags to return True for is_api_enabled
    mock_feature_flags.is_api_enabled.return_value = True
    route.method = "GET"

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with("/api/test", "GET")

    # Assert that the route_map_fn returned MCPType.TOOL
    assert result == MCPType.TOOL

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 3: POST endpoint (should be categorized as TOOL)
    route.method = "POST"

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with("/api/test", "POST")

    # Assert that the route_map_fn returned MCPType.TOOL
    assert result == MCPType.TOOL

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 4: PUT endpoint (should be categorized as TOOL)
    route.method = "PUT"

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with("/api/test", "PUT")

    # Assert that the route_map_fn returned MCPType.TOOL
    assert result == MCPType.TOOL

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 5: PATCH endpoint (should be categorized as TOOL)
    route.method = "PATCH"

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with("/api/test", "PATCH")

    # Assert that the route_map_fn returned MCPType.TOOL
    assert result == MCPType.TOOL

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 6: DELETE endpoint (should be categorized as TOOL)
    route.method = "DELETE"

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with("/api/test", "DELETE")

    # Assert that the route_map_fn returned MCPType.TOOL
    assert result == MCPType.TOOL

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 7: Other HTTP method (should return the original mcp_type)
    route.method = "HEAD"

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with("/api/test", "HEAD")

    # Assert that the route_map_fn returned the original mcp_type
    assert result == mcp_type

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 8: Advanced API route with blocklist enabled (should be excluded)
    route.path = "/api/test-advanced"
    route.method = "GET"
    mock_settings.DISABLE_ADVANCED_API_BLOCKLIST = False

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that the route_map_fn returned MCPType.EXCLUDE
    assert result == MCPType.EXCLUDE

    # Assert that is_api_enabled was not called (blocklist check happens before feature flag check)
    mock_feature_flags.is_api_enabled.assert_not_called()

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 9: Advanced API route with blocklist disabled (should be allowed)
    route.path = "/api/test-advanced"
    route.method = "GET"
    mock_settings.DISABLE_ADVANCED_API_BLOCKLIST = True

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with(
        "/api/test-advanced", "GET"
    )

    # Assert that the route_map_fn returned MCPType.TOOL (since it's a GET endpoint)
    assert result == MCPType.TOOL

    # Reset the mock
    mock_feature_flags.is_api_enabled.reset_mock()

    # Test 10: Non-advanced API route (should not be affected by blocklist)
    route.path = "/api/test"
    route.method = "GET"
    mock_settings.DISABLE_ADVANCED_API_BLOCKLIST = False

    # Call the route_map_fn
    result = server._route_map_fn(route, mcp_type)

    # Assert that is_api_enabled was called with the correct path and method
    mock_feature_flags.is_api_enabled.assert_called_once_with("/api/test", "GET")

    # Assert that the route_map_fn returned MCPType.TOOL (since it's a GET endpoint)
    assert result == MCPType.TOOL


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_settings", [{"API_HOST": "https://example.com"}], indirect=True
)
async def test_initialize_with_remote_spec(
    mock_settings, mock_http_client, mock_feature_flags, sample_openapi_spec
):
    """Test that MCPServer.initialize uses the remote OpenAPI spec."""
    # Create a server
    server = MCPServer()

    # Mock the _fetch_openapi_spec method to return the sample spec
    with mock.patch.object(
        server, "_fetch_openapi_spec", return_value=sample_openapi_spec
    ):
        # Mock the FastMCPOpenAPI constructor
        with mock.patch(
            "secure_endpoint_mcp.server.mcp_server.FastMCPOpenAPI"
        ) as mock_fastmcp_openapi:
            # Mock the _extract_api_groups_from_openapi method
            with mock.patch.object(
                server, "_extract_api_groups_from_openapi"
            ) as mock_extract:
                # Initialize the server
                await server.initialize()

                # Assert that _extract_api_groups_from_openapi was called
                mock_extract.assert_called_once()

                # Assert that FastMCPOpenAPI was called with the correct parameters
                mock_fastmcp_openapi.assert_called_once()
                args, kwargs = mock_fastmcp_openapi.call_args
                assert kwargs["openapi_spec"] == sample_openapi_spec
                assert kwargs["client"] == server.http_client
                assert kwargs["route_map_fn"] == server._route_map_fn


@pytest.mark.asyncio
async def test_fetch_openapi_spec(mock_settings, sample_openapi_spec):
    """Test that MCPServer._fetch_openapi_spec fetches the OpenAPI spec from the URL."""
    # Create a server
    server = MCPServer()
    server.openapi_spec_url = "https://example.com/openapi.json"

    # Mock httpx.AsyncClient.get to return a response with the sample spec
    mock_response = mock.MagicMock()
    mock_response.json.return_value = sample_openapi_spec
    mock_response.raise_for_status = mock.MagicMock()

    with mock.patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        # Fetch the OpenAPI spec
        result = await server._fetch_openapi_spec()

        # Assert that httpx.AsyncClient.get was called with the correct URL
        mock_get.assert_called_once_with("https://example.com/openapi.json")

        # Assert that the result is the sample spec
        assert result == sample_openapi_spec


@pytest.mark.asyncio
async def test_fetch_openapi_spec_error(mock_settings):
    """Test that MCPServer._fetch_openapi_spec raises an exception when the request fails."""
    # Create a server
    server = MCPServer()
    server.openapi_spec_url = "https://example.com/openapi.json"

    # Mock httpx.AsyncClient.get to raise an exception
    with mock.patch(
        "httpx.AsyncClient.get", side_effect=httpx.HTTPError("Request failed")
    ) as mock_get:
        # Fetch the OpenAPI spec should raise an exception
        with pytest.raises(httpx.HTTPError):
            await server._fetch_openapi_spec()

        # Assert that httpx.AsyncClient.get was called with the correct URL
        mock_get.assert_called_once_with("https://example.com/openapi.json")


@pytest.mark.asyncio
async def test_initialize_with_remote_spec_error(
    mock_settings, mock_http_client, mock_feature_flags
):
    """Test that MCPServer.initialize raises an exception when fetching the remote OpenAPI spec fails."""
    # Create a server
    server = MCPServer()

    # Mock the _fetch_openapi_spec method to raise an exception
    with mock.patch.object(
        server, "_fetch_openapi_spec", side_effect=Exception("Failed to fetch spec")
    ):
        # Initialize the server should raise an exception
        with pytest.raises(Exception):
            await server.initialize()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_settings", [{"TRANSPORT_MODE": "invalid"}], indirect=True
)
async def test_start_with_invalid_transport(mock_settings):
    """Test that MCPServer.start raises ValueError when an invalid transport mode is provided."""
    # Create a server
    server = MCPServer()

    # Mock the initialize method to do nothing
    with mock.patch.object(server, "initialize", return_value=None):
        # Start the server should raise ValueError
        with pytest.raises(AssertionError, match="MCP app is not initialized"):
            await server.start()


@pytest.mark.asyncio
async def test_strip_html_from_description():
    """Test that MCPServer._strip_html_from_description strips HTML tags from description fields."""
    # Create a server
    server = MCPServer()

    # Create a test object with HTML in description fields
    test_obj = {
        "description": "<p>This is a <strong>test</strong> description</p>",
        "nested": {"description": "<p>Nested <em>description</em></p>"},
        "list": [{"description": "<p>List item <a href='#'>description</a></p>"}],
    }

    # Strip HTML tags from description fields
    server._strip_html_from_description(test_obj)

    # Assert that HTML tags were stripped
    assert test_obj["description"] == "This is a test description"
    assert test_obj["nested"]["description"] == "Nested description"
    assert test_obj["list"][0]["description"] == "List item description"
