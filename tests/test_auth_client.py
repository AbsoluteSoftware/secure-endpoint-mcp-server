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
    # Mock the parent class send method -- the real interception point: get/post/
    # request all converge on send(), and fastmcp>=4.0 calls build_request()+send()
    # directly without ever calling request()
    with mock.patch("httpx.AsyncClient.send") as mock_send:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_send.return_value = mock_response

        # Mock JsonWebSignature.serialize_compact
        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            # Create the client
            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            # Mock time.time to return a fixed timestamp
            with mock.patch("time.time", return_value=1234567890):
                # Call the method
                response = await client.get("/api/test")

                # Assert that the parent class send method was called
                mock_send.assert_called_once()

                # Get the signed request that was actually sent
                args, kwargs = mock_send.call_args
                sent_request = args[0]

                # Assert that the request was rewritten into a signed JWS call
                assert sent_request.method == "POST"  # JWS validation always uses POST
                assert (
                    str(sent_request.url) == f"{settings.API_HOST}/jws/validate"
                )  # Default API endpoint
                assert sent_request.content == b"mocked.jws.payload"
                assert sent_request.headers["content-type"] == "text/plain"

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
    with mock.patch("httpx.AsyncClient.send") as mock_send:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_send.return_value = mock_response

        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            with mock.patch("time.time", return_value=1234567890):
                # Call the method with a JSON body
                json_body = {"key": "value"}
                response = await client.post("/api/test", json=json_body)

                mock_send.assert_called_once()
                args, kwargs = mock_send.call_args
                sent_request = args[0]

                assert sent_request.method == "POST"
                assert str(sent_request.url) == f"{settings.API_HOST}/jws/validate"
                assert sent_request.content == b"mocked.jws.payload"
                assert sent_request.headers["content-type"] == "text/plain"

                mock_jws.assert_called_once()
                jws_args, jws_kwargs = mock_jws.call_args
                jws_headers, jws_payload, jws_secret = jws_args

                assert jws_headers["alg"] == "HS256"
                assert jws_headers["kid"] == "test_key"
                assert jws_headers["method"] == "POST"
                assert jws_headers["content-type"] == "application/json"
                assert jws_headers["uri"] == "/v3/api/test"
                assert jws_headers["query-string"] == ""
                assert jws_headers["issuedAt"] == 1234567890 * 1000

                expected_payload = json.dumps({"data": json_body})
                assert jws_payload == expected_payload

                assert jws_secret == "test_secret"
                assert response is mock_response


@pytest.mark.asyncio
async def test_auth_client_request():
    """Test that AbsoluteAuthClient.request makes a request with JWS authentication."""
    with mock.patch("httpx.AsyncClient.send") as mock_send:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_send.return_value = mock_response

        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            with mock.patch("time.time", return_value=1234567890):
                # Call the request method with a custom method and params
                response = await client.request(
                    "CUSTOM", "/api/test", params={"param": "value"}
                )

                mock_send.assert_called_once()
                args, kwargs = mock_send.call_args
                sent_request = args[0]

                assert sent_request.method == "POST"
                assert str(sent_request.url) == f"{settings.API_HOST}/jws/validate"
                assert sent_request.content == b"mocked.jws.payload"
                assert sent_request.headers["content-type"] == "text/plain"

                mock_jws.assert_called_once()
                jws_args, jws_kwargs = mock_jws.call_args
                jws_headers, jws_payload, jws_secret = jws_args

                assert jws_headers["alg"] == "HS256"
                assert jws_headers["kid"] == "test_key"
                assert jws_headers["method"] == "CUSTOM"
                assert jws_headers["content-type"] == "application/json"
                assert jws_headers["uri"] == "/v3/api/test"
                assert jws_headers["query-string"] == "param=value"
                assert jws_headers["issuedAt"] == 1234567890 * 1000

                assert jws_payload == '{"data": {}}'
                assert jws_secret == "test_secret"
                assert response is mock_response


