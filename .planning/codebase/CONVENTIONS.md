# Coding Conventions

**Analysis Date:** 2026-09-25

## Naming Patterns

**Files:**
- Use lowercase `snake_case.py` for Python modules: `mcp_server/ableton_claude/client.py`, `mcp_server/ableton_claude/music/theory.py`, and `mcp_server/tests/test_bridge_plumbing.py`.
- Name test modules `test_<area>.py` and keep tests under `mcp_server/tests/`; examples are `mcp_server/tests/test_music.py` and `mcp_server/tests/test_analysis.py`.
- Keep runnable maintenance and production workflows as verb-first scripts under `scripts/`, such as `scripts/build_profile.py`, `scripts/render_and_analyze.py`, and `scripts/validate_render.py`.
- The only intentional mixed-case package path is Ableton's Remote Script entry point, `remote_script/ClaudeBridge/`, because Live discovers the control surface by folder/package name.

**Functions:**
- Use `snake_case` for functions and MCP tools: `ableton_status()` in `mcp_server/ableton_claude/server.py`, `toward_profile()` in `mcp_server/ableton_claude/mixing.py`, and `record_master()` in `remote_script/ClaudeBridge/handlers.py`.
- Prefix internal helpers with `_`: `_track()` and `_advance()` in `remote_script/ClaudeBridge/handlers.py`, `_plain()` in `mcp_server/ableton_claude/analysis.py`, and `_key_arg()` in `mcp_server/ableton_claude/server.py`.
- Remote Script command names are the decorated function names. Add a handler as `@command` plus `def command_name(...)` in `remote_script/ClaudeBridge/handlers.py`; the name becomes part of the bridge protocol and the generic `ableton_command` MCP surface in `mcp_server/ableton_claude/server.py`.
- Name tests as behavior statements, not implementation units: `test_render_refuses_playback_that_starts_away_from_the_render_start()` in `mcp_server/tests/test_bridge_plumbing.py` and `test_voice_leading_keeps_chord_tones_and_moves_little()` in `mcp_server/tests/test_music.py`.

**Variables:**
- Use short mathematical names only inside bounded DSP/music calculations (`x`, `y`, `f`, `p`, `sr`) as in `mcp_server/ableton_claude/analysis.py` and `mcp_server/ableton_claude/loops.py`.
- Use descriptive names at protocol and workflow boundaries: `commands`, `reference_path`, `start_bar`, `end_bar`, `delete_track`, and `timeout_s` in `mcp_server/ableton_claude/server.py`.
- Use uppercase module constants for fixed protocol and DSP values: `HOST`, `PORT`, and `REPLY_TIMEOUT` in `remote_script/ClaudeBridge/__init__.py`; `DEFERRED_TIMEOUT_S` and `PARK` in `remote_script/ClaudeBridge/handlers.py`; `SR`, `BANDS`, and `TARGETS` in `mcp_server/ableton_claude/analysis.py` and `mcp_server/ableton_claude/loops.py`.

**Types:**
- Use `PascalCase` for classes and exceptions: `BridgeError` and `BridgeOffline` in `mcp_server/ableton_claude/client.py`, `Phrase` and `Arranger` in `mcp_server/ableton_claude/arranger.py`, and `ClaudeBridge` in `remote_script/ClaudeBridge/__init__.py`.
- Use a `@dataclass` for small Python-side value objects, as with `Phrase` in `mcp_server/ableton_claude/arranger.py`.
- Use modern Python 3.10 annotations on the MCP/public tool surface (`dict | None`, `list[dict]`, explicit return types) in `mcp_server/ableton_claude/server.py`.
- Keep the Live Remote Script layer annotation-free and compatible with Live's embedded runtime style in `remote_script/ClaudeBridge/__init__.py` and `remote_script/ClaudeBridge/handlers.py`; this layer uses classic `%` formatting and `class Context(object)` deliberately.
- Represent MCP and bridge payloads as JSON-serializable dictionaries/lists rather than custom objects. `mcp_server/ableton_claude/analysis.py::_plain()` converts NumPy scalars before returning them through `mcp_server/ableton_claude/server.py`.

## Code Style

