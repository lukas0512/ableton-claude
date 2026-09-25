# External Integrations

**Analysis Date:** 2026-09-25

## APIs & External Services

**Ableton Live:**
- Ableton Live Object Model - the system reads and drives a running Live set through the Remote Script in `remote_script/ClaudeBridge/`.
  - SDK/Client: proprietary `Live` and `_Framework.ControlSurface` modules supplied inside Ableton, imported by `remote_script/ClaudeBridge/handlers.py` and `remote_script/ClaudeBridge/__init__.py`.
  - Auth: none; the bridge binds only to loopback at `127.0.0.1:9878`.
  - Capabilities: 50 bridge commands cover song/track inspection, MIDI/audio arrangement clips, notes, devices/presets/parameters, automation envelopes, routing/sidechain, locators, transport, Groove Pool, warping, and real-time master recording in `remote_script/ClaudeBridge/handlers.py`.
  - Runtime requirement: Live must be open and `ClaudeBridge` must be selected as a Control Surface, per `README.md` and the error handling in `mcp_server/ableton_claude/client.py`.

**Model Context Protocol:**
- Standard MCP server - exposes 33 tools from `mcp_server/ableton_claude/server.py` for Ableton control, deterministic music generation, audio/reference analysis, genre planning, sample search, and ear reports.
  - SDK/Client: `mcp.server.fastmcp.FastMCP`, dependency declared in `mcp_server/pyproject.toml`.
  - Transport: stdio through `mcp.run()` in `mcp_server/ableton_claude/server.py`; the example registration command is in `README.md`.
  - Auth: inherited from the local MCP host/process; this repository adds no authentication or authorization layer.
  - Model compatibility: any host/model capable of using standard MCP tools can use the server. No Claude/Anthropic SDK or API call exists; Claude branding is limited to names and MCP instructions.

**Local Bridge Protocol:**
- ClaudeBridge newline-delimited JSON RPC-like protocol - one JSON request and response per line between the MCP process and Live.
  - Client: `mcp_server/ableton_claude/client.py` opens a fresh TCP connection per call and sends `{id, cmd, args}`.
  - Server: `remote_script/ClaudeBridge/__init__.py` listens on `127.0.0.1:9878`, queues work, and executes it on Live's main UI/audio thread via `update_display`.
  - Concurrency: the socket accepts concurrent connections, but work is serialized/bounded on Live's main thread; batch commands run in one tick, and deferred generator commands yield across ticks in `remote_script/ClaudeBridge/handlers.py`.
  - Timeouts: client connect timeout is 5 seconds, normal command timeout is 70 seconds, batch timeout is 120 seconds in `mcp_server/ableton_claude/client.py`; bridge replies time out after 60 seconds in `remote_script/ClaudeBridge/__init__.py`.

**Audio Toolchain:**
- FFmpeg - decodes formats that libsndfile cannot read and performs MP3 delivery encode/decode.
  - SDK/Client: external `ffmpeg` process invoked with `subprocess.run` in `mcp_server/ableton_claude/references.py` and `mcp_server/ableton_claude/export.py`.
  - Auth: not applicable.
  - Packaging gap: FFmpeg is not declared or installed by `mcp_server/pyproject.toml`; it must already be on `PATH`.
- libsndfile through SoundFile - local WAV/AIFF/FLAC/OGG read/write in `mcp_server/ableton_claude/analysis.py`, `mcp_server/ableton_claude/references.py`, `mcp_server/ableton_claude/library.py`, and `mcp_server/ableton_claude/loops.py`.

**Machine-Learning Model Distribution:**
- Beat This - beat/downbeat inference is initialized as `Audio2Beats(checkpoint_path="final0")` in `mcp_server/ableton_claude/ear/grid.py`.
  - SDK/Client: GitHub-source `beat-this` package plus PyTorch; `mcp_server/pyproject.toml` points at `https://github.com/CPJKU/beat_this/archive/main.zip`.
  - Network behavior: Beat This resolves named checkpoint `final0` through its model loader when it is not already cached, so initial ear analysis can perform a model-weight download.
