# Codebase Concerns

## Executive assessment

The repository is a capable local Ableton Live automation system and an existing MCP
server, but it is not yet safe or polished enough to distribute as a general-purpose
"Ableton MCP". The main blockers are an arbitrary-code-execution escape hatch in the
Live process, a broad untyped mutation surface, and incomplete end-to-end automation
coverage outside the developer's own Live environment.

## Critical security risk

- `remote_script/ClaudeBridge/handlers.py` exposes `api_probe(ctx, expr)` through the
  same unauthenticated TCP command dispatcher as every other bridge operation.
- `api_probe` calls Python `eval()` with a globals dictionary that does not explicitly
  remove `__builtins__`. Python therefore makes builtins available, so the claimed
  "read-only expression" restriction is not enforced. A caller can potentially import
  modules, access the filesystem, or execute code inside Ableton Live's Python process.
- `remote_script/ClaudeBridge/__init__.py` binds only to `127.0.0.1`, which limits remote
  exposure, but any local process can connect to port 9878 without authentication.
- Before distribution, remove `api_probe` from release builds or replace it with a
  strict attribute-walking inspector that rejects calls, dunder names, assignments,
  indexing into unsafe objects, and all builtins. Add a release-mode command allowlist.

## Mutation safety

- `mcp_server/ableton_claude/server.py` exposes most Live mutations through the generic
  `ableton_command(cmd, args)` and `ableton_batch(commands)` tools. The nested command
  arguments have no MCP-level JSON schemas, so validation and discoverability depend on
  a long instruction string and on the model following it correctly.
- Destructive commands such as `delete_track`, `delete_clip`, `delete_clips_in_range`,
  `delete_device`, and `clear_cues` have no confirmation token, dry-run mode, scope
  guard, snapshot, or transaction boundary.
- The project documentation correctly says to work on a copy, but the software does not
  enforce that policy. There is also no bridge command for save or recovery.
- Add typed, task-level tools for common operations and keep raw bridge access behind an
  explicit expert/developer mode. Consider plan/apply, expected-state checks, and a
  user-visible change summary for destructive operations.

## Reliability and concurrency

- `mcp_server/ableton_claude/client.py` uses a process-local monotonically increasing
  request ID, one TCP connection per call, fixed host/port constants, and no retry or
  idempotency key. A timeout can leave the caller unsure whether Live applied a change.
- `remote_script/ClaudeBridge/__init__.py` accepts multiple client threads while all Live
  mutations are serialized through one inbox. There is no session ownership, project
  lock, or protection against two MCP hosts editing the same Set concurrently.
- `ableton_batch` does not roll back prior items when a later item fails. Its docstring
  states this, but callers still need an explicit partial-success handling strategy.
- Long renders and model-backed audio analysis are synchronous workflows. The render
  path has polling, but the analysis tools do not expose general job IDs, cancellation,
  or progress reporting.

## Portability and packaging

- The runtime is model-agnostic at the protocol layer: `mcp_server/ableton_claude/server.py`
  uses `mcp.server.fastmcp.FastMCP` and `mcp.run()` (stdio by default). Branding and setup
  documentation remain Claude-specific in `README.md`, `CLAUDE.md`, package names, the
  bridge name, render names, and example scripts.
- There is no `LICENSE`, release metadata, CI workflow, supported Live/Python/macOS
  matrix, installer/uninstaller, or version compatibility handshake beyond `ping`.
- `scripts/install_remote_script.sh` is macOS-oriented and should be audited and tested
  for Windows before claiming general Ableton Live support.
- The optional "ear" stack is large (Demucs, PyTorch, Beat This). It is included in the
  default uv dependency groups, contributing substantially to the repository environment
  size and making a lightweight installation harder.

## Test and validation gaps

- The offline suite is substantial and currently passes, but most bridge tests mock the
  Live API or test transport plumbing. `scripts/smoke_live.py` is the only broad live-set
  integration workflow and requires a running, configured Ableton instance.
- There are no protocol-level tests that launch the MCP server over stdio, perform the
  MCP initialize/list-tools/call-tool sequence, and assert serialized error behavior.
- There are no tests for multiple simultaneous clients, timeout ambiguity, interrupted
  render recovery, malformed or oversized JSON requests, or local unauthorized access.
- The example composition scripts prove significant capability but contain project- and
  sample-specific track names, preset paths, bars, and `/tmp/claude-501` output paths.
  They are demonstrations, not reusable end-user flows.

## Product boundary

- The code can generate symbolic musical material (chords, voiced progressions, motifs,
  drum patterns, build rolls) and can place/edit/render it in Live. It is not a trained
  music-generation model and does not autonomously create raw audio from a text prompt.
- Musical intent and high-level arrangement decisions are currently supplied by the MCP
  client model through the extensive server instructions. Results therefore depend on
  the host model's tool-use quality unless more orchestration is moved into typed,
  deterministic server-side tools such as `compose_section` or `build_song_plan`.

## Recommended order of work

1. Remove or harden `api_probe`; add release-mode command policy and request limits.
2. Add typed MCP tools for core read/write operations and gate raw commands.
3. Add plan/apply safety, expected-state checks, session locking, and clearer recovery.
4. Add stdio MCP conformance tests and a repeatable Live integration test matrix.
5. Rename product-facing surfaces and publish client-neutral setup examples.
6. Split lightweight control dependencies from optional audio-analysis dependencies.
7. Only then add a GUI/app wrapper or streamable HTTP deployment with authentication.
