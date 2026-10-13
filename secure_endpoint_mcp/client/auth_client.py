#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import json
import time
from typing import Any, Dict, Optional, cast

import httpx
from authlib.jose import JsonWebSignature

from secure_endpoint_mcp.config.logging import get_logger
from secure_endpoint_mcp.config.settings import settings

logger = get_logger(__name__)

_PASSTHROUGH_EXCLUDED_HEADERS = {
    "accept",
    "accept-encoding",
    "connection",
    "content-length",
    "content-type",
    "host",
    "user-agent",
}


class AbsoluteAuthClient(httpx.AsyncClient):
    """HTTP client with JWS authentication for Absolute API."""

    def __init__(
        self, api_key: str, api_secret: str, timeout_seconds: int = 30, **kwargs: Any
    ):
        """
        Initialize the client with API credentials.

        Args:
            api_key: The API key (token ID) for authentication
            api_secret: The API secret (token secret) for signing requests
            timeout_seconds: Timeout for HTTP requests in seconds
            **kwargs: Additional keyword arguments to pass to httpx.AsyncClient
        """
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
        signed = cast(str, signed)

        # Log the JWS creation
        logger.debug(f"Created JWS for request: {method} {path}: {signed}")

        return signed

    async def send(
        self,
        request: httpx.Request,
        *,
        stream: bool = False,
        auth: Any = httpx.USE_CLIENT_DEFAULT,
        follow_redirects: Any = httpx.USE_CLIENT_DEFAULT,
    ) -> httpx.Response:
        """
        Sign every outbound request as JWS before sending it.

        Overriding send() (instead of request()) guarantees this runs no matter
        which entry point a caller uses: AsyncClient.get/post/request all build a
        Request and call self.send() internally, and fastmcp>=4.0's OpenAPIProvider
        calls build_request()+send() directly without ever calling request(). An
        earlier version of this client overrode request() only; fastmcp>=4.0 never
        calls it, which silently skipped JWS signing entirely for every real call.

        Args:
            request: The already-built outbound httpx.Request to sign and redirect
                to the JWS validation endpoint.
            stream, auth, follow_redirects: Passed through to the real send().

        Returns:
            The HTTP response from the JWS validation endpoint.
        """
        # Add /v3 prefix to the path, this is necessary for JWS signature generation
        path = request.url.path
        path = "/v3" + path if not path.startswith("/v3") else path
        query_string = request.url.query.decode("ascii")

        json_data: Optional[Dict[str, Any]] = None
        if request.content:
            json_data = json.loads(request.content)

        # Create the JWS payload
        signed_payload = self._prepare_jws_payload(
            request.method, path, query_string, json_data
        )

        # Set the content type for the JWS request, forwarding only genuinely
        # custom headers the caller set -- not httpx's auto-computed transport
        # headers, which described the *original* request, not this replacement
        jws_headers: Dict[str, str] = {"content-type": "text/plain"}
        for key, value in request.headers.items():
            if key.lower() not in _PASSTHROUGH_EXCLUDED_HEADERS:
                jws_headers[key] = value

        # Use a custom API endpoint if the caller set one via extensions,
        # otherwise use the default
        endpoint = request.extensions.get("api_endpoint") or self.api_endpoint

        # Build a fresh request to the JWS validation endpoint and send it via
        # the real httpx.AsyncClient.send() (super(), not self -- calling self.send()
        # here would re-enter this override and double-sign the already-signed payload)
        signed_request = self.build_request(
            "POST", endpoint, content=signed_payload, headers=jws_headers
        )
        return await super().send(
            signed_request, stream=stream, auth=auth, follow_redirects=follow_redirects
        )