- Demucs - `get_model("htdemucs")` in `mcp_server/ableton_claude/ear/stems.py` supplies drums/bass/other/vocals stems.
  - SDK/Client: `demucs` plus PyTorch, declared in the optional/default `ear` dependency group of `mcp_server/pyproject.toml`.
  - Network behavior: initial model construction can require downloading pretrained weights into the framework cache.

## Data Storage

**Databases:**
- Not detected. There is no SQL/NoSQL service or ORM.

**File Storage:**
- Repository-local JSON genre profiles: `knowledge/genres/*.profile.json`, loaded through `mcp_server/ableton_claude/knowledge.py` and written by reference/profile scripts such as `scripts/build_profile.py`.
- Repository-local analysis caches: `knowledge/cache.json`, `knowledge/samples_cache.json`, and `knowledge/samples_index.json`; indexing/writes are implemented in `mcp_server/ableton_claude/library.py` and reference/timbre modules.
- Per-audio ear cache: `knowledge/ear/<content-id>/report.json` and `heard.mid`, written by `mcp_server/ableton_claude/ear/listen.py`.
- Generated audio loops: caller-selected output paths written by `mcp_server/ableton_claude/loops.py` and the `groove_loop` MCP tool in `mcp_server/ableton_claude/server.py`.
- Generated groove files: `~/Music/Ableton/User Library/Grooves/Claude/*.agr`, written by `mcp_server/ableton_claude/ear/groove_file.py` using a hard-coded Ableton 12 Suite core template.
- Live recordings: `record_master` in `remote_script/ClaudeBridge/handlers.py` creates a Resampling track and reports the arrangement clip's `file_path`; Ableton chooses the recording location.
- User samples/references: tools accept absolute/local filesystem paths and scan user-selected directories in `mcp_server/ableton_claude/library.py`, `mcp_server/ableton_claude/references.py`, and `mcp_server/ableton_claude/server.py`.

**Caching:**
- Local JSON/filesystem caching only. Reference analysis is keyed by file content in `mcp_server/ableton_claude/references.py`; ear reports use file IDs in `mcp_server/ableton_claude/ear/listen.py`; sample measurements/indexing use JSON files through `mcp_server/ableton_claude/library.py` and `mcp_server/ableton_claude/timbre.py`.
- PyTorch model weights use upstream framework caches outside the repository.

## Authentication & Identity

**Auth Provider:**
- None.
  - Implementation: MCP is launched as a local child process, and the Ableton bridge is reachable only on loopback (`127.0.0.1`) in `mcp_server/ableton_claude/client.py` and `remote_script/ClaudeBridge/__init__.py`.
  - There are no user accounts, tokens, API keys, OAuth flows, or multi-tenant boundaries.
  - The local security boundary is process/user access. Any local process that can reach port 9878 can issue mutating bridge commands while Live is running.

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, hosted telemetry, or analytics integration is present.

**Logs:**
- Remote Script lifecycle, socket, client, and tick failures are written to Ableton's log via `ControlSurface.log_message` in `remote_script/ClaudeBridge/__init__.py` and `remote_script/ClaudeBridge/handlers.py`.
- Bridge errors return an error string and truncated traceback in the JSON response; `mcp_server/ableton_claude/client.py` raises `BridgeError` or `BridgeOffline`.
- Analysis scripts print progress/results to stdout; no structured centralized logging framework is configured.
- Render failures may require inspecting Ableton's `Log.txt`, as described in `README.md` and `CLAUDE.md`.

## CI/CD & Deployment

**Hosting:**
- Local-only desktop process plus an Ableton Remote Script. No cloud hosting target is defined.
- The MCP package exposes `ableton-claude-mcp = "ableton_claude.server:main"` in `mcp_server/pyproject.toml` and is normally launched by an MCP host with `uv run --directory ...` as shown in `README.md`.
- The Live side is installed by copying `remote_script/ClaudeBridge/*.py` into the user library using `scripts/install_remote_script.sh`.

**CI Pipeline:**
- None detected. No `.github/workflows/`, Dockerfile, or release automation is present.
- Local verification uses `uv run pytest -q` under `mcp_server/` and `uv run python ../scripts/smoke_live.py [--force]` against Live, documented in `README.md`.

