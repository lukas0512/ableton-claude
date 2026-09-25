# Architecture

**Analysis Date:** 2026-09-25

## Pattern Overview

**Overall:** Local three-process adapter architecture: an MCP stdio server delegates Ableton mutations to a localhost JSON-RPC-like bridge running inside Live, while pure Python modules perform composition and audio analysis outside Live.

**Key Characteristics:**
- The model-facing boundary is already MCP. `mcp_server/ableton_claude/server.py` creates `FastMCP("ableton-claude")`, registers tools, and calls `mcp.run()`; `mcp_server/pyproject.toml` publishes this as the `ableton-claude-mcp` console command.
- Live is never edited through `.als` files. All reads and mutations cross `mcp_server/ableton_claude/client.py` and the TCP bridge in `remote_script/ClaudeBridge/`; this preserves Live's own clip, warp, device, and arrangement semantics.
- The bridge binds only to `127.0.0.1:9878`. `mcp_server/ableton_claude/client.py` and `remote_script/ClaudeBridge/__init__.py` both hard-code that endpoint, so the current deployment is single-machine and local-user scoped.
- Live API operations execute on Live's main thread. `remote_script/ClaudeBridge/__init__.py` receives requests on socket threads, queues them, and drains at most 64 requests from `update_display()`; `remote_script/ClaudeBridge/handlers.py` owns dispatch and tick-based deferred work.
- Composition logic and audio analysis are ordinary Python functions. Files under `mcp_server/ableton_claude/music/`, `mcp_server/ableton_claude/ear/`, and analysis modules do not need an LLM and can be called from tests, scripts, or another API adapter.
- The public mutation surface is intentionally thin: `ableton_command` and `ableton_batch` in `mcp_server/ableton_claude/server.py` expose a generic command plus free-form argument dictionaries rather than one MCP tool per Live operation.
- Branding is Claude-specific in package, bridge, installation, and documentation names (`ableton_claude`, `ClaudeBridge`, `ableton-claude-mcp`), but the protocol and implementation contain no Anthropic SDK dependency; the runtime dependency is the standard `mcp` package in `mcp_server/pyproject.toml`.

## Layers

**MCP Adapter:**
- Purpose: Advertise tools and workflow instructions to an MCP-capable host, validate top-level tool arguments, and translate tool calls into domain functions or bridge RPC.
- Location: `mcp_server/ableton_claude/server.py`
- Contains: One `FastMCP` instance, server instructions, direct Live tools, rendering tools, music generators, reference/genre analysis, ear analysis, and library tools.
- Depends on: `mcp_server/ableton_claude/client.py`, domain modules in `mcp_server/ableton_claude/`, and `mcp.server.fastmcp.FastMCP` from `mcp_server/pyproject.toml`.
- Used by: Any MCP host that launches `ableton-claude-mcp`; the documented host happens to be Claude Code in `README.md`.

**Bridge Client / Transport Adapter:**
- Purpose: Convert Python calls into newline-delimited JSON requests and map protocol failures to `BridgeError` or `BridgeOffline`.
- Location: `mcp_server/ableton_claude/client.py`
- Contains: Monotonic request IDs, one TCP connection per `call()`, response decoding, a 5-second connect timeout, a default 70-second request timeout, and a 120-second batch timeout.
- Depends on: Python `socket` and `json`; endpoint `127.0.0.1:9878` is defined directly in this file.
- Used by: `mcp_server/ableton_claude/server.py`, `mcp_server/ableton_claude/arranger.py`, `mcp_server/ableton_claude/mixing.py`, and automation scripts under `scripts/`.

**Live Control-Surface Transport:**
- Purpose: Host the TCP listener inside Ableton, isolate socket work from Live's main thread, and return correlated protocol responses.
- Location: `remote_script/ClaudeBridge/__init__.py`
- Contains: `create_instance()`, `ClaudeBridge`, TCP accept/client threads, the inbox queue, request/reply framing, `update_display()`, and teardown.
- Depends on: Ableton's `_Framework.ControlSurface`; it is installed into the User Library by `scripts/install_remote_script.sh`.
- Used by: Ableton Live after the user selects ClaudeBridge as a Control Surface, as documented in `README.md`.

