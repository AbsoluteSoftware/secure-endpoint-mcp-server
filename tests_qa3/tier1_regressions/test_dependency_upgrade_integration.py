#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import json
from typing import Any

import pytest


@pytest.mark.qa3_integration
def test_fastmcp_upgrade_signs_and_reaches_real_api(mcp_client: Any) -> None:
    """
    Prove, against the real QA3 sandbox, that:
    1. The running Docker image actually shipped fastmcp>=4.0 (the upgrade
       this suite exists to verify).
    2. A real tool call succeeds end-to-end through the real MCP client
       protocol -- not mocked, not a Python-function import.
    3. The request was actually signed and reached the real Absolute API --
       the exact property the Critical send()-bypass bug violated (see
       docs/spec/2026-09-21-fastmcp-dependency-upgrade.md and fix commit
       3af5cfa).
    """
    server_info = mcp_client.initialize_result["result"]["serverInfo"]
    assert server_info["name"] == "OpenAPI Server"
    major, minor = (int(p) for p in server_info["version"].split(".")[:2])
    assert (major, minor) >= (
        4,
        0,
    ), f"expected fastmcp>=4.0 in the running image, got {server_info['version']}"

    stderr_before_call = len(mcp_client.stderr_lines)
    result = mcp_client.call_tool("get_devices", {"pageSize": "1"})
    assert "error" not in result, result.get("error")
    payload = json.loads(result["result"]["content"][0]["text"])
    assert isinstance(payload.get("data"), list)

    # Scan only stderr emitted by *this* call, not the whole container
    # lifetime -- otherwise this assertion would stay vacuously true even if
    # a future change moved some other, earlier call off the signed client
    # (e.g. the spec fetch at startup, which already uses a plain
    # httpx.AsyncClient) and only this get_devices call still went through
    # AbsoluteAuthClient. Scoping to post-call lines keeps this a real
    # per-call check, not a lifetime-of-container check.
    jws_lines = [
        line
        for line in mcp_client.stderr_lines[stderr_before_call:]
        if "/jws/validate" in line and "HTTP Request: POST" in line
    ]
    assert jws_lines, (
        "no signed request to /jws/validate observed in container logs -- "
        f"stderr tail: {mcp_client.stderr_lines[-15:]}"
    )
    assert any("200 OK" in line for line in jws_lines), jws_lines
