#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import json
from unittest import mock

import httpx
import pytest

from secure_endpoint_mcp.client.auth_client import AbsoluteAuthClient
from secure_endpoint_mcp.config.settings import settings


@pytest.mark.asyncio
async def test_auth_client_get():
    """Test that AbsoluteAuthClient.get makes a request with JWS authentication."""
    # Mock the parent class request method
    with mock.patch("httpx.AsyncClient.request") as mock_request:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_request.return_value = mock_response

        # Mock JsonWebSignature.serialize_compact
        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            # Create the client
            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            # Mock time.time to return a fixed timestamp
            with mock.patch("time.time", return_value=1234567890):
                # Call the method
                response = await client.get("/api/test")

                # Assert that the parent class request method was called
                mock_request.assert_called_once()

                # Get the parameters from the call
                args, kwargs = mock_request.call_args
                # First positional argument is the method, second is the URL
                method, url = args
                content = kwargs.get("content")
                headers = kwargs.get("headers", {})

                # Assert that the parameters were passed correctly
                assert method == "POST"  # JWS validation always uses POST
                assert url == f"{settings.API_HOST}/jws/validate"  # Default API endpoint
                assert content == "mocked.jws.payload"
                assert headers["content-type"] == "text/plain"

                # Assert that JsonWebSignature.serialize_compact was called with the correct parameters
                mock_jws.assert_called_once()
                jws_args, jws_kwargs = mock_jws.call_args
                jws_headers, jws_payload, jws_secret = jws_args

                # Verify JWS headers
                assert jws_headers["alg"] == "HS256"
                assert jws_headers["kid"] == "test_key"
                assert jws_headers["method"] == "GET"
                assert jws_headers["content-type"] == "application/json"
                assert jws_headers["uri"] == "/v3/api/test"
                assert jws_headers["query-string"] == ""
                assert jws_headers["issuedAt"] == 1234567890 * 1000

                # Verify JWS payload
                assert jws_payload == '{"data": {}}'

                # Verify JWS secret
                assert jws_secret == "test_secret"

                # Assert that the response is the mock response
                assert response is mock_response


@pytest.mark.asyncio
async def test_auth_client_post():
    """Test that AbsoluteAuthClient.post makes a request with JWS authentication."""
    # Mock the parent class request method
    with mock.patch("httpx.AsyncClient.request") as mock_request:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_request.return_value = mock_response

        # Mock JsonWebSignature.serialize_compact
        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            # Create the client
            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            # Mock time.time to return a fixed timestamp
            with mock.patch("time.time", return_value=1234567890):
                # Call the method with a JSON body
                json_body = {"key": "value"}
                response = await client.post("/api/test", json=json_body)

                # Assert that the parent class request method was called
                mock_request.assert_called_once()

                # Get the parameters from the call
                args, kwargs = mock_request.call_args
                # First positional argument is the method, second is the URL
                method, url = args
                content = kwargs.get("content")
                headers = kwargs.get("headers", {})

                # Assert that the parameters were passed correctly
                assert method == "POST"  # JWS validation always uses POST
                assert url == f"{settings.API_HOST}/jws/validate"  # Default API endpoint
                assert content == "mocked.jws.payload"
                assert headers["content-type"] == "text/plain"

                # Assert that JsonWebSignature.serialize_compact was called with the correct parameters
                mock_jws.assert_called_once()
                jws_args, jws_kwargs = mock_jws.call_args
                jws_headers, jws_payload, jws_secret = jws_args

                # Verify JWS headers
                assert jws_headers["alg"] == "HS256"
                assert jws_headers["kid"] == "test_key"
                assert jws_headers["method"] == "POST"
                assert jws_headers["content-type"] == "application/json"
                assert jws_headers["uri"] == "/v3/api/test"
                assert jws_headers["query-string"] == ""
                assert jws_headers["issuedAt"] == 1234567890 * 1000

                # Verify JWS payload
                expected_payload = json.dumps({"data": json_body})
                assert jws_payload == expected_payload

                # Verify JWS secret
                assert jws_secret == "test_secret"

                # Assert that the response is the mock response
                assert response is mock_response


