#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

from typing import Dict, Set, Tuple, Any

import html2text
import httpx
from fastmcp.server.openapi import FastMCPOpenAPI, MCPType

from secure_endpoint_mcp.client.auth_client import AbsoluteAuthClient
from secure_endpoint_mcp.config.logging import get_logger
from secure_endpoint_mcp.config.settings import settings, TransportMode
from secure_endpoint_mcp.feature_flags.manager import feature_flags

logger = get_logger(__name__)


class MCPServer:
    """MCP server using FastMCP framework to adopt an OpenAPI spec."""

    def __init__(self):
        self._api_groups: Dict[str, Set[Tuple[str, str]]] = {}

        # Create the HTTP client with authentication
        self.http_client = AbsoluteAuthClient(
            api_key=settings.API_KEY,
            api_secret=settings.API_SECRET,
            timeout_seconds=settings.HTTP_TIMEOUT_SECONDS
        )
        self.openapi_spec = None

        # Use the remote OpenAPI spec URL
        self.openapi_spec_url = f"{settings.API_HOST}/api-doc/spec/openapi.json"
        logger.info(f"Using OpenAPI spec from: {self.openapi_spec_url}")

    def _strip_html_from_description(self, obj: Any) -> None:
        """
        Recursively traverse the OpenAPI spec and strip HTML tags from description fields.
        This is to reduce the length for better performance and money savings.

        Args:
            obj: The object to process (dict, list, or scalar value)
        """
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        h.ignore_tables = False
        h.ignore_emphasis = True
        h.body_width = 0  # No wrapping

        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "description" and isinstance(value, str):
                    # Strip HTML tags from description fields
                    obj[key] = h.handle(value).strip()
                elif isinstance(value, (dict, list)):
                    # Recursively process nested objects
                    self._strip_html_from_description(value)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, (dict, list)):
                    # Recursively process nested objects
                    self._strip_html_from_description(item)

    async def initialize(self) -> None:
        """Initialize the MCP server by loading the OpenAPI spec."""
        logger.info(f"Initializing MCP server with OpenAPI spec from: {self.openapi_spec_url}")
        # Fetch the OpenAPI spec from the URL
        try:
            self.openapi_spec = await self._fetch_openapi_spec()
        except Exception as e:
            logger.error(f"Failed to fetch OpenAPI spec from URL: {str(e)}")
            raise

        try:
            # Strip HTML tags from description fields in the OpenAPI spec
            logger.info("Stripping HTML tags from OpenAPI description fields")
            self._strip_html_from_description(self.openapi_spec)

            # Extract API groups from the OpenAPI spec for feature flags
            await self._extract_api_groups_from_openapi()

            logger.info("MCP server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {str(e)}")
            raise

        self.app = FastMCPOpenAPI(
            openapi_spec=self.openapi_spec,
            client=self.http_client,
            route_map_fn=self._route_map_fn
        )

    def _transform_tag_name(self, tag: str) -> str:
        """Transform tag name from 'Space Case' to 'lower-case-with-dashes'."""
        return tag.lower().replace(' ', '-')

    def _route_map_fn(self, route, mcp_type):
        """
        Route mapping function for FastMCPOpenAPI.

        This function is called for each route in the OpenAPI spec.
        It categorizes routes based on their HTTP method and checks if they are enabled
        based on feature flags.

        It also implements a blocklist for advanced APIs, which excludes any routes
        with "-advanced" in their path. This blocklist is enabled by default but can
        be disabled by setting the DISABLE_ADVANCED_API_BLOCKLIST environment variable
        to True.

        Args:
            route: The route object from FastMCPOpenAPI
            mcp_type: The default MCPType determined by FastMCPOpenAPI

        Returns:
            MCPType.EXCLUDE if the route is disabled by feature flags or blocklist,
            MCPType.TOOL if the route is a GET endpoint (data source),
            MCPType.TOOL if the route is a POST/PUT/PATCH/DELETE endpoint (action),
            or the original mcp_type if none of the above apply.
        """

        # Check if the route is an advanced API (contains "-advanced" in the path)
        if "-advanced" in route.path:
            # If the blocklist is enabled (DISABLE_ADVANCED_API_BLOCKLIST is False),
            # exclude the route
            if not settings.DISABLE_ADVANCED_API_BLOCKLIST:
                return MCPType.EXCLUDE
            # else, continue with normal categorization

        # Check if the route is enabled based on feature flags
        if not feature_flags.is_api_enabled(route.path, route.method.upper()):
            return MCPType.EXCLUDE

        # Categorize routes based on HTTP method
        if route.method.upper() == "GET":
            return MCPType.TOOL
        elif route.method.upper() in ["POST", "PUT", "PATCH", "DELETE"]:
            return MCPType.TOOL

        # If we can't categorize the route based on HTTP method, return the original mcp_type
        return mcp_type

    async def _fetch_openapi_spec(self) -> dict:
        """Fetch the OpenAPI spec from the URL."""
        if self.openapi_spec_url is None:
            raise ValueError("OPENAPI_SPEC_URL is None. Cannot fetch OpenAPI spec.")

        async with httpx.AsyncClient() as client:
            response = await client.get(str(self.openapi_spec_url))
            response.raise_for_status()
            return response.json()

    async def _extract_api_groups_from_openapi(self) -> None:
        """Extract API groups from the OpenAPI spec for feature flags."""
        # Use the OpenAPI spec that's already stored in the instance
        paths = self.openapi_spec.get("paths", {})

        # Group API paths by tags for feature flags
        for path, methods in paths.items():
            for method, operation in methods.items():
                tags = operation.get("tags", [])

                # Register the path with each tag as a feature flag group
                for tag in tags:
                    # Transform tag name from 'Space Case' to 'lower-case-with-dashes'
                    transformed_tag = self._transform_tag_name(tag)
                    if transformed_tag not in self._api_groups:
                        self._api_groups[transformed_tag] = set()
                    # Store both path and HTTP method as a tuple
                    self._api_groups[transformed_tag].add((path, method.upper()))
                    logger.info(
                        f"Registered route: {method.upper()} {path} to API group: {transformed_tag}")

        # Register API groups with the feature flag manager
        for group_name, paths_with_methods in self._api_groups.items():
            for path, method in paths_with_methods:
                feature_flags.register_api_group(group_name, path, method)

        # Note: FastMCPOpenAPI doesn't provide direct access to routes or a disable_route method
        # Feature flag disabling will need to be handled differently or skipped
        logger.info("API groups registered with feature flag manager")

    async def start(self) -> None:
        """Start the MCP server with the configured transport mode."""
        await self.initialize()

        host = settings.SERVER_HOST
        port = settings.SERVER_PORT
        transport_mode = settings.TRANSPORT_MODE

        if transport_mode == TransportMode.HTTP:
            logger.info(f"Starting MCP server with HTTP transport on {host}:{port}")
            await self.app.run_http_async(host=host, port=port, transport="http")
        elif transport_mode == TransportMode.SSE:
            logger.info(f"Starting MCP server with SSE transport on {host}:{port}")
            await self.app.run_http_async(host=host, port=port, transport="sse")
        elif transport_mode == TransportMode.STDIO:
            logger.info("Starting MCP server with stdio transport")
            await self.app.run_stdio_async()
        else:
            raise ValueError(f"Unsupported transport mode: {transport_mode}")

    async def stop(self) -> None:
        """Stop the MCP server."""
        logger.info("Stopping MCP server")


# Create a global instance for convenience
mcp_server = MCPServer()