**Live Command Domain:**
- Purpose: Resolve tracks/clips/devices, mutate the Live Object Model, and implement workarounds for Live API limitations.
- Location: `remote_script/ClaudeBridge/handlers.py`
- Contains: The `@command` registry, dispatch, generator-based deferred jobs, address resolution, track/clip/device operations, routing, browser/device loading, transport, locators, groove/warp operations, and master recording.
- Depends on: Ableton's `Live` Python module and the `Context` supplied by `remote_script/ClaudeBridge/__init__.py`.
- Used by: The bridge's `update_display()` / installed `_main_loop()` and indirectly by every bridge call.

**Composition Domain:**
- Purpose: Produce structured musical material that is ready for `create_midi_clip` or arrangement placement.
- Location: `mcp_server/ableton_claude/music/` and `mcp_server/ableton_claude/arranger.py`
- Contains: Theory/voicing in `mcp_server/ableton_claude/music/theory.py`, progressions in `mcp_server/ableton_claude/music/harmony.py`, call-and-response in `mcp_server/ableton_claude/music/melody.py`, drum/groove generation in `mcp_server/ableton_claude/music/groove.py`, sample analysis in `mcp_server/ableton_claude/music/samples.py`, and phrase placement in `mcp_server/ableton_claude/arranger.py`.
- Depends on: Pure Python plus NumPy/SoundFile for sample analysis; `Arranger` alone depends on the bridge client.
- Used by: MCP tools in `mcp_server/ableton_claude/server.py`, tests under `mcp_server/tests/`, and worked build scripts such as `scripts/build_deep_house.py`.

**Audio Intelligence Domain:**
- Purpose: Measure a render or reference, derive genre profiles, separate/transcribe stems, validate a mix, and produce producer-facing comparisons.
- Location: `mcp_server/ableton_claude/analysis.py`, `mcp_server/ableton_claude/references.py`, `mcp_server/ableton_claude/timbre.py`, `mcp_server/ableton_claude/tension.py`, `mcp_server/ableton_claude/validate.py`, and `mcp_server/ableton_claude/ear/`
- Contains: Loudness/spectral analysis, tempo/key/structure fingerprints, element timbre, tension, source separation, beat-grid fitting, drum/bass/chord transcription, arrangement recognition, MIDI emission, and plain-language comparison.
- Depends on: NumPy, SciPy, SoundFile, pyloudnorm, optional Demucs and Beat This dependencies declared in `mcp_server/pyproject.toml`, and `ffmpeg` subprocess fallback in `mcp_server/ableton_claude/references.py`.
- Used by: Analysis MCP tools in `mcp_server/ableton_claude/server.py` and reporting/profile scripts under `scripts/`.

**Knowledge and Asset Domain:**
- Purpose: Supply genre conventions, measured reference profiles, indexed sample packs, generated loops, and cached listening results.
- Location: `mcp_server/ableton_claude/knowledge.py`, `mcp_server/ableton_claude/library.py`, `mcp_server/ableton_claude/loops.py`, and `knowledge/`
- Contains: Genre lookup/planning, sample metadata search, audio construction helpers, profiles in `knowledge/genres/`, sample indexes in `knowledge/samples_index.json`, and ear caches in `knowledge/ear/`.
- Depends on: Repository-relative paths computed in `mcp_server/ableton_claude/knowledge.py` and `mcp_server/ableton_claude/ear/listen.py`.
- Used by: MCP knowledge/library tools and build/report scripts.

**Automation / Workflow Examples:**
- Purpose: Encode full production workflows that sequence many low-level bridge calls outside the MCP request lifecycle.
- Location: `scripts/`
- Contains: Track builders, mix/timbre/tension passes, reference/profile builders, render/analysis helpers, validation, smoke testing, and remote-script installation.
- Depends on: `mcp_server/ableton_claude/client.py` and domain modules; several scripts prepend `mcp_server/` to `sys.path`.
- Used by: A local operator with Live running; `scripts/build_deep_house.py` is the clearest end-to-end production example.

## Data Flow

**Model or User Request to Ableton Mutation:**