**Formatting:**
- No formatter configuration is present in `mcp_server/pyproject.toml`; preserve the existing PEP 8-like four-space indentation, blank-line grouping, and approximately 100-character pragmatic line style used throughout `mcp_server/ableton_claude/` and `mcp_server/tests/`.
- Use module docstrings to state purpose and operational constraints, as in `mcp_server/ableton_claude/mixing.py`, `mcp_server/ableton_claude/arranger.py`, and `remote_script/ClaudeBridge/handlers.py`.
- Prefer trailing commas and one argument/payload field per wrapped line for large calls and dictionaries, as in `mcp_server/ableton_claude/server.py` and `mcp_server/tests/test_harmony_arranger.py`.
- Use inline comments to preserve non-obvious audio or Live API reasoning, not to narrate syntax. Examples include the start-marker explanation in `remote_script/ClaudeBridge/handlers.py::_goto()` and the crest-floor rationale in `mcp_server/ableton_claude/mixing.py::loudness_move()`.

**Linting:**
- No Ruff, Flake8, Black, mypy, pyright, or pre-commit configuration is present; `mcp_server/pyproject.toml` defines runtime dependencies, pytest, Hatch, and uv only.
- Existing scripts use targeted `# noqa: E402` only where path setup must precede imports, as in `scripts/smoke_live.py`; do not introduce blanket lint suppressions.
- Keep code importable on Python `>=3.10`, the requirement declared in `mcp_server/pyproject.toml`, while preserving the separate embedded-Live style in `remote_script/ClaudeBridge/`.

## Import Organization

**Order:**
1. Standard library imports first: `os`, `time`, `json`, `socket`, `threading`, and similar examples appear in `mcp_server/ableton_claude/server.py`, `mcp_server/ableton_claude/client.py`, and `remote_script/ClaudeBridge/__init__.py`.
2. Third-party imports second: `FastMCP` in `mcp_server/ableton_claude/server.py`, NumPy/SciPy/SoundFile in `mcp_server/ableton_claude/analysis.py`, and pytest in `mcp_server/tests/test_music.py`.
3. Relative project imports last: `from . import ...` in `mcp_server/ableton_claude/server.py` and `from .music import ...` in the same file.
4. Keep expensive or optional imports local when the feature does not belong on the default import path. Ear modules are imported inside tools in `mcp_server/ableton_claude/server.py`, and `client`, `knowledge`, and `references` are imported inside `toward_profile()` in `mcp_server/ableton_claude/mixing.py`.

**Path Aliases:**
- No package aliases are configured in `mcp_server/pyproject.toml`; import installed package modules as `ableton_claude...` in tests and use relative imports inside `mcp_server/ableton_claude/`.
- Executable scripts prepend the repository's `mcp_server` directory to `sys.path`, as shown in `scripts/smoke_live.py`; new reusable logic belongs in `mcp_server/ableton_claude/`, not duplicated in scripts.

## Error Handling

**Patterns:**
- Raise `ValueError` for invalid user/protocol inputs and unresolved entities: `_track()`, `_device()`, `_param()`, `trim_clip()`, and `set_warp_markers()` in `remote_script/ClaudeBridge/handlers.py` follow this pattern.
- Raise `RuntimeError` when valid input cannot be completed because of Live state or operation failure: `record_master()`, `_goto()`, and `_finish_record()` paths in `remote_script/ClaudeBridge/handlers.py`, plus `Arranger.stash()`/`clear()` in `mcp_server/ableton_claude/arranger.py`.
- Convert transport failures into `BridgeOffline` and negative bridge replies into `BridgeError` in `mcp_server/ableton_claude/client.py`; preserve the original exception with `raise ... from e` for socket failures.
- Serialize bridge exceptions as an error string plus a bounded traceback using `_err()` in `remote_script/ClaudeBridge/handlers.py`; unknown commands additionally return the available command list from `dispatch()`.
- Use bounded waiting for asynchronous Live operations. Generator commands in `remote_script/ClaudeBridge/handlers.py` carry `DEFERRED_TIMEOUT_S`, `_goto()` has tick bounds, device loading checks at most 20 ticks, clip deletion has at most four passes, and `_trim_at()` has at most 64 passes.
- Limit broad `except Exception` blocks to protocol boundaries, best-effort cleanup, or known Live handle invalidation. Examples are connection cleanup in `remote_script/ClaudeBridge/__init__.py`, stale clip deletion in `remote_script/ClaudeBridge/handlers.py::delete_clips_in_range()`, and smoke-test cleanup in `scripts/smoke_live.py`.
- Return structured partial outcomes where continued operation is intentional. `dispatch()` in `remote_script/ClaudeBridge/handlers.py` makes batch items independently `ok`/`error`; `render_wait()` in `mcp_server/ableton_claude/server.py` returns `delete_error` without discarding the analysis result.
- Treat `ableton_batch()` as non-transactional. `mcp_server/ableton_claude/server.py` documents that one command failure does not stop the rest, and `remote_script/ClaudeBridge/handlers.py::dispatch()` implements that contract.

