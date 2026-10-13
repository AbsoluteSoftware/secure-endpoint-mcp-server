# CLAUDE.md

Guidance for Claude Code (and any other coding agent) working in this repository.

## Project Snapshot

This is an MCP (Model Context Protocol) server that exposes the [Absolute Security
Secure Endpoint Public API](https://api.absolute.com/api-doc/doc.html) as MCP tools,
built on `fastmcp`.

**The most important architectural fact:** the tool surface is spec-driven, not
hand-written. At startup, `MCPServer` (`secure_endpoint_mcp/server/mcp_server.py`)
fetches Absolute's live OpenAPI document and uses FastMCP's `FastMCPOpenAPI` adapter
to generate one MCP tool per API operation automatically. This means:

- There is no list of tools to edit in code. "Add a tool" is almost never the right
  instinct here.
- Controlling which tools are exposed is done declaratively, via `ABS_FEATURE_*`
  feature flags (`secure_endpoint_mcp/feature_flags/manager.py`) and the advanced-API
  path blocklist — not by editing a tool registry.
- See `docs/spec/2026-08-06-secure-endpoint-mcp-server-architecture.md`
  for the full architecture writeup before making structural changes.

## Commands

```bash
# Install dependencies (dev extras)
uv sync
uv pip install -e ".[dev]"

# Run tests
uv run pytest
uv run pytest --cov=secure_endpoint_mcp

# Lint / format / type-check
uv run black secure_endpoint_mcp tests
uv run isort secure_endpoint_mcp tests
uv run mypy secure_endpoint_mcp
```

## Project Layout

- `secure_endpoint_mcp/config/` — Pydantic settings (`settings.py`) and structlog JSON
  logging (`logging.py`).
- `secure_endpoint_mcp/client/` — `AbsoluteAuthClient`, the `httpx` client subclass
  that signs requests as JWS.
- `secure_endpoint_mcp/feature_flags/` — `FeatureFlagManager`, tag-based API group
  enable/disable.
- `secure_endpoint_mcp/server/` — `MCPServer` (startup orchestration) and
  `schema_fix` (works around broken `$ref`s in the upstream OpenAPI spec).
- `tests/` — unit tests, one module per source module.

For environment variables, Docker usage, and feature-flag operation, see
`README.md` and `docs/usage-guide.md` — don't duplicate that content here.

## Spec-First Workflow

All design and planning documents live under `docs/` — never under any other tool-specific default location. This applies
regardless of which agent or skill produces the document.

- **Specs** live in `docs/spec/`, named `YYYY-MM-DD-<topic>-design.md` (see the
  existing docs there for examples).
- **Implementation plans** live in `docs/plans/`, named `YYYY-MM-DD-<topic>.md`.
   Save any plans to `docs/plans/`.

- **Architectural changes** (new subsystems, changes to how components fit
  together, anything that alters interfaces other code depends on): write a spec to
  `docs/spec/` and get it reviewed *before* writing implementation code.
- **Bounded changes** (a fix or small addition to an existing flow): a short design
  stated in chat and approved is enough — no spec file needed.

When in doubt, treat it as architectural. A spec that turns out to be unnecessary
costs little; skipping one for something that needed it costs a rebuild.

## Working Guidelines

**Think before coding.** Don't assume — state assumptions explicitly. If multiple
interpretations exist, present them instead of silently picking one. If something is
unclear, stop and ask rather than guessing.

**Simplicity first.** Write the minimum code that solves the problem. No speculative
abstractions, no "flexibility" that wasn't requested, no error handling for scenarios
that can't happen. If it could be half the size, rewrite it.

**Surgical changes.** Touch only what the task requires. Don't refactor or reformat
adjacent code, even if you'd write it differently. Every changed line should trace
back to the request. Clean up only the mess your own change creates (e.g. now-unused
imports) — leave pre-existing dead code alone, just mention it.

**Goal-driven execution.** Turn tasks into verifiable success criteria before
starting ("fix the bug" → "write a failing test that reproduces it, then make it
pass") and confirm against them before declaring done.
