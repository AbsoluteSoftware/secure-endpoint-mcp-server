#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import json
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse

import httpx
from authlib.jose import JsonWebSignature

from secure_endpoint_mcp.config.logging import get_logger
from secure_endpoint_mcp.config.settings import settings

logger = get_logger(__name__)


class AbsoluteAuthClient(httpx.AsyncClient):
    """HTTP client with JWS authentication for Absolute API."""

    def __init__(
        self, api_key: str, api_secret: str, timeout_seconds: int = 30, **kwargs
    ):
        """
        Initialize the client with API credentials.

        Args:
            api_key: The API key (token ID) for authentication
            api_secret: The API secret (token secret) for signing requests
            timeout_seconds: Timeout for HTTP requests in seconds
            **kwargs: Additional keyword arguments to pass to httpx.AsyncClient
        """
        # Initialize the parent class with timeout and any other kwargs
        super().__init__(timeout=timeout_seconds, **kwargs)

        self.token_id = api_key
        self.token_secret = api_secret
        self.api_endpoint = f"{settings.API_HOST}/jws/validate"

    def _prepare_jws_payload(
        self,
        method: str,
        path: str,
        query_string: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Prepare the JWS payload for authentication.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            query_string: Query string from the URL
            json_data: JSON body for the request

        Returns:
            The signed JWS payload as a string
        """

        # Prepare the request payload
        payload = json_data if json_data else {}
        request_payload_data = {"data": payload}

        # Prepare the JWS headers
        headers = {
            "alg": "HS256",
            "kid": self.token_id,
            "method": method.upper(),
            "content-type": "application/json",
            "uri": path,
            "query-string": query_string,
            "issuedAt": round(time.time() * 1000),
        }

        # Create the JWS
        jws = JsonWebSignature()
        signed = jws.serialize_compact(
            headers, json.dumps(request_payload_data), self.token_secret
        )

        # Log the JWS creation
        logger.debug(f"Created JWS for request: {method} {path}: {signed}")

        return signed

    async def request(
        self,
        method: str,
        url: str,
        *,
        content: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Any] = None,
        auth: Optional[Any] = None,
        follow_redirects: Optional[bool] = None,
        timeout: Optional[Any] = None,
        extensions: Optional[Any] = None,
        api_endpoint: Optional[str] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make a request with JWS authentication.

        This method overrides the parent class method to use JWS authentication.
        Instead of making the request directly to the provided URL, it creates a JWS
        payload and sends it to the Absolute API endpoint.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            content, data, files: Request body
            json: JSON body for the request
            params: Query parameters
            headers: Additional headers to include
            cookies, auth, follow_redirects, timeout, extensions: Other httpx parameters
            api_endpoint: Optional override for the API endpoint
            **kwargs: Additional keyword arguments

        Returns:
            The HTTP response
        """

        # Add /v3 prefix to the URL, this is necessary for JWS signature generation
        url = "/v3" + url if not url.startswith("/v3") else url

        # Log the request method and URL
        logger.debug(f"Making request: {method} {url}")

        # Parse the URL to get the path and query string
        parsed_url = urlparse(url)
        path = parsed_url.path
        query_string = parsed_url.query

        # If params are provided, add them to the query string
        if params:
            additional_query = urlencode(params)
            if query_string:
                query_string = f"{query_string}&{additional_query}"
            else:
                query_string = additional_query

        # Create the JWS payload
        signed_payload = self._prepare_jws_payload(method, path, query_string, json)

        # Set the content type for the JWS request
        jws_headers = {"content-type": "text/plain"}

        # Merge with provided headers if any
        if headers:
            for key, value in headers.items():
                if key.lower() != "content-type":  # Don't override content-type
                    jws_headers[key] = value

        # Use custom API endpoint if provided, otherwise use the default
        endpoint = api_endpoint if api_endpoint else self.api_endpoint

        # Make the request to the API endpoint with the signed payload
        return await super().request(
            "POST",  # JWS validation always uses POST
            endpoint,
            content=signed_payload,
            headers=jws_headers,
            cookies=cookies,
            follow_redirects=follow_redirects,
            timeout=timeout,
            extensions=extensions,
            **kwargs,
        )