@pytest.mark.asyncio
async def test_auth_client_with_custom_headers():
    """Test that AbsoluteAuthClient correctly merges custom headers with JWS headers."""
    with mock.patch("httpx.AsyncClient.send") as mock_send:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_send.return_value = mock_response

        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            with mock.patch("time.time", return_value=1234567890):
                custom_headers = {
                    "Custom-Header": "value",
                    "Another-Header": "another-value",
                }
                response = await client.request(
                    "GET", "/api/test", headers=custom_headers
                )

                mock_send.assert_called_once()
                args, kwargs = mock_send.call_args
                sent_request = args[0]

                assert sent_request.headers["content-type"] == "text/plain"
                assert "custom-header" in sent_request.headers
                assert sent_request.headers["custom-header"] == "value"
                assert "another-header" in sent_request.headers
                assert sent_request.headers["another-header"] == "another-value"
                assert response is mock_response


@pytest.mark.asyncio
async def test_auth_client_with_custom_endpoint():
    """Test that AbsoluteAuthClient uses a custom API endpoint when provided via extensions."""
    with mock.patch("httpx.AsyncClient.send") as mock_send:
        mock_response = mock.MagicMock(spec=httpx.Response)
        mock_send.return_value = mock_response

        with mock.patch("authlib.jose.JsonWebSignature.serialize_compact") as mock_jws:
            mock_jws.return_value = "mocked.jws.payload"

            client = AbsoluteAuthClient(api_key="test_key", api_secret="test_secret")

            with mock.patch("time.time", return_value=1234567890):
                custom_endpoint = "https://api.us.absolute.com/jws/validate"
                response = await client.request(
                    "GET", "/api/test", extensions={"api_endpoint": custom_endpoint}
                )

                mock_send.assert_called_once()
                args, kwargs = mock_send.call_args
                sent_request = args[0]

                assert str(sent_request.url) == custom_endpoint
                assert response is mock_response


@pytest.mark.asyncio
async def test_send_signs_real_request_via_mock_transport():
    """
    End-to-end check with NO internal mocking of this client's own methods: build
    a real AbsoluteAuthClient over an httpx.MockTransport, issue a normal .post()
    call, and assert the transport actually received a signed JWS POST to the
    validate endpoint -- not the original unsigned request.

    This is the regression test for the fastmcp 4.x migration bug where
    AbsoluteAuthClient's signing override (previously on request()) was silently
    bypassed, because fastmcp's OpenAPIProvider calls build_request()+send()
    directly and never calls request(). Real (non-mocked) authlib signing runs
    here, unlike every other test in this file.
    """
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(200, json={"ok": True})

    client = AbsoluteAuthClient(
        api_key="test_key",
        api_secret="test_secret",
        transport=httpx.MockTransport(handler),
    )

    response = await client.post(
        "/configurations/edd-policy/rebuild", json={"foo": "bar"}
    )

    assert response.status_code == 200
    sent_request = captured["request"]

    # The transport must have received the SIGNED request, not the original one
    assert sent_request.method == "POST"
    assert str(sent_request.url) == f"{settings.API_HOST}/jws/validate"
    assert sent_request.headers["content-type"] == "text/plain"

    # The body must be a real compact JWS (header.payload.signature), not the
    # raw unsigned JSON body -- proves real (unmocked) authlib signing ran
    assert sent_request.content.count(b".") == 2
    assert sent_request.content != b'{"foo": "bar"}'


def test_authlib_jose_import_emits_deprecation_warning():
    """authlib>=1.8 deprecates the authlib.jose module (used by auth_client.py
    for JWS signing) in favor of joserfc, with removal planned for authlib
    2.0 (excluded by pyproject.toml's `authlib<2` bound). This test is a
    tripwire: if it starts failing, authlib.jose was either removed (migrate
    auth_client.py to joserfc) or stopped warning (safe to delete this test).
    """
    import importlib
    import warnings

    import authlib.jose
    from authlib.deprecate import AuthlibDeprecationWarning

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.reload(authlib.jose)

        assert any(
            issubclass(w.category, AuthlibDeprecationWarning)
            and "authlib.jose module is deprecated" in str(w.message)
            for w in caught
        )