1. An MCP host launches `ableton-claude-mcp` using the console entry in `mcp_server/pyproject.toml`; `mcp_server/ableton_claude/server.py` starts FastMCP over its default stdio transport.
2. The host discovers tools and receives the production workflow encoded in `INSTRUCTIONS` in `mcp_server/ableton_claude/server.py`.
3. For direct Live changes, the host calls `ableton_command(cmd, args)` or `ableton_batch(commands)` in `mcp_server/ableton_claude/server.py`.
4. `mcp_server/ableton_claude/client.py` serializes `{"id", "cmd", "args"}` as one JSON line and opens a local TCP connection to `127.0.0.1:9878`.
5. `remote_script/ClaudeBridge/__init__.py` parses the line on a socket thread and puts `(cmd, args, reply_queue)` into `_inbox`.
6. Ableton calls `update_display()` roughly ten times per second; `remote_script/ClaudeBridge/handlers.py` dispatches the command on Live's main thread through its `COMMANDS` registry.
7. The selected handler mutates or reads the Live Object Model. Immediate handlers return directly; generator handlers yield across ticks and remain in `Context.pending` until complete or timed out.
8. The bridge returns `{"id", "ok", "result"}` or `{"id", "ok": false, "error", "trace"}`; `mcp_server/ableton_claude/client.py` returns the result or raises a bridge exception, and FastMCP returns it to the host.

**Generated Music to Arrangement:**

1. The host requests `music_chords`, `music_progression`, `music_call_and_response`, or `music_drum_pattern` from `mcp_server/ableton_claude/server.py`.
2. Modules in `mcp_server/ableton_claude/music/` return notes as `[pitch, start_beat, duration_beats, velocity]`, plus audit/voicing metadata where applicable.
3. The host passes those notes to `ableton_command("create_midi_clip", ...)` or batches multiple placement commands; the current architecture leaves this orchestration to the model or a script.
4. `create_midi_clip()` in `remote_script/ClaudeBridge/handlers.py` creates the arrangement clip natively when possible; when envelopes are needed it creates a Session clip and duplicates it into Arrangement because Live cannot create new automation envelopes directly on arrangement clips.
5. Full-song workflows can instead use `Arranger` in `mcp_server/ableton_claude/arranger.py`; `scripts/build_deep_house.py` shows stashing source phrases, clearing the target range, filling sections, generating new MIDI, adding locators, and applying levels.

**Render, Listen, and Iterate:**

1. `render_start()` in `mcp_server/ableton_claude/server.py` calls `record_master` in `remote_script/ClaudeBridge/handlers.py`.
2. The bridge creates an audio track, selects Resampling input, arms it, moves playback to the requested start, and records in real time; `tick()` advances and finalizes the job.
3. `render_wait()` polls `record_status`, obtains the recorded WAV path, optionally deletes the temporary Live track, and invokes `mcp_server/ableton_claude/analysis.py`.
4. Deeper `listen()` calls flow through `mcp_server/ableton_claude/ear/listen.py`: grid detection, Demucs stems, drum/bass/harmony transcription, arrangement analysis, mix balance, cached JSON, and a generated `heard.mid`.
5. Validation tools in `mcp_server/ableton_claude/server.py` compare results to conventions and profiles in `mcp_server/ableton_claude/knowledge.py` and `knowledge/genres/`; the host then issues further Live commands.

**State Management:**
- Live project state is authoritative and remains inside Ableton; read it with `get_song`, `get_track`, and `get_device` from `remote_script/ClaudeBridge/handlers.py`.
- Bridge runtime state lives in `Context` in `remote_script/ClaudeBridge/handlers.py`: recording job, browser cache, and pending generators survive handler hot reloads.
- Request state is ephemeral because `mcp_server/ableton_claude/client.py` creates a new TCP socket for each call.
- Analysis state is file-backed under `knowledge/`, including profiles, sample indexes, and `knowledge/ear/<content-id>/report.json` as defined by `mcp_server/ableton_claude/ear/listen.py`.
- The MCP server has no session, project, undo, transaction, or authorization state in `mcp_server/ableton_claude/server.py`.

## Key Abstractions