## Logging

**Framework:** `ControlSurface.log_message` inside Live, structured MCP/bridge return values, and `print()` in operator scripts; no standard Python logging configuration is present in `mcp_server/pyproject.toml`.

**Patterns:**
- Log bridge lifecycle and unrecoverable background-loop failures through `ClaudeBridge.log_message()` in `remote_script/ClaudeBridge/__init__.py` and `Context.log()` in `remote_script/ClaudeBridge/handlers.py`.
- Return command errors to the caller rather than only logging them. The request/response boundary in `remote_script/ClaudeBridge/__init__.py` and dispatch boundary in `remote_script/ClaudeBridge/handlers.py` preserve actionable errors for any MCP client.
- Use flushed `print()` output for long-running scripts that operators watch, as in `scripts/render_and_analyze.py`, `scripts/build_timbre.py`, and `scripts/tuning_pass.py`.
- Keep library modules free of unsolicited console output. Functions in `mcp_server/ableton_claude/analysis.py`, `mcp_server/ableton_claude/music/`, and `mcp_server/ableton_claude/loops.py` return data; optional progress is injected as callbacks such as `echo` in `mcp_server/ableton_claude/validate.py`.

## Comments

**When to Comment:**
- Explain Live API behavior, musical rationale, numerical units, and safety bounds. High-value examples are `_via_session()` and `_trim_at()` in `remote_script/ClaudeBridge/handlers.py`, `eq_plan()` in `mcp_server/ableton_claude/mixing.py`, and the beat-grid fixtures in `mcp_server/tests/test_export.py`.
- Preserve the reason for limits and retries next to the bound. `delete_clips_in_range()` and render `tick()` in `remote_script/ClaudeBridge/handlers.py` explain the freeze-prevention and playback-start guards.
- Record operational invariants centrally in `CLAUDE.md`, including work-on-a-copy, no direct `.als` writes, bounded main-thread work, and real-time render constraints.

**JSDoc/TSDoc:**
- Not applicable; the codebase is Python. Use Python docstrings on modules, public tools, bridge commands, and non-obvious helpers in `mcp_server/ableton_claude/` and `remote_script/ClaudeBridge/handlers.py`.
- MCP tool docstrings are product-facing schema guidance. Keep argument semantics, units, accepted values, and side effects explicit in `mcp_server/ableton_claude/server.py` because arbitrary MCP-capable models consume them.

## Function Design

**Size:**
- Keep pure music and DSP functions focused and composable, following `eq_plan()` in `mcp_server/ableton_claude/mixing.py`, `four_on_floor()` in `mcp_server/ableton_claude/loops.py`, and theory helpers in `mcp_server/ableton_claude/music/theory.py`.
- Keep MCP tools as thin adapters over domain modules or `client.call()`, as in `music_chords()`, `analyze_audio()`, and `ableton_status()` in `mcp_server/ableton_claude/server.py`.
- Keep Live API mechanics inside command handlers in `remote_script/ClaudeBridge/handlers.py`; do not move Live object access into model-facing tools or pure music modules.
- For operations that must wait on Live, implement a generator handler that yields between bounded checks, following `load_device()`, `_goto()`, and locator commands in `remote_script/ClaudeBridge/handlers.py`.

