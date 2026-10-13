# Usage Guide: Running the Server and Enabling Features

This guide covers how to connect an MCP client to this server and how to control which
Absolute API operations are exposed as tools via feature flags. For how the server works
internally, see the [architecture spec](superpowers/specs/2026-08-06-secure-endpoint-mcp-server-architecture.md).

## 1. Prerequisites

- An Absolute symmetric API key/secret pair (`API_KEY` / `API_SECRET`). See
  [Create your API token](https://api.absolute.com/api-doc/doc.html#section/Getting-started:-Create-your-credentials/Create-your-API-token).
- Docker (recommended, see below) or a local Python 3.13 + [`uv`](https://github.com/astral-sh/uv)
  environment.

## 2. Connecting an MCP Client

The recommended setup runs the published Docker image over stdio. Add this to your MCP
client's server config (e.g. Claude Desktop, Claude Code):

```json5
{
  "mcpServers": {
    "absolute-security": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "API_HOST",
        "-e", "API_KEY",
        "-e", "API_SECRET",
        "-e", "TRANSPORT_MODE",
        "-e", "ABS_FEATURE_DEVICE_REPORTING",
        "ghcr.io/absolutesoftware/secure-endpoint-mcp-server:latest"
      ],
      "env": {
        "API_HOST": "https://api.absolute.com",
        "API_KEY": "<your_symmetric_api_key>",
        "API_SECRET": "<your_symmetric_api_secret>",
        "TRANSPORT_MODE": "stdio",
        "ABS_FEATURE_DEVICE_REPORTING": "enabled"
      }
    }
  }
}
```

Every `ABS_FEATURE_*` variable you want to pass through must be listed both as a
`-e NAME` docker flag **and** in the `env` block — Docker only forwards variables you
explicitly declare with `-e`.

**Without any `ABS_FEATURE_*` variables set, only the `device-reporting` group is
enabled** — every other API group is off by default. Add flags for any additional group
you want to use (see §4).

### Verifying which tools are live

Use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to confirm
what's actually exposed before wiring up a client (requires `uv` and the repo checked
out). It has an interactive (browser) mode and a CLI mode.

#### Interactive mode

Opens a browser UI where you can inspect the tool list, call tools, and view raw
request/response payloads:

```bash
export API_KEY=<your_symmetric_api_key>
export API_SECRET=<your_symmetric_api_secret>
export API_HOST=https://api.absolute.com

npx @modelcontextprotocol/inspector \
  --transport stdio \
  -e "API_KEY=$API_KEY" -e "API_SECRET=$API_SECRET" -e "API_HOST=$API_HOST" \
  -e LOG_LEVEL=debug \
  -e TRANSPORT_MODE=stdio \
  uv run main.py
```

Add any `-e ABS_FEATURE_<GROUP>=enabled` flags you want to test alongside the ones
above, then use the browser's "List Tools" action to see what's exposed.

#### CLI mode

Same idea, but scriptable and non-interactive — prints the tool list as JSON:

```bash
npx @modelcontextprotocol/inspector \
  --cli --method tools/list \
  -e "API_KEY=$API_KEY" -e "API_SECRET=$API_SECRET" -e "API_HOST=$API_HOST" \
  -e TRANSPORT_MODE=stdio \
  uv run main.py
```

`tools/list` only needs the OpenAPI spec fetch to succeed — it does not require valid
credentials, since listing tools happens before any authenticated call is made. To call
a specific tool instead of just listing them (this does require valid credentials):

```bash
npx @modelcontextprotocol/inspector \
  --cli --method tools/call \
  -e "API_KEY=$API_KEY" -e "API_SECRET=$API_SECRET" -e "API_HOST=$API_HOST" \
  -e TRANSPORT_MODE=stdio \
  uv run main.py \
  --tool-name get_devices --tool-arg pageSize="1"
```

> Note: Inspector CLI flag syntax varies by version. If `--method` errors with "No
> servers found" or similar, check `npx @modelcontextprotocol/inspector --cli --help`
> for the flags supported by the version npx resolved.

## 3. How Feature Flags Work (recap)

Every Absolute API operation is tagged in the OpenAPI spec (e.g. `Device Reporting`,
`Freeze`, `Users`). The server transforms each tag into a **group name**
(lowercase, spaces → dashes — e.g. `Device Reporting` → `device-reporting`), then maps
that to an environment variable: `ABS_FEATURE_<GROUP_NAME_UPPER_SNAKE>`.

- `ABS_FEATURE_<GROUP>=enabled` → every operation tagged with that group becomes an MCP
  tool.
- `ABS_FEATURE_<GROUP>=disabled` (or simply omitting the variable) → the group's
  operations are excluded.
- If **no** `ABS_FEATURE_*` variables are set at all, the server falls back to enabling
  only `device-reporting`.
- Independently of feature flags, any route whose path contains `-advanced` (e.g.
  `devices-advanced`) is excluded by default regardless of flags. Set
  `DISABLE_ADVANCED_API_BLOCKLIST=True` to lift that blocklist.

## 4. Feature Flag Reference

The table below lists every group currently defined in Absolute's live OpenAPI spec,
the corresponding environment variable, and the number of operations it controls (as of
the time this guide was written — re-verify with the recipe in §5 if the API evolves).

| Group | Env var | Operations | Enabled by default? |
|---|---|---|---|
| `device-reporting` | `ABS_FEATURE_DEVICE_REPORTING` | 3 | **Yes** |
| `action-thresholds` | `ABS_FEATURE_ACTION_THRESHOLDS` | 2 | No |
| `agents` | `ABS_FEATURE_AGENTS` | 4 | No |
| `application-resilience` | `ABS_FEATURE_APPLICATION_RESILIENCE` | 3 | No |
| `custom-data` | `ABS_FEATURE_CUSTOM_DATA` | 7 | No |
| `custom-fields` | `ABS_FEATURE_CUSTOM_FIELDS` | 7 | No |
| `device-group-tree` | `ABS_FEATURE_DEVICE_GROUP_TREE` | 5 | No |
| `device-groups` | `ABS_FEATURE_DEVICE_GROUPS` | 2 | No |
| `edd-configuration` | `ABS_FEATURE_EDD_CONFIGURATION` | 14 | No |
| `edd-reporting` | `ABS_FEATURE_EDD_REPORTING` | 5 | No |
| `file-delete` | `ABS_FEATURE_FILE_DELETE` | 7 | No |
| `freeze` | `ABS_FEATURE_FREEZE` | 9 | No |
| `geofence` | `ABS_FEATURE_GEOFENCE` | 3 | No |
| `geolocation` | `ABS_FEATURE_GEOLOCATION` | 2 | No |
| `license-configuration` | `ABS_FEATURE_LICENSE_CONFIGURATION` | 1 | No |
| `license-reporting` | `ABS_FEATURE_LICENSE_REPORTING` | 2 | No |
| `messaging` | `ABS_FEATURE_MESSAGING` | 8 | No |
| `missing-devices` | `ABS_FEATURE_MISSING_DEVICES` | 3 | No |
| `perform-edd-scan` | `ABS_FEATURE_PERFORM_EDD_SCAN` | 2 | No |
| `playbook` | `ABS_FEATURE_PLAYBOOK` | 3 | No |
| `policy-groups` | `ABS_FEATURE_POLICY_GROUPS` | 8 | No |
| `reach` | `ABS_FEATURE_REACH` | 11 | No |
| `roles` | `ABS_FEATURE_ROLES` | 1 | No |
| `rsvp` | `ABS_FEATURE_RSVP` | 1 | No |
| `siem-event-reporting` | `ABS_FEATURE_SIEM_EVENT_REPORTING` | 1 | No |
| `software-reporting` | `ABS_FEATURE_SOFTWARE_REPORTING` | 2 | No |
| `tokens` | `ABS_FEATURE_TOKENS` | 2 | No |
| `unenroll` | `ABS_FEATURE_UNENROLL` | 5 | No |
| `users` | `ABS_FEATURE_USERS` | 5 | No |
| `validate-webservice` | `ABS_FEATURE_VALIDATE_WEBSERVICE` | 2 | No |
| `wipe` | `ABS_FEATURE_WIPE` | 7 | No |

For what each group's operations actually do, see the Public API endpoint inventory at
`public-api-service/docs/api-endpoint-inventory.md` (sibling repository — tag names
there match group names here 1:1, modulo the case/dash transform).

## 5. Recipes

### Enable a specific set of groups

Only the groups you list are enabled; everything else stays off (including
`device-reporting`, if you omit it):

```bash
export ABS_FEATURE_DEVICE_REPORTING=enabled
export ABS_FEATURE_USERS=enabled
export ABS_FEATURE_POLICY_GROUPS=enabled
```

### Enable every group

Useful for exploration/testing, not recommended for production least-privilege setups:

```bash
export ABS_FEATURE_ACTION_THRESHOLDS=enabled
export ABS_FEATURE_AGENTS=enabled
export ABS_FEATURE_APPLICATION_RESILIENCE=enabled
export ABS_FEATURE_CUSTOM_DATA=enabled
export ABS_FEATURE_CUSTOM_FIELDS=enabled
export ABS_FEATURE_DEVICE_GROUP_TREE=enabled
export ABS_FEATURE_DEVICE_GROUPS=enabled
export ABS_FEATURE_DEVICE_REPORTING=enabled
export ABS_FEATURE_EDD_CONFIGURATION=enabled
export ABS_FEATURE_EDD_REPORTING=enabled
export ABS_FEATURE_FILE_DELETE=enabled
export ABS_FEATURE_FREEZE=enabled
export ABS_FEATURE_GEOFENCE=enabled
export ABS_FEATURE_GEOLOCATION=enabled
export ABS_FEATURE_LICENSE_CONFIGURATION=enabled
export ABS_FEATURE_LICENSE_REPORTING=enabled
export ABS_FEATURE_MESSAGING=enabled
export ABS_FEATURE_MISSING_DEVICES=enabled
export ABS_FEATURE_PERFORM_EDD_SCAN=enabled
export ABS_FEATURE_PLAYBOOK=enabled
export ABS_FEATURE_POLICY_GROUPS=enabled
export ABS_FEATURE_REACH=enabled
export ABS_FEATURE_ROLES=enabled
export ABS_FEATURE_RSVP=enabled
export ABS_FEATURE_SIEM_EVENT_REPORTING=enabled
export ABS_FEATURE_SOFTWARE_REPORTING=enabled
export ABS_FEATURE_TOKENS=enabled
export ABS_FEATURE_UNENROLL=enabled
export ABS_FEATURE_USERS=enabled
export ABS_FEATURE_VALIDATE_WEBSERVICE=enabled
export ABS_FEATURE_WIPE=enabled
```

### Explicitly disable a group while others are enabled

Flags are independent booleans, so you can mix enabled/disabled explicitly rather than
relying on the "unset = disabled" default:

```bash
export ABS_FEATURE_DEVICE_REPORTING=enabled
export ABS_FEATURE_WIPE=disabled   # redundant with default, but explicit
```

### Include "advanced" endpoints

Advanced endpoints (path contains `-advanced`, e.g. `devices-advanced`) are blocked
independently of feature flags. To include them once their owning group is enabled:

```bash
export ABS_FEATURE_DEVICE_REPORTING=enabled
export DISABLE_ADVANCED_API_BLOCKLIST=True
```

### Re-discover the current group list

Group names and counts can change as Absolute's API evolves. To regenerate the table in
§4 from the live spec:

```bash
uv run python - <<'EOF'
import asyncio, httpx

async def main():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.absolute.com/api-doc/spec/openapi.full.json")
        resp.raise_for_status()
        spec = resp.json()
    groups = {}
    for methods in spec.get("paths", {}).values():
        for op in methods.values():
            for tag in op.get("tags", []):
                key = tag.lower().replace(" ", "-")
                groups[key] = groups.get(key, 0) + 1
    for name, count in sorted(groups.items()):
        print(f"{name}\t{count}")

asyncio.run(main())
EOF
```

## 6. Troubleshooting

- **Server fails to start / hangs on startup:** it fetches the OpenAPI spec from
  `API_HOST` synchronously before it can serve anything. Check network access to
  `API_HOST` and that `API_HOST` is correct (default `https://api.absolute.com`).
- **A tool you expect isn't listed:** confirm the operation's OpenAPI tag maps to a
  group you've enabled (§4), and that the path doesn't contain `-advanced` while the
  blocklist is active (§5).
- **Toggling a flag has no effect:** feature flags are read once at startup — restart
  the server (or container) after changing `ABS_FEATURE_*` values; there is no runtime
  reload.
- **Tool calls fail with auth errors:** verify `API_KEY`/`API_SECRET` are set — spec
  fetch and tool listing don't require valid credentials, but actual tool invocations do
  (they sign a JWS request per call).