## Environment Configuration

**Required env vars:**
- None for normal MCP execution.
- `ABLETON_USER_LIBRARY` is optional for `scripts/install_remote_script.sh`; without it the script uses `$HOME/Music/Ableton/User Library`.

**Secrets location:**
- Not applicable. No `.env` files were detected, and the code does not reference secret or vendor API-key variables.

**Hard-coded local configuration:**
- Bridge endpoint `127.0.0.1:9878`: `mcp_server/ableton_claude/client.py`, `remote_script/ClaudeBridge/__init__.py`.
- Ableton 12 Suite stock groove template and user groove directory: `mcp_server/ableton_claude/ear/groove_file.py`.
- Genre/cache storage below `knowledge/`: `mcp_server/ableton_claude/knowledge.py`, `mcp_server/ableton_claude/library.py`, and `mcp_server/ableton_claude/ear/listen.py`.

## Webhooks & Callbacks

**Incoming:**
- No HTTP webhooks.
- Incoming local TCP command requests arrive at `127.0.0.1:9878` in `remote_script/ClaudeBridge/__init__.py`.
- Incoming MCP messages arrive over stdin through `mcp.run()` in `mcp_server/ableton_claude/server.py`.

**Outgoing:**
- No application webhooks or third-party API calls.
- Socket responses return bridge command results to `mcp_server/ableton_claude/client.py`.
- Initial ML model use may make upstream weight-download requests through Beat This/PyTorch and Demucs caches.

## Ableton Control Flow

1. An MCP-capable model host launches the console command defined in `mcp_server/pyproject.toml` and discovers the tools registered in `mcp_server/ableton_claude/server.py`.
2. High-level music tools generate JSON-ready notes/patterns locally, while control tools call `mcp_server/ableton_claude/client.py`.
3. The client sends newline-delimited JSON to `127.0.0.1:9878`; `remote_script/ClaudeBridge/__init__.py` queues it for Live's main thread.
4. `remote_script/ClaudeBridge/handlers.py` uses the Live Object Model to alter the open set and returns JSON-serializable state/results.
5. The model can render by real-time Resampling, analyze the resulting local file, compare it with profiles/references, and issue another round of arrangement/mix commands.

## Model-Agnostic MCP Feasibility

**Current status:**
- The repository is already an MCP server at the protocol level. A Claude Code registration example appears in `README.md`, but the server itself does not authenticate to or import Claude/Anthropic.
- A different MCP host can use the same command from `mcp_server/pyproject.toml` as long as it supports local stdio servers, can pass local file paths, and runs on the same machine as Ableton Live.

**Required for a broadly reusable app:**
- Rename Claude-specific package, bridge, track, and user-library labels in `mcp_server/pyproject.toml`, `mcp_server/ableton_claude/server.py`, `remote_script/ClaudeBridge/`, and `scripts/install_remote_script.sh`; this is branding cleanup, not protocol work.
- Make bridge host/port and Ableton installation/user-library paths configurable instead of constants in `mcp_server/ableton_claude/client.py`, `remote_script/ClaudeBridge/__init__.py`, and `mcp_server/ableton_claude/ear/groove_file.py`.
- Provide client-specific MCP registration examples or an installer. The current single example in `README.md` targets Claude Code even though the server transport is standard.
- Keep the default deployment local. Exposing MCP or port 9878 remotely would require authentication, authorization, TLS, input/path policy, and command restrictions that are absent now.
- Split optional heavy ear dependencies from the default installation if fast/lightweight adoption matters; `mcp_server/pyproject.toml` currently enables both `dev` and `ear` groups by default.

**Compatibility limits:**
- Models without an MCP-capable host cannot call this server directly; they need an adapter translating their tool/function-call system to MCP.
- Remote/cloud model hosts cannot directly reach local `127.0.0.1`, Ableton's embedded API, or user audio paths. They need a trusted local MCP client/agent process.
- The generic MCP layer does not make the DAW adapter generic: replacing Ableton requires implementing the command contract against another DAW.

---

*Integration audit: 2026-09-25*
