# Absolute Security Secure Endpoint MCP Server

An MCP (Message Control Protocol) server
for [Absolute Security Secure Endpoint Public API](https://api.absolute.com/api-doc/doc.html). Run
it locally and connect it
with [a wide range of supported MCP Client applications](https://modelcontextprotocol.io/clients) to
integrate Absolute to the LLM of your choice and make Absolute work with other systems of your
security stack.

## Usage

### Docker - stdio (Recommended)

```json5
{
  "mcpServers": {
    "absolute-security": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "OPENAPI_SPEC_URL",
        "-e",
        "API_KEY",
        "-e",
        "API_SECRET",
        "-e",
        "TRANSPORT_MODE",
        "ghcr.io/AbsoluteSoftware/secure-endpoint-mcp-server:latest"
      ],
      "env": {
        "API_HOST": "https://api.absolute.com",
        "API_KEY": "<your_symmetric_api_key>",
        "API_SECRET": "<your_symmetric_api_secret>",
        "TRANSPORT_MODE": "stdio"
      }
    }
  }
}
```

### Pypi (coming soon)

## Configuration

### Authentication

This MCP server interacts with Absolute Secure Endpoint Public API on the user's behalf using
__symmetric__ API keys. Please refer to
the [Authentication](https://api.absolute.com/api-doc/doc.html#section/Getting-started:-Create-your-credentials/Create-your-API-token)
section of the Absolute API documentation about how to generate API keys.

### Environment Variables

The following environment variables are optional. The application uses sensible defaults when these
variables are
not provided.

- `API_KEY`: (required) API key for authentication
- `API_SECRET`: (required) API secret for signing requests
- `API_HOST`: The base URL for the Absolute API (default: "https://api.absolute.com").
  See [Public API Doc](https://api.absolute.com/api-doc/doc.html%20target=%22_blank#section/Introduction/Accessing-the-API)
  for all the available endpoints.
- `ABS_FEATURE_*`: Feature flags to enable/disable API groups. For example,
  `ABS_FEATURE_DEVICE_REPORTING=enabled` enables the device-reporting API group, and
  `ABS_FEATURE_DEVICE_REPORTING=disabled` disables it.
- `DISABLE_ADVANCED_API_BLOCKLIST`: Set to `True` to disable the blocklist for advanced APIs.
  When enabled (the default), any API route with "-advanced" in its path is excluded from the MCP
  server.
- `SERVER_HOST`: Host to bind the server to in `sse` or `http` transport mode (default: `0.0.0.0`)
- `SERVER_PORT`: Port to bind the server to in `sse` or `http` transport mode (default: `8000`)
- `LOG_LEVEL`: Logging level (default: `info`). Valid values are `debug`, `info`, `warning`,
  `error`, `critical`.
- `TRANSPORT_MODE`: Transport mode for the MCP server (default: "http"). Valid values are `http`,
  `sse`, `stdio`. The `http` mode starts an HTTP server, the `sse` mode starts a Server-Sent
  Events (SSE) server, and the `stdio` mode uses standard input/output for communication.
- `HTTP_TIMEOUT_SECONDS`: Timeout for HTTP requests in seconds (default: 30)

### Using Feature Flags

Feature flags allow you to enable or disable groups of APIs. APIs are grouped by their tags in the
OpenAPI spec.

```bash
# Enable api_group1 and disable api_group2
export ABS_FEATURE_API_GROUP1=enabled
export ABS_FEATURE_API_GROUP2=disabled
```

By default, if no feature flags are set, only the "device-reporting" feature is enabled.

## Development

### Requirements

- Python 3.13 or higher
- [`uv`](https://github.com/astral-sh/uv) as project and package manager

### Project Structure

- `secure_endpoint_mcp/`: Main package directory
    - `config/`: Configuration management
    - `client/`: HTTP client with symmetric encryption
    - `feature_flags/`: Feature flag implementation
    - `server/`: MCP server implementation
- `tests/`: Unit tests

### Installation

```bash
# Create and activate a virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync
```

### Running Tests

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=secure_endpoint_mcp
```

### MCP Inspector

All the testings below assume that we have the following env vars

```bash
export API_HOST=<api host, for example, https://api.absolute.com>
export API_KEY=<symmetric-api-token-id>
export API_SECRET=<symmetric-api-secret-key>
```

#### Interactive mode

We can run MCP inspector in interactive mode (with browser) to explore the options and its raw
outputs.

```bash
npx @modelcontextprotocol/inspector \
  --transport stdio \
  -e "API_KEY=$API_KEY" \
  -e "API_SECRET=$API_SECRET" \
  -e "API_HOST=$API_HOST" \
  -e LOG_LEVEL=debug \
  -e TRANSPORT_MODE=stdio \
  uv run main.py
```

#### CLI Mode

##### Tools list

```bash
npx @modelcontextprotocol/inspector \
  --cli \
  --method tools/list \
  -e "API_KEY=$API_KEY" \
  -e "API_SECRET=$API_SECRET" \
  -e "API_HOST=$API_HOST" \
  -e LOG_LEVEL=debug \
  -e TRANSPORT_MODE=stdio \
  -- \
  uv run main.py
```

##### Get Devices

```bash
npx @modelcontextprotocol/inspector \
  --cli \
  --method tools/call \
  -e "API_KEY=$API_KEY" \
  -e "API_SECRET=$API_SECRET" \
  -e "API_HOST=$API_HOST" \
  -e LOG_LEVEL=debug \
  -e TRANSPORT_MODE=stdio \
  uv run main.py \
  --tool-name get_devices \
  --tool-arg pageSize=1
```