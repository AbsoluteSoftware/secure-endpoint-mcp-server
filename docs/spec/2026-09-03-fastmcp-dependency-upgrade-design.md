# Secure Endpoint MCP Server — Dependency Upgrade Design

**Date:** 2026-09-03
— "Update dependencies of absolute public api mcp server"
**Scope:** Bump `fastmcp`/`mcp` and all transitive dependencies to latest, eliminate known CVEs, and add guardrails so this doesn't silently drift again.

## 1. Background

The repo has been running `fastmcp==2.12.4` / `mcp==1.15.0` for roughly a year. `pyproject.toml`
declares every dependency as a bare name with no version constraint at all, so the lockfile
drifted two `fastmcp` majors (2.x → 4.x) and one `mcp` major (1.x → 2.x) behind without any PR
ever surfacing the jump. The ticket was raised because:

- There is a client building a Claude integration against this server, so
  staying current and CVE-clean is now externally visible, not just internal hygiene.
- A CVE table posted to the ticket flagged 12 CVEs across 8
  packages. That table itself undercounts the real exposure — see below.

**Verified CVE count (2026-09-21, queried directly against OSV.dev by package+version, deduped by
CVE alias — not taken from the Jira comment or any single tool's word alone):**

| Package | Locked version | Distinct advisories | Worst CVSS | Notably includes |
| --- | --- | --- | --- | --- |
| `authlib` | 1.6.0 | 10 | 9.1 | CVE-2026-27962 — JWS JWK header injection, **signature verification bypass** |
| `fastmcp` | 2.12.4 | 8 | 10.0 | CVE-2026-32871 — OpenAPI provider SSRF & path traversal |
| `starlette` | 0.47.1 | 7 | 7.5 | CVE-2026-54283 — form-limit DoS; CVE-2026-48710 — Host header poisons `request.url.path` |
| `cryptography` | 45.0.5 | 7 | — | subgroup-validation, DNS-constraint, and buffer-overflow issues |
| `urllib3` | 2.5.0 | 4 | 7.5 | decompression-bomb / redirect-chain issues |
| `mcp` | 1.15.0 | 3 | 8.1 | CVE-2025-66416 — DNS rebinding; CVE-2026-52869 — session hijack w/o origin check |
| `idna` | 3.10 | 1 | — | CVE-2026-45409 |
| `pygments` | 2.19.2 | 1 | — | CVE-2026-4539 — ReDoS |
| `requests` | 2.32.5 | 1 | — | CVE-2026-25645 — insecure temp-file reuse |

**42 distinct advisories across 9 packages** — none of them direct dependencies of this repo
(`pyproject.toml` only declares `fastmcp`, `httpx`, `pydantic`, `pydantic-settings`, `pytest`,
`python-dotenv`, `structlog`, `html2text`); all 9 are pulled in transitively through `fastmcp`/`mcp`.
This is well beyond both the original 8-CVE/4-package pip-audit scope this spec started from and
the 12-CVE/8-package table posted to the ticket — the ticket's table was itself a partial ("FYI")
list, not exhaustive. `authlib` (this repo's JWS-signing dependency — see §3) and `fastmcp` itself
carry the two most severe findings (9.1 and 10.0 CVSS), which is the strongest argument for why this
bump can't be treated as routine hygiene.

**Verified: does the planned bump actually clear all 42?** Ran a real `uv lock` (not just PyPI
metadata) in an isolated scratch copy of `pyproject.toml` with `fastmcp>=4.0,<5` — the resolver
picked `fastmcp==4.0.5`, `mcp==2.2.0`, `authlib==1.8.0`, `starlette==1.6.0`, `cryptography==50.0.1`,
`idna==3.20`, `pygments==2.21.0`, and — notably — **`requests`/`urllib3`/`openapi-core` no longer
appear in the resolved tree at all** under `fastmcp` 4.x (see §3.1). Checked every one of those
resolved versions against OSV.dev directly: all clean, 0 remaining vulnerabilities. So the bump does
clear everything, but only because the resolver's default "pick latest compatible" behavior lands
above the floors `fastmcp-slim`/`mcp` themselves declare (`authlib>=1.6.11`, `starlette>=1.0.1`) —
both of which, verified independently, are *not* sufficient on their own (`authlib==1.6.11` still
carries 2 open CVEs, `starlette==1.0.1` still carries 8). See §5 for why that gap should be closed
with explicit direct-dependency floors rather than left to resolver defaults.

- The existing UAT remediation spec
  (`docs/spec/2026-08-25-secure-endpoint-mcp-uat-remediation-design.md`) separately flagged three
  defects living inside `fastmcp` itself (dangling `$ref` resolution, dropped array-body schemas,
  binary-response mis-decoding) and recommended checking whether a newer `fastmcp` release already
  fixes them. **That verification is explicitly out of scope for this ticket** (see §2) — it is
  tracked as its own follow-up, even though this upgrade is a prerequisite for ever running that
  check. One new wrinkle for that follow-up: §3.1 below found that `fastmcp` 4.x's OpenAPI provider
  drops the `openapi-core`/`requests`/`urllib3` dependency chain entirely, which strongly suggests
  the OpenAPI parsing internals (`fastmcp/utilities/openapi.py`, where all three Group B root causes
  live) were rewritten, not just patched — worth flagging to whoever picks up that ticket so they
  don't assume the old file/line references still apply.

## 2. Goals / Non-goals

**Goals:**

- Bump `fastmcp` `2.12.4` → `4.x` and `mcp` `1.15.0` → `2.x` in a single jump (no staged
  2.x→3.x→4.x bisection), fixing whatever breaks along the way. Use range constraints
  (`fastmcp>=4.0,<5`, `mcp>=2.1,<3`) rather than exact pins, since verification (§1) showed the
  resolver already lands on newer, equally-clean patch releases (`4.0.5`/`2.2.0` as of 2026-09-21)
  — pinning the exact versions checked today would immediately go stale.
- Resolve all transitive dependencies to latest via `uv lock --upgrade` and confirm all **42**
  verified findings from §1 are cleared (not the original 8 this spec started from) — re-check
  against OSV.dev/`pip-audit` after locking, don't assume the bump clears them just because it did
  in the §1 scratch-dir verification.
- Add version bounds to every direct dependency in `pyproject.toml` (currently unconstrained bare
  names), **add explicit direct-dependency floors for the security-critical transitive packages
  identified in §5** (`authlib`, `starlette`), and add GitHub Dependabot for the Python ecosystem,
  so future upgrades arrive as small, reviewed PRs instead of another silent multi-major drift.

**Non-goals:**

- No UAT remediation work. Group A (`_prepare_jws_payload` bodyless-write fix), Group B (fastmcp
  internal `$ref`/array-body/binary-response defects), and every other item in the 2026-08-25 UAT
  design doc stay out of scope. If this upgrade happens to fix a Group B defect as a side effect,
  note it in the PR description for the record — do not scope-creep into verifying or fixing it
  here.
- No new tools, features, or behavior changes beyond what's required to keep the server working
  under the new dependency versions.
- No CI workflow redesign beyond adding the Dependabot config itself.

## 3. Key risk: `httpx` vs `httpx2` in the auth path

**Confirmed, not hedged:** checked `mcp`'s published metadata directly (`pip download`-equivalent
PyPI JSON for `mcp==2.1.1` and the resolver-selected `2.2.0`) — both declare `httpx2>=2.5.0` as a
hard dependency. This lands in stable, it was not reverted. Separately, `starlette` is required at
`>=0.27` for `python_version < "3.14"` or `>=0.48.0` for `python_version >= "3.14"` — this repo's
`requires-python = ">=3.13"` means either branch can apply depending on the interpreter actually
used to lock/run, but neither caps the resolver below the fully-patched `1.6.0` (verified in the
scratch-dir lock in §1, which ran under Python 3.14.2 and landed on `starlette==1.6.0` regardless).

This repo's entire auth mechanism is `AbsoluteAuthClient` (`client/auth_client.py`), a subclass of
`httpx.AsyncClient` whose overridden `request()` is handed to `FastMCPOpenAPI` as the backend HTTP
client used for every call to Absolute's API. That is a different layer from the MCP
client↔server transport `httpx2` note is describing — confirmed via the scratch-dir lock in §1,
where plain `httpx` stayed at `0.28.1` (untouched) while `httpx2` (`2.13.0`) was added alongside it
as a new, separate transitive dependency of `mcp`. The two packages coexist; `httpx2` does not
replace this repo's own `httpx.AsyncClient` usage. Still to confirm by reading actual `fastmcp`
4.x source against a real install (not release-note wording) before writing code:

1. `FastMCPOpenAPI` (or its 4.x equivalent) still accepts a real `httpx.AsyncClient` (or subclass)
   as its backend client parameter.
2. The `mcp_component_fn` hook (`schema_fix.py`'s output-schema-disabling mechanism) and the
   `_route_map_fn` signature (`mcp_server.py`) are unchanged, or have a clear, mechanical migration
   path if renamed/reshaped.
3. Nothing this server actually uses collides with "FastMCP 3's deprecated APIs are gone" or the
   4.0.0 removal of server-initiated sampling/roots — this server doesn't use sampling or
   elicitation, so this is expected to be a non-issue, but must be confirmed rather than assumed.

### 3.1 New finding: `fastmcp` 4.x drops `openapi-core`/`requests`/`urllib3`

The scratch-dir `uv lock` in §1 resolved with `fastmcp>=4.0,<5` present but **no `requests`,
`urllib3`, or `openapi-core` anywhere in the 92-package lock** — all three were transitive children
of `fastmcp==2.12.4` (via `openapi-core` → `jsonschema-path` → `requests` → `urllib3`) and are
absent under `fastmcp` 4.x. Two implications:

- The `requests`/`urllib3` CVEs in §1 are cleared by *removal*, not by patching — there is no
  version of these packages installed at all post-upgrade, so there's nothing to pin or track for
  them going forward (contrast with `authlib`/`starlette`, which remain present and need the
  explicit floors in §5).
- `fastmcp` also depends on a new split package, `fastmcp-slim` (PyPI metadata: `fastmcp==4.0.5`
  requires `fastmcp-slim[client,server]==4.0.5`), which is where `authlib`/`starlette` are now
  declared (`authlib>=1.6.11`, `starlette>=1.0.1` for the `client`/`server`/`mcp` extras). This is
  a real internal restructuring, not just a version bump — the OpenAPI-provider internals this
  server touches indirectly (`fastmcp/utilities/openapi.py`, where every Group B defect in the
  2026-08-25 UAT spec lives) very likely moved or were rewritten rather than patched in place.
  Whoever verifies the UAT spec's Group B items against 4.x should expect to relocate those
  functions, not find them at the same file/line.

## 4. Execution plan

1. **Spike/verify** — install `fastmcp` (`>=4.0,<5`) and `mcp` (`>=2.1,<3`) into a scratch venv and
   read the installed source directly for the three confirmations in §3 and the `fastmcp-slim`
   split in §3.1. This determines the actual scope of code changes needed in step 3, rather than
   guessing from release notes.
2. **Add version bounds and re-lock** — change every bare dependency name in `pyproject.toml` to a
   compatible-range constraint (`fastmcp>=4.0,<5`, `mcp>=2.1,<3`, and similar bounds for `httpx`,
   `pydantic`, `pydantic-settings`, `structlog`, `html2text`, `python-dotenv`). **Also add
   `authlib` and `starlette` as new explicit direct dependencies** with the floors from §5
   (`authlib>=1.8.0`, `starlette>=1.6.0`, or whatever's current-latest-clean at merge time — verify
   against OSV.dev before merging, since these move fast). Then run `uv lock --upgrade` to
   regenerate `uv.lock` against the new bounds.
3. **Fix breaks** — resolve whatever `mypy`, `pytest`, `black`, and `isort` (the existing CI gates)
   surface, guided by step 1's findings. Expect at minimum a review of `schema_fix.py` and the
   `_route_map_fn`/`FastMCPOpenAPI` construction in `mcp_server.py`, since those are this server's
   only points of contact with fastmcp's internal APIs.
4. **Validate:**
   - Full CI suite (tests + mypy + black + isort) passing locally.
   - Live smoke test against a sandbox Absolute account: one read-only tool call and one
     bodyless-write tool call (mirroring the reproduction pattern in the 2026-08-25 UAT doc), to
     confirm `AbsoluteAuthClient` still signs and sends correctly at runtime, not just under the
     mocked-transport unit tests.
   - Manual MCP-client round trip (Claude Desktop or Claude Code) confirming tool discovery and a
     real tool call succeed over the actual stdio/http transport.
5. **Re-verify against OSV.dev/`pip-audit`** against the upgraded environment to confirm all **42**
   findings from §1 are cleared — not just the original 8 this spec started from. Note any that
   persist — that would mean the CVE lives in a dependency this bump didn't touch, and needs
   separate handling.
6. **Add `.github/dependabot.yml`** for the Python ecosystem (`pip`/`uv`), weekly cadence,
   targeting `pyproject.toml`, so future version drift arrives as reviewable PRs instead of
   silently accumulating. Because `authlib`/`starlette` become explicit direct dependencies in
   step 2, Dependabot will now track them by name instead of leaving them invisible inside a
   `fastmcp`/`mcp` bump.

## 5. Best practice: explicit floors for security-critical transitive dependencies

**Which transitive packages should become explicit direct dependencies, and why:**

- **`authlib` — yes, add explicitly (`authlib>=1.8.0`).** It isn't in `pyproject.toml` today, but
  it performs the JWS signing that is this repo's entire trust boundary (`auth_client.py`). It
  carries the single worst finding in §1 (CVSS 9.1, signature-verification bypass) and has 10
  distinct advisories at the currently-locked `1.6.0`. Verified that the floor `fastmcp-slim`/`mcp`
  themselves declare (`authlib>=1.6.11`) is **not enough** — `authlib==1.6.11` still carries 2 open
  CVEs (`GHSA-r95x-qfjj-fjj2`, `PYSEC-2026-188`); only `1.8.0`+ is fully clean per OSV.dev. Today,
  clearing this depends entirely on the resolver's "pick latest compatible" default — an explicit
  floor makes that a checked-in guarantee instead of an accident of resolution order, and gives
  Dependabot a named target to track.
- **`starlette` — yes, add explicitly (`starlette>=1.6.0`).** It's the ASGI layer under `mcp`'s
  HTTP transport, 7 distinct advisories at the locked `0.47.1` including a Host-header-poisoning
  CVE. Same gap as `authlib`: the floor `mcp` itself declares (`starlette>=0.27`/`>=0.48.0`
  depending on Python version) is far below fully-patched, and even the `fastmcp-slim` floor
  (`>=1.0.1`) still leaves 8 CVEs open — verified only `1.6.0` clears everything.
- **`cryptography` — optional, no explicit pin needed.** Transitive via `authlib`, 7 advisories at
  the locked `45.0.5`, but `authlib`'s own constraint on it is loose (`>=45.0.1` or unconstrained)
  and nothing else in the graph caps it — the scratch-dir resolution picked the fully-clean
  `50.0.1` with no help. Worth a comment in `pyproject.toml` if `authlib` is added, but not a hard
  requirement.
- **`urllib3`/`requests` — moot.** Both are removed entirely from the dependency graph under
  `fastmcp` 4.x (§3.1), so there's nothing to pin.
- **`idna`/`pygments`** — single low/no-CVSS advisories, already one patch version from clean, no
  conflicting floor anywhere in the graph. Not worth an explicit pin; the existing plan (resolve to
  latest, verify) is sufficient.

Rationale that generalizes beyond this one bump: a transitive package that's genuinely
security-load-bearing for what this service does (signing, transport) shouldn't be invisible in
`pyproject.toml` just because nothing here calls its API directly — an explicit floor is what makes
future CVEs in it show up as a reviewable Dependabot PR against a named package, instead of riding
along silently inside the next `fastmcp`/`mcp` bump (or not surfacing until someone happens to
re-run an audit).

## 6. Testing strategy

The existing suite (`test_auth_client.py`, `test_config.py`, `test_feature_flags.py`,
`test_mcp_server.py`) must keep passing with behavior unchanged; only touch a test's assertions
where the new dependency version forces an actual API signature change. Add new regression
coverage only if step 1's verification uncovers a real behavior change worth locking in — this is
a dependency bump, not a feature, so no speculative new tests. The live smoke test and manual MCP
client test in step 4 are one-time validation gates for this PR, not new permanent automated
tests — there are no sandbox credentials available in CI to run them repeatedly.

## 7. Rollback

Since no code beyond dependency-facing shims should change behavior for callers, rollback is a
straight revert of the PR (`pyproject.toml`, `uv.lock`, and whatever `schema_fix.py`/`mcp_server.py`
changes step 3 required). No data migration or external state is touched by this work.

## 8. Open questions

- ~~Whether `httpx2` actually shipped in `mcp` 2.0.0 stable~~ — **resolved during this spec's
  verification pass (§3):** confirmed via PyPI metadata for both `mcp==2.1.1` and `2.2.0`, and
  `httpx2` coexists alongside this repo's own `httpx.AsyncClient` usage rather than replacing it.
  Still open: whether anything in `mcp_server.py`'s `FastMCPOpenAPI` construction path is affected
  by `httpx2` indirectly — that requires reading real 4.x source per step 1, not just metadata.
- Whether any of the UAT Group B defects are incidentally fixed by the version bump — now more
  likely than the original spec assumed, given §3.1's finding that `fastmcp` 4.x's OpenAPI
  provider dropped `openapi-core`/`requests`/`urllib3` entirely, implying real internal rewrite
  rather than a patch. Still not investigated as part of this ticket; worth a one-line note in the
  PR description if observed in passing during step 4's smoke testing, for whoever picks up the
  UAT follow-up ticket.
- Exact current-latest-clean version floors for `authlib`/`starlette` (§5) should be re-verified
  against OSV.dev immediately before the PR merges, not trusted from this spec's 2026-09-21
  snapshot — both packages are actively receiving new CVE disclosures.