**Parameters:**
- Use explicit keyword-oriented protocol parameters with units in names (`start_bar`, `end_bar`, `timeout_s`, `ceiling_db`) in `mcp_server/ableton_claude/server.py` and `remote_script/ClaudeBridge/handlers.py`.
- Accept model-friendly JSON shapes at external boundaries: note lists, command dictionaries, and section dictionaries in `mcp_server/ableton_claude/server.py`.
- Inject side-effect dependencies for testability, as with `call=None` in `mcp_server/ableton_claude/mixing.py::toward_profile()` and `mcp_server/ableton_claude/arranger.py::Arranger`.
- Avoid new mutable default arguments. `music_call_and_response()` in `mcp_server/ableton_claude/server.py` currently has list defaults for ranges; new code should use tuples or `None` and construct values inside the function.

**Return Values:**
- Return dictionaries with measured/confirmed state after mutations, as in `set_track()`, `set_param()`, `create_midi_clip()`, and `record_status()` in `remote_script/ClaudeBridge/handlers.py`.
- Return deterministic note lists and plans from pure generation functions in `mcp_server/ableton_claude/music/`, enabling direct property assertions in `mcp_server/tests/test_music.py` and `mcp_server/tests/test_harmony_arranger.py`.
- Ensure MCP results contain Python primitives. Use `_plain()` in `mcp_server/ableton_claude/analysis.py` for NumPy-derived results.

## Module Design

**Exports:**
- `mcp_server/ableton_claude/server.py` is the MCP composition root: register tools there, delegate domain work to sibling modules, and keep `main()` limited to `mcp.run()`.
- `remote_script/ClaudeBridge/handlers.py` is the Live command registry: `@command` populates `COMMANDS`, and `dispatch()` is the only command execution gateway.
- `mcp_server/ableton_claude/client.py` owns the loopback TCP protocol; callers use `call()`/`batch()` and handle `BridgeError` subclasses.
- `scripts/` contains orchestration examples and operator workflows; do not import large scripts as libraries when the reusable logic can live under `mcp_server/ableton_claude/`.

**Barrel Files:**
- No barrel exports are used. `mcp_server/ableton_claude/__init__.py` and `mcp_server/ableton_claude/music/__init__.py` are empty; import the concrete module explicitly.
- The Remote Script package entry point `remote_script/ClaudeBridge/__init__.py` is not a barrel: Live calls `create_instance()`, and command logic remains in `remote_script/ClaudeBridge/handlers.py`.

## Mutation Safety Conventions

- Work on a copy of the user's Live Set and never edit `.als` XML directly; this invariant is documented in `CLAUDE.md`. Live has no save API, so persistence remains a user action in Live.
- Resolve tracks/devices/parameters through exact names first and reject ambiguous fragments via `_track()`, `_device()`, and `_param()` in `remote_script/ClaudeBridge/handlers.py`.
- Keep all Live API access on Live's main thread. The TCP thread queues work in `remote_script/ClaudeBridge/__init__.py`, while `update_display()`/`_main_loop()` dispatch it in `remote_script/ClaudeBridge/handlers.py`.
- Bound every retry or potentially expensive main-thread loop as required by `CLAUDE.md` and implemented in `remote_script/ClaudeBridge/handlers.py`.
- Read back the changed state in mutation replies whenever the Live API exposes it, following `set_track()`, `set_param()`, `track_routing()`, and `record_status()` in `remote_script/ClaudeBridge/handlers.py`.
- Do not assume batch rollback. Callers of `ableton_batch()` in `mcp_server/ableton_claude/server.py` must inspect every item result and perform explicit cleanup or compensating operations.
- Treat `delete_track`, `delete_clip`, `delete_clips_in_range`, `delete_device`, `clear_cues`, routing changes, and `api_probe` as privileged operations even though the current bridge exposes them through `ableton_command`; their implementations are in `remote_script/ClaudeBridge/handlers.py` and current code has no confirmation, dry-run, undo, or capability policy.
- Keep `api_probe()` in `remote_script/ClaudeBridge/handlers.py` out of a hardened model-agnostic surface until it is replaced by an allowlisted introspection API. Its `eval()` can invoke methods despite the docstring calling the expression read-only.

---

*Convention analysis: 2026-09-25*
