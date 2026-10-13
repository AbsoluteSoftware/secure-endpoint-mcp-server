# QA3 Real Integration Test Suite — Design

**Date:** 2026-09-23
**Scope:** A new, separate test suite that drives the actual built Docker image over real MCP stdio, against the real QA3 sandbox, to prove specific known-defect regressions and dependency-upgrade correctness that unit tests structurally cannot catch.

## 1. Background

`docs/testing.md` documents, as a fact about this repo, that everything under `tests/` is a pure unit-test suite: httpx, `authlib` JWS signing, and FastMCP's `FastMCPOpenAPI`/`OpenAPIProvider` are all mocked, with zero live network or filesystem I/O. That design is correct for what it covers — but this session found a Critical bug that lived exactly in the gap that design leaves open: the `2026-09-21-fastmcp-dependency-upgrade` plan's final whole-branch review discovered that fastmcp 4.x's `OpenAPIProvider` calls `build_request()`+`send()` directly, silently bypassing `AbsoluteAuthClient`'s `request()`-based JWS signing override. Every unit test passed (97% coverage) throughout, because none of them exercised a real, unmocked request through the real framework integration. The bug was only caught by a whole-branch architectural review, then confirmed via ad-hoc manual `docker run` + raw stdio JSON-RPC probing in this same session — evidence that worked, but was never captured as a repeatable, automated check.

This spec turns that ad-hoc manual verification into a real, repeatable, separate test suite — scoped down (per direct instruction during brainstorming) to proving the fastmcp/dependency upgrade's real end-to-end integration first. A broader defect-regression and general-health-check scope was discussed and is captured as deferred future work (§6), not built now.

## 2. Goals / Non-goals

**Goals:**

- Prove, automatically and repeatably, that a request from a real MCP client (spawning the actual built Docker image over real stdio) reaches the real Absolute API signed correctly — the exact property the Critical bug violated and no existing test covers.
- Prove the fastmcp dependency bump actually shipped in the running artifact (assert the reported fastmcp version, not just "some version runs").
- Keep this suite fully separate from `tests/`, so `docs/testing.md`'s "no live I/O" claim about `tests/` stays true, and so this suite never accidentally runs in default CI or default `uv run pytest`.

**Non-goals (this round):**

- The four other known-defect scenarios discussed during brainstorming (bodyless-write body-shape bug, dangling `$ref`, dropped array-body schemas, binary-response mis-decoding) — deferred, see §6.
- Any broader "general health check" scenario coverage across API groups — deferred, see §6.
- Any destructive or state-mutating scenario — this round is read-only only.
- CI integration of any kind (scheduled or on-demand) — local, manual invocation only for now.
- Fixing the bodyless-write body-shape bug (ABS-300501/300503) itself — tracked separately, untouched here.

## 3. Architecture

New top-level directory, sibling to `tests/`, not nested inside it:

```
tests_qa3/
  conftest.py                          # mcp_client fixture, credential loading, fail-fast checks
  tier1_regressions/
    test_dependency_upgrade_integration.py
```

Keeping this outside `tests/` is deliberate, not cosmetic: `docs/testing.md` states "all tests are unit tests with no live network or filesystem I/O" as a fact about `tests/`. Nesting a real-network suite inside it would make that statement false. `pyproject.toml`'s `[tool.pytest.ini_options]` `testpaths = ["tests"]` already excludes `tests_qa3/` from any bare `uv run pytest` invocation without needing a marker-based opt-out — this suite is invisible to the default suite and to CI by construction, not by convention that could be forgotten.

The `qa3_integration` marker used in §3.2 is not load-bearing for that exclusion — it's there for clarity when running `tests_qa3/` directly (`-m qa3_integration`), and as defense-in-depth if `testpaths` is ever widened later. It needs registering in `pyproject.toml`'s `[tool.pytest.ini_options]` (`markers = ["qa3_integration: real-network test against the QA3 sandbox, run manually only"]`) — otherwise pytest emits an "unknown mark" warning, which this repo's existing test-report conventions treat as a defect (test output must be pristine).

### 3.1 The `mcp_client` fixture

The one reusable component, in `tests_qa3/conftest.py`. It formalizes the manual pattern already validated twice this session (`/tmp/mcp_stdio_probe.py`, `/tmp/mcp_real_probe.py`):

- **Setup:** reads `API_HOST`, `API_KEY`, `API_SECRET` from the environment. Fails immediately with a clear `pytest.UsageError` (not a cryptic downstream connection error) if any are unset or equal to a placeholder like `dummy_key` — this suite only means something against real credentials.
- Spawns `docker run -i --rm -e API_HOST -e API_KEY -e API_SECRET -e TRANSPORT_MODE=stdio <image>` as a subprocess, where `<image>` defaults to `secure-endpoint-mcp-server:local` (the tag used throughout this session) but is overridable via an `MCP_QA3_IMAGE` env var — so the suite can later point at `ghcr.io/absolutesoftware/secure-endpoint-mcp-server:latest` for a pre-release sanity check without a code change.
- Performs the real `initialize` / `notifications/initialized` handshake over the subprocess's stdin/stdout, capturing stderr separately (this is where the `POST .../jws/validate` evidence line lives).
- Exposes exactly two methods to test bodies: `call_tool(name: str, arguments: dict) -> dict` and `list_tools() -> list[dict]`. Both are real JSON-RPC round trips — no mocking anywhere in this call path.
- Exposes `initialize_result` (the raw `initialize` response, for asserting `serverInfo`) and `stderr_lines` (for asserting the signing evidence line).
- Teardown: closes stdin, waits with a timeout, kills the container if it hangs. `--rm` guarantees no leftover containers even on a hard kill.