@pytest.mark.asyncio
async def test_auth_client_request():
    """Test that AbsoluteAuthClient.request makes a request with JWS authentication."""
    # Mock the parent class request method
    with mock.patch("httpx.AsyncClient.request") as mock_request:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_request.return_value = mock_response

        # Mock JsonWebSignature.serialize_compact
        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            # Create the client
            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            # Mock time.time to return a fixed timestamp
            with mock.patch("time.time", return_value=1234567890):
                # Call the request method with a custom method and params
                response = await client.request(
                    "CUSTOM",
                    "/api/test",
                    params={"param": "value"}
                )

                # Assert that the parent class request method was called
                mock_request.assert_called_once()

                # Get the parameters from the call
                args, kwargs = mock_request.call_args
                # First positional argument is the method, second is the URL
                method, url = args
                content = kwargs.get("content")
                headers = kwargs.get("headers", {})

                # Assert that the parameters were passed correctly
                assert method == "POST"  # JWS validation always uses POST
                assert url == f"{settings.API_HOST}/jws/validate"  # Default API endpoint
                assert content == "mocked.jws.payload"
                assert headers["content-type"] == "text/plain"

                # Assert that JsonWebSignature.serialize_compact was called with the correct parameters
                mock_jws.assert_called_once()
                jws_args, jws_kwargs = mock_jws.call_args
                jws_headers, jws_payload, jws_secret = jws_args

                # Verify JWS headers
                assert jws_headers["alg"] == "HS256"
                assert jws_headers["kid"] == "test_key"
                assert jws_headers["method"] == "CUSTOM"
                assert jws_headers["content-type"] == "application/json"
                assert jws_headers["uri"] == "/v3/api/test"
                assert jws_headers["query-string"] == "param=value"
                assert jws_headers["issuedAt"] == 1234567890 * 1000

                # Verify JWS payload
                assert jws_payload == '{"data": {}}'

                # Verify JWS secret
                assert jws_secret == "test_secret"

                # Assert that the response is the mock response
                assert response is mock_response


@pytest.mark.asyncio
async def test_auth_client_with_custom_headers():
    """Test that AbsoluteAuthClient correctly merges custom headers with JWS headers."""
    # Mock the parent class request method
    with mock.patch("httpx.AsyncClient.request") as mock_request:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_request.return_value = mock_response

        # Mock JsonWebSignature.serialize_compact
        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            # Create the client
            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            # Mock time.time to return a fixed timestamp
            with mock.patch("time.time", return_value=1234567890):
                # Call the request method with custom headers
                custom_headers = {"Custom-Header": "value", "Another-Header": "another-value"}
                response = await client.request(
                    "GET",
                    "/api/test",
                    headers=custom_headers
                )

                # Assert that the parent class request method was called
                mock_request.assert_called_once()

                # Get the headers from the call
                args, kwargs = mock_request.call_args
                headers = kwargs.get("headers", {})

                # Assert that both custom and JWS headers are present
                assert headers["content-type"] == "text/plain"  # JWS content type
                assert "Custom-Header" in headers
                assert headers["Custom-Header"] == "value"
                assert "Another-Header" in headers
                assert headers["Another-Header"] == "another-value"

                # Assert that the response is the mock response
                assert response is mock_response


@pytest.mark.asyncio
async def test_auth_client_with_custom_endpoint():
    """Test that AbsoluteAuthClient uses a custom API endpoint when provided."""
    # Mock the parent class request method
    with mock.patch("httpx.AsyncClient.request") as mock_request:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_request.return_value = mock_response

        # Mock JsonWebSignature.serialize_compact
        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            # Create the client
            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            # Mock time.time to return a fixed timestamp
            with mock.patch("time.time", return_value=1234567890):
                # Call the request method with a custom API endpoint
                custom_endpoint = "https://api.us.absolute.com/jws/validate"
                response = await client.request(
                    "GET",
                    "/api/test",
                    api_endpoint=custom_endpoint
                )

                # Assert that the parent class request method was called
                mock_request.assert_called_once()

                # Get the parameters from the call
                args, kwargs = mock_request.call_args
                # First positional argument is the method, second is the URL
                method, url = args

                # Assert that the custom API endpoint was used
                assert url == custom_endpoint

                # Assert that the response is the mock response
                assert response is mock_response