**FastMCP Tool Surface:**
- Purpose: Make bridge operations and music/audio functions discoverable to a model host.
- Examples: `mcp_server/ableton_claude/server.py`, `mcp_server/pyproject.toml`
- Pattern: Decorated synchronous Python functions; long render waits block and poll inside the tool call.

**Command Registry:**
- Purpose: Decouple wire command names from Live handler functions.
- Examples: `COMMANDS`, `@command`, `_run()`, and `dispatch()` in `remote_script/ClaudeBridge/handlers.py`
- Pattern: Decorator registry with consistent `(ctx, **args)` handlers and JSON-serializable results.

**Deferred Live Command:**
- Purpose: Wait for Live to apply changes without blocking its main thread.
- Examples: `_goto()`, locator commands, transport, and `record_master()` in `remote_script/ClaudeBridge/handlers.py`
- Pattern: Generator yields one Live display tick at a time; `tick()` advances pending jobs with a 30-second deadline.

**Address Specification:**
- Purpose: Let callers refer to Live objects without opaque object IDs.
- Examples: `_track()`, `_clip()`, `_device()`, and `_param()` in `remote_script/ClaudeBridge/handlers.py`
- Pattern: Resolve by index, exact name, unique substring, special target, or time-position object. Ambiguity is reported rather than guessed.

**Phrase Library:**
- Purpose: Build arrangements by copying known-good phrases while preserving Live's internal clip data.
- Examples: `Phrase` and `Arranger` in `mcp_server/ableton_claude/arranger.py`
- Pattern: Temporarily stash phrases at bars 601+, fill/place them from left to right, then remove the temporary library zone.

**Measured Genre Profile:**
- Purpose: Replace generic production rules with medians and middle-half ranges measured from reference music.
- Examples: `mcp_server/ableton_claude/knowledge.py`, `mcp_server/ableton_claude/references.py`, `knowledge/genres/deep_house.profile.json`
- Pattern: JSON profile over references, loaded alongside curated conventions and used for structure, timbre, mix, and tension comparisons.

## Entry Points

**MCP Server:**
- Location: `mcp_server/ableton_claude/server.py`
- Triggers: `ableton-claude-mcp` from `mcp_server/pyproject.toml` or `python -m ableton_claude.server`.
- Responsibilities: Start the MCP protocol endpoint, publish tool schemas/instructions, and route calls into bridge/domain code.

**Ableton Remote Script:**
- Location: `remote_script/ClaudeBridge/__init__.py`
- Triggers: Ableton invokes `create_instance(c_instance)` after ClaudeBridge is selected as a Control Surface.
- Responsibilities: Bind localhost TCP, queue requests, execute them on Live's main thread, and manage bridge lifecycle.

**Remote Script Installer:**
- Location: `scripts/install_remote_script.sh`
- Triggers: Manual shell execution.
- Responsibilities: Copy `remote_script/ClaudeBridge/*.py` into the Ableton User Library and clear only the installed bridge's `__pycache__`.

**Production Scripts:**
- Location: `scripts/build_deep_house.py`, `scripts/build_after_midnight.py`, and the remaining `scripts/*.py`
- Triggers: Manual Python execution with Ableton and ClaudeBridge running.
- Responsibilities: Orchestrate deterministic multi-step builds, rendering, measurement, profile generation, and tuning outside the model loop.

## Error Handling

**Strategy:** Preserve errors across process boundaries with explicit protocol status while bounding work on Live's main thread.

**Patterns:**
- Transport failures become `BridgeOffline`; negative bridge replies become `BridgeError` in `mcp_server/ableton_claude/client.py`.
- Handler exceptions are converted to `{error, trace}` by `_err()` in `remote_script/ClaudeBridge/handlers.py`; unknown commands include the available command list.
- Batch items fail independently in `dispatch()` in `remote_script/ClaudeBridge/handlers.py`; a batch-level response can therefore be successful while individual entries contain errors.
- Generator commands cannot run in a batch and are rejected explicitly in `remote_script/ClaudeBridge/handlers.py`.
- Deferred handlers have a 30-second deadline in `remote_script/ClaudeBridge/handlers.py`; socket-side replies have a 60-second timeout in `remote_script/ClaudeBridge/__init__.py`.
- `render_wait()` in `mcp_server/ableton_claude/server.py` returns status instead of raising on an incomplete render and captures temporary-track deletion errors separately.