### 3.2 The scenario

`tests_qa3/tier1_regressions/test_dependency_upgrade_integration.py`, one test function for this round:

```python
@pytest.mark.qa3_integration
def test_fastmcp_upgrade_signs_and_reaches_real_api(mcp_client):
    # 1. Prove the upgrade actually shipped in the running artifact
    server_info = mcp_client.initialize_result["result"]["serverInfo"]
    assert server_info["name"] == "OpenAPI Server"
    major, minor = (int(p) for p in server_info["version"].split(".")[:2])
    assert (major, minor) >= (4, 0), (
        f"expected fastmcp>=4.0 in the running image, got {server_info['version']}"
    )

    # 2. Prove a real tool call succeeds end-to-end (not a connection failure)
    result = mcp_client.call_tool("get_devices", {"pageSize": "1"})
    assert "error" not in result, result.get("error")
    payload = json.loads(result["result"]["content"][0]["text"])
    assert isinstance(payload.get("data"), list)

    # 3. Prove the request was actually signed and reached the real endpoint --
    # the exact property the Critical send()-bypass bug violated
    jws_lines = [
        l for l in mcp_client.stderr_lines
        if "/jws/validate" in l and "HTTP Request: POST" in l
    ]
    assert jws_lines, "no signed request to /jws/validate observed in container logs"
    assert any("200 OK" in l for l in jws_lines)
```

Exact assertion syntax will be finalized during implementation against real captured output (the fixture's log format needs confirming against a live run first) — the plan will treat this as a spike-and-confirm step, not blind transcription.

## 4. Credentials & execution

Environment variables only, matching the existing README "MCP Inspector" pattern exactly (`API_HOST`, `API_KEY`, `API_SECRET`) — no new credential mechanism introduced. Never written to a file, never logged (the fixture must redact `API_SECRET` from any error message it constructs).

Invocation: `uv run pytest tests_qa3/ -v`. Never part of `uv run pytest` (bare), never wired into `.github/workflows/ci.yml`. A developer runs this manually, by hand, when they want to verify a real integration point (a dependency bump, a fastmcp version bump, a change to `auth_client.py`) actually works against the real API — exactly the situation this session was in.

## 5. Reporting

A dated markdown snapshot, `docs/test-reports/YYYY-MM-DD-qa3-integration.md`, following the exact format already established by `docs/test-reports/2026-09-09-baseline.md` and `2026-09-21-fastmcp-4-upgrade.md`: environment, command run, pass/fail result, and — specific to this suite — the redacted evidence line (`POST .../jws/validate ... 200 OK`) that proves real signing occurred, since that's the whole point of this suite and worth keeping as a permanent, dated record. Generated by hand after a run for now (copy the real terminal output into the template, same process already used for the two existing snapshots) — no new reporting tooling built for a single scenario.

## 6. Deferred scope (explicitly not built this round)

Captured here so this doesn't need re-litigating when picked up later:

- **Bodyless-write body-shape regression** (ABS-300501/300503) — call `policy_groups_activate_policies` on a dynamically-discovered `deviceCount:0` policy group; expected to currently fail (`xfail`) until the separate, still-open body-shape fix lands.
- **Dangling `$ref` / PointerToNowhere** (Group B, 6 tickets) — schema-only check (`tools/list`) on `create_cdc_configurations`, no real call; settles whether fastmcp 4.x's rewrite fixed this incidentally.
- **Dropped array-body schema** (ABS-300687) — schema-only check on `update_device_cdf`.
- **Binary response mis-decoding** (ABS-299630) — needs a concrete safe (non-destructive) binary-download tool identified first; not yet chosen.
- **Tier 2 general health-check scenarios** — broader smoke coverage across API groups, pagination, error handling, feature-flag gating. Shape not yet designed.
- Safe-target dynamic-discovery helper (query read-only, filter for `deviceCount: 0` or equivalent zero-impact target) — needed once any write-shaped scenario (item 1 above) is built; not needed for this round's read-only scenario.

## 7. Risks / rollback

This suite only reads from a real account (`get_devices`) in this round — no state mutation, so no rollback concern. The suite itself is new files only; deleting `tests_qa3/` fully removes it with no effect on `tests/` or production code. The only operational risk is credential handling — mitigated by env-var-only sourcing (never written to disk) and fail-fast validation against placeholder values.
