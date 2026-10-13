#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import json
import os
import subprocess
import threading
from typing import Any, Dict, Iterator, List

import pytest

_PLACEHOLDER_VALUES = {"dummy_key", "dummy_secret", "", None}


class MCPClient:
    """A real MCP client over stdio, driving the actual packaged Docker image.

    Speaks real JSON-RPC over the process's stdin/stdout -- no mocking
    anywhere in this call path. This is deliberately the same shape a real
    MCP client (Claude Code, Claude Desktop) uses, because the bug this suite
    exists to catch (fastmcp>=4.0 bypassing AbsoluteAuthClient's JWS signing)
    only shows up at this level, never in a test that imports Python
    functions directly.
    """

    def __init__(self, image: str) -> None:
        self._proc = subprocess.Popen(
            [
                "docker",
                "run",
                "-i",
                "--rm",
                "-e",
                "API_HOST",
                "-e",
                "API_KEY",
                "-e",
                "API_SECRET",
                "-e",
                "TRANSPORT_MODE=stdio",
                image,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=os.environ.copy(),
        )
        self.stderr_lines: List[str] = []
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()
        self._next_id = 1
        self.initialize_result: Dict[str, Any] = self._handshake()

    def _drain_stderr(self) -> None:
        assert self._proc.stderr is not None
        for line in self._proc.stderr:
            self.stderr_lines.append(line.rstrip())

    def _send(self, message: Dict[str, Any]) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.write(json.dumps(message) + "\n")
        self._proc.stdin.flush()

    def _recv(self) -> Dict[str, Any]:
        assert self._proc.stdout is not None
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError(
                "MCP server closed its stdout before responding "
                f"(stderr tail: {self.stderr_lines[-10:]})"
            )
        return dict(json.loads(line))

    def _handshake(self) -> Dict[str, Any]:
        self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "tests_qa3", "version": "0.1.0"},
                },
            }
        )
        result = self._recv()
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        self._next_id += 1
        return self._recv()

    def list_tools(self) -> List[Dict[str, Any]]:
        self._send({"jsonrpc": "2.0", "id": self._next_id, "method": "tools/list"})
        self._next_id += 1
        response = self._recv()
        return list(response.get("result", {}).get("tools", []))

    def close(self) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.close()
        try:
            self._proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._stderr_thread.join(timeout=2)


@pytest.fixture
def mcp_client() -> Iterator[MCPClient]:
    for name in ("API_HOST", "API_KEY", "API_SECRET"):
        value = os.environ.get(name)
        if value in _PLACEHOLDER_VALUES:
            raise pytest.UsageError(
                f"{name} is unset or a placeholder value. tests_qa3/ requires "
                "real QA3 credentials -- export API_HOST, API_KEY, API_SECRET "
                "yourself before running (see README.md's MCP Inspector "
                "section for the same pattern). Refusing to run against a "
                "placeholder value."
            )

    image = os.environ.get("MCP_QA3_IMAGE", "secure-endpoint-mcp-server:local")
    client = MCPClient(image)
    yield client
    client.close()