## Cross-Cutting Concerns

**Logging:** The bridge writes to Ableton's log through `Context.log()` and `ControlSurface.log_message()` in `remote_script/ClaudeBridge/`; scripts use direct console output. The MCP layer in `mcp_server/ableton_claude/server.py` has no structured logging or request correlation beyond the bridge request ID.

**Validation:** FastMCP derives top-level schemas from annotations in `mcp_server/ableton_claude/server.py`; nested `args` for `ableton_command` and items in `ableton_batch` remain free-form and are validated only by Python handler signatures or handler code in `remote_script/ClaudeBridge/handlers.py`.

**Authentication:** Not implemented. The bridge is constrained to localhost in `remote_script/ClaudeBridge/__init__.py`, and MCP access is inherited from the process-launching host. Do not expose port 9878 beyond loopback without adding authentication and authorization.

**Safety:** The server instructions in `mcp_server/ableton_claude/server.py` communicate workflow rules, but destructive tools such as track/clip deletion have no confirmation or policy layer. Live has no save API; `README.md` and `CLAUDE.md` require working on a copy and saving manually.

**Model-Agnostic MCP/App Boundary:**
- Current compatibility: Any host implementing MCP stdio can run `ableton-claude-mcp`; no Claude API appears in `mcp_server/pyproject.toml` or `mcp_server/ableton_claude/server.py`. The quickest generalization is documentation/configuration, not a protocol rewrite.
- Rename boundary: Neutralize `ableton_claude`, `ClaudeBridge`, `ableton-claude-mcp`, and Claude-specific setup text across `mcp_server/pyproject.toml`, `mcp_server/ableton_claude/`, `remote_script/ClaudeBridge/`, `scripts/install_remote_script.sh`, and `README.md` if the product identity must be model-neutral.
- Typed tool boundary: Promote high-value handlers from the generic `ableton_command(cmd, args)` in `mcp_server/ableton_claude/server.py` to first-class typed MCP tools, or generate those wrappers from a shared command schema. This lets clients other than prompt-driven Claude discover required arguments, enums, destructive intent, and result shapes reliably.
- Shared contract boundary: Replace the duplicated prose command list in `mcp_server/ableton_claude/server.py` and Python signatures in `remote_script/ClaudeBridge/handlers.py` with a versioned command contract consumed by both layers; include bridge/version capability discovery based on `ping()`.
- Configuration boundary: Move `HOST`/`PORT` in `mcp_server/ableton_claude/client.py` and `remote_script/ClaudeBridge/__init__.py`, repository-relative knowledge paths in `mcp_server/ableton_claude/knowledge.py`, ear cache paths in `mcp_server/ableton_claude/ear/listen.py`, and groove output in `mcp_server/ableton_claude/ear/groove_file.py` behind explicit configuration.
- Workflow boundary: Package deterministic song creation now demonstrated by `scripts/build_deep_house.py` and `mcp_server/ableton_claude/arranger.py` as reusable domain services/tools. A generic model should submit a validated song plan rather than reproduce hundreds of low-level commands from instructions.
- Long-running boundary: Convert blocking/polling operations such as `render_wait()` and `listen()` in `mcp_server/ableton_claude/server.py` into job-oriented start/status/cancel tools if the target host enforces short tool-call timeouts.
- Security boundary: Add allowlists, path scoping, destructive-operation policy, and optional confirmation tokens around `mcp_server/ableton_claude/server.py` before packaging it as a broadly distributed app. Keep `remote_script/ClaudeBridge/__init__.py` loopback-only unless a separately authenticated transport is introduced.
- Distribution boundary: Bundle Python environment creation, remote-script installation, Ableton Control Surface selection guidance, health checks, and MCP client configuration. Today these are separate manual steps in `README.md` and `scripts/install_remote_script.sh`.
- App/UI boundary: A standalone app can call the same domain modules and `mcp_server/ableton_claude/client.py`; it does not need to replace the Live bridge. Keep `remote_script/ClaudeBridge/` as the privileged Live adapter and add UI/API/MCP adapters above the existing Python service boundary.

---

*Architecture analysis: 2026-09-25*
