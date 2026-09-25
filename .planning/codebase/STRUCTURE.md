# Codebase Structure

**Analysis Date:** 2026-09-25

## Directory Layout

```text
ableton-claude/
├── README.md                         # Product architecture, installation, tool catalog, Live limitations
├── CLAUDE.md                         # Operational rules learned from production use
├── mcp_server/
│   ├── pyproject.toml                # Python package, dependencies, CLI entry point
│   ├── uv.lock                       # Reproducible Python dependency lock
│   ├── ableton_claude/
│   │   ├── server.py                 # FastMCP entry point and complete public tool surface
│   │   ├── client.py                 # Local TCP request client for the Live bridge
│   │   ├── arranger.py               # Phrase-library arrangement service
│   │   ├── analysis.py               # Render loudness, peak, spectrum, stereo analysis
│   │   ├── references.py             # Reference fingerprinting and genre aggregation
│   │   ├── knowledge.py              # Curated genre rules plus measured profile loading
│   │   ├── library.py                # Sample-pack indexing and search
│   │   ├── loops.py                  # Offline audio-loop construction
│   │   ├── mixing.py                 # Reference-driven master EQ/limiter moves
│   │   ├── timbre.py                 # Kick/bass/hats/clap element measurements
│   │   ├── tension.py                # Section tension measurements
│   │   ├── validate.py               # Aggregate genre validation
│   │   ├── export.py                 # WAV/MP3 edit and encode utilities
│   │   ├── music/                    # Pure music theory and note/pattern generation
│   │   └── ear/                      # Stem separation, transcription, form, MIDI, groove extraction
│   └── tests/                        # Offline unit and bridge plumbing tests
├── remote_script/
│   └── ClaudeBridge/
│       ├── __init__.py               # Ableton Control Surface and TCP/inbox transport
│       └── handlers.py               # Live Object Model command registry and implementations
├── scripts/                          # Installation, full builds, rendering, profiling, tuning, validation
├── knowledge/
│   ├── genres/                       # Measured genre profile JSON files
│   └── ear/                          # Content-addressed listening reports and heard MIDI caches
└── .planning/codebase/               # GSD codebase reference documents
```

## Directory Purposes

**`mcp_server/ableton_claude/`:**
- Purpose: Own the model-facing MCP adapter, bridge client, and all reusable production/audio domain logic that runs outside Ableton.
- Contains: MCP definitions, TCP client, generators, analyzers, knowledge access, asset search, and arrangement helpers.
- Key files: `mcp_server/ableton_claude/server.py`, `mcp_server/ableton_claude/client.py`, `mcp_server/ableton_claude/arranger.py`.

**`mcp_server/ableton_claude/music/`:**
- Purpose: Generate symbolic musical material without requiring Ableton.
- Contains: Scales/chords/voice leading, chord progression notes, call-and-response melodies, drum grooves/build rolls, and sample key/tempo/swing analysis.
- Key files: `mcp_server/ableton_claude/music/theory.py`, `mcp_server/ableton_claude/music/harmony.py`, `mcp_server/ableton_claude/music/melody.py`, `mcp_server/ableton_claude/music/groove.py`, `mcp_server/ableton_claude/music/samples.py`.

**`mcp_server/ableton_claude/ear/`:**
- Purpose: Translate audio into structured producer-readable evidence and reusable MIDI/groove data.
- Contains: Neural beat detection, Demucs stem separation, drums/bass/harmony transcription, arrangement segmentation, comparison explanations, MIDI encoding, and Ableton groove-file writing.
- Key files: `mcp_server/ableton_claude/ear/listen.py`, `mcp_server/ableton_claude/ear/grid.py`, `mcp_server/ableton_claude/ear/stems.py`, `mcp_server/ableton_claude/ear/why.py`.

**`mcp_server/tests/`:**
- Purpose: Verify pure domain code and exercise the bridge protocol without requiring a running Live instance.
- Contains: One `test_*.py` module per major domain plus fake-ControlSurface plumbing tests.
- Key files: `mcp_server/tests/test_bridge_plumbing.py`, `mcp_server/tests/test_music.py`, `mcp_server/tests/test_ear.py`, `mcp_server/tests/test_references.py`.

**`remote_script/ClaudeBridge/`:**
- Purpose: Provide the only supported boundary into Ableton Live's Python API.
- Contains: A stable transport shell in `remote_script/ClaudeBridge/__init__.py` and hot-reloadable command logic in `remote_script/ClaudeBridge/handlers.py`.
- Key files: `remote_script/ClaudeBridge/__init__.py`, `remote_script/ClaudeBridge/handlers.py`.

**`scripts/`:**
- Purpose: Run operator-driven end-to-end workflows and repository maintenance tasks that are too specific or multi-step for a single low-level MCP tool.
- Contains: Remote-script installation, smoke testing, example track builds, render/analyze loops, profile/principle builders, mix/timbre/tension passes, and export/repair utilities.
- Key files: `scripts/install_remote_script.sh`, `scripts/smoke_live.py`, `scripts/build_deep_house.py`, `scripts/render_and_analyze.py`, `scripts/validate_render.py`.

**`knowledge/`:**
- Purpose: Persist measured domain knowledge and reusable local indexes/caches.
- Contains: Genre profiles under `knowledge/genres/`, content-addressed ear artifacts under `knowledge/ear/`, and sample/reference caches at the directory root.
- Key files: `knowledge/genres/deep_house.profile.json`, `knowledge/samples_index.json`, `knowledge/cache.json`.

**`.planning/codebase/`:**
- Purpose: Store generated GSD maps consumed by later planning and execution workflows.
- Contains: Architecture, structure, stack, integration, convention, test, and concern documents as generated.
- Key files: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`.

## Key File Locations

**Entry Points:**
- `mcp_server/ableton_claude/server.py`: Starts FastMCP and defines every public MCP tool.
- `mcp_server/pyproject.toml`: Maps the `ableton-claude-mcp` console command to `ableton_claude.server:main`.
- `remote_script/ClaudeBridge/__init__.py`: Exposes Ableton's required `create_instance()` and starts the local bridge.
- `scripts/install_remote_script.sh`: Installs the Ableton Remote Script into the User Library.
- `scripts/build_deep_house.py`: Worked full-track construction entry point.
- `scripts/smoke_live.py`: Running-Live integration check.

**Configuration:**
- `mcp_server/pyproject.toml`: Python version, runtime dependencies, optional ear dependencies, build backend, and CLI entry.
- `mcp_server/uv.lock`: Exact dependency resolution.
- `mcp_server/ableton_claude/client.py`: MCP-side bridge host/port and network timeouts.
- `remote_script/ClaudeBridge/__init__.py`: Live-side bridge host/port, reply timeout, and per-tick request limit.
- `mcp_server/ableton_claude/knowledge.py`: Repository-relative genre-profile path and curated conventions.
- `mcp_server/ableton_claude/ear/listen.py`: Repository-relative ear-cache path.
- `mcp_server/ableton_claude/ear/groove_file.py`: Ableton User Library groove output path.

**Core Logic:**
- `remote_script/ClaudeBridge/handlers.py`: Authoritative Live command behavior.
- `mcp_server/ableton_claude/music/`: Symbolic composition logic.
- `mcp_server/ableton_claude/arranger.py`: High-level phrase-based arrangement logic.
- `mcp_server/ableton_claude/analysis.py`: Mix analysis foundation.
- `mcp_server/ableton_claude/references.py`: Reference analysis and aggregation foundation.
- `mcp_server/ableton_claude/ear/listen.py`: Full producer-ear pipeline coordinator.
- `mcp_server/ableton_claude/knowledge.py`: Genre/profile query and section planning.

**Testing:**
- `mcp_server/tests/test_bridge_plumbing.py`: Socket framing, main-thread queueing, errors, batch, deferred commands, and reload.
- `mcp_server/tests/test_music.py`: Theory, melody, and groove generators.
- `mcp_server/tests/test_harmony_arranger.py`: Harmony and arrangement service behavior.
- `mcp_server/tests/test_analysis.py`: Audio metrics.
- `mcp_server/tests/test_ear.py`: Listening/transcription units.
- `scripts/smoke_live.py`: Real Ableton integration flow.

## Naming Conventions

**Files:**
- Use lowercase `snake_case.py` for Python modules, as in `mcp_server/ableton_claude/render.py` if a new reusable module is introduced.
- Use `test_<module>.py` for offline tests under `mcp_server/tests/`, matching `mcp_server/tests/test_mixing.py`.
- Use imperative or subject-oriented `snake_case.py` names for operator scripts under `scripts/`, matching `scripts/build_profile.py` and `scripts/render_and_analyze.py`.
- Keep the Ableton Remote Script package directory name importable by Live; the current package is `remote_script/ClaudeBridge/`.

**Directories:**
- Use lowercase Python package directories under `mcp_server/ableton_claude/`, matching `music/` and `ear/`.
- Keep persistent genre profiles under `knowledge/genres/` and content-addressed ear output under `knowledge/ear/<id>/`, following `mcp_server/ableton_claude/knowledge.py` and `mcp_server/ableton_claude/ear/listen.py`.
- Keep the Python distribution root separate at `mcp_server/`; repository-level scripts import from it explicitly.

## Where to Add New Code

**New MCP Capability:**
- Primary code: Add the typed tool wrapper to `mcp_server/ableton_claude/server.py`.
- Domain logic: Put reusable, model-independent logic in a focused module under `mcp_server/ableton_claude/`; do not embed substantial algorithms in the MCP wrapper.
- Tests: Add or extend `mcp_server/tests/test_<domain>.py`.

**New Ableton Read/Mutation Command:**
- Implementation: Add a decorated handler to `remote_script/ClaudeBridge/handlers.py`; use its `_track`, `_clip`, `_device`, `_param`, and `_t` helpers rather than creating a second addressing scheme.
- MCP exposure: Add a first-class wrapper in `mcp_server/ableton_claude/server.py` for discoverable cross-client use, or document the command in `INSTRUCTIONS` if it remains behind `ableton_command`.
- Bridge tests: Add protocol/dispatch behavior to `mcp_server/tests/test_bridge_plumbing.py`; add running-Live coverage to `scripts/smoke_live.py` when Live API behavior is involved.
- Installation: Keep the network shell in `remote_script/ClaudeBridge/__init__.py` stable; handler edits are hot-reloadable after running `scripts/install_remote_script.sh`.

**New Composition Generator:**
- Primary code: Add a module or function under `mcp_server/ableton_claude/music/`.
- MCP adapter: Add the smallest input/output wrapper to `mcp_server/ableton_claude/server.py`.
- Tests: Place deterministic unit coverage in `mcp_server/tests/test_music.py` or a new focused `mcp_server/tests/test_<feature>.py`.

**New Audio Analysis:**
- General mix metric: `mcp_server/ableton_claude/analysis.py`.
- Reference/profile metric: `mcp_server/ableton_claude/references.py` and aggregation/profile consumers in `mcp_server/ableton_claude/knowledge.py`.
- Instrument-element metric: `mcp_server/ableton_claude/timbre.py` or `mcp_server/ableton_claude/tension.py`.
- Stem/transcription stage: Add the focused implementation under `mcp_server/ableton_claude/ear/` and orchestrate it from `mcp_server/ableton_claude/ear/listen.py`.
- Tests: Mirror the target module in `mcp_server/tests/`.

**New Full Production Workflow:**
- Reusable service: Put orchestration primitives in `mcp_server/ableton_claude/arranger.py` or a new domain module under `mcp_server/ableton_claude/`.
- Operator-specific recipe: Put the entry script under `scripts/`, matching `scripts/build_deep_house.py`.
- Model-agnostic tool: Expose a validated plan/service in `mcp_server/ableton_claude/server.py` instead of requiring every client to reproduce the recipe through generic commands.

**New External Adapter or App UI:**
- Shared service boundary: Reuse domain functions under `mcp_server/ableton_claude/` and Live calls through `mcp_server/ableton_claude/client.py`.
- Adapter location: Create a sibling package to `mcp_server/ableton_claude/server.py` rather than adding UI or HTTP concerns to the FastMCP module.
- Privileged Live boundary: Keep all Live Object Model access in `remote_script/ClaudeBridge/`; do not duplicate it in an app process.

**Utilities:**
- Shared bridge/address utilities: Keep Live-specific helpers in `remote_script/ClaudeBridge/handlers.py`.
- Shared audio utilities: Keep them in the closest analysis/ear module under `mcp_server/ableton_claude/`.
- One-off maintenance: Place executable helpers under `scripts/` rather than the importable package.

## Special Directories

**`remote_script/ClaudeBridge/`:**
- Purpose: Code copied into Ableton's User Library and imported by Live's embedded Python runtime.
- Generated: No.
- Committed: Yes.

**`knowledge/ear/`:**
- Purpose: Cache expensive listening results and generated `heard.mid` by audio content ID.
- Generated: Yes, by `mcp_server/ableton_claude/ear/listen.py`.
- Committed: Repository-dependent; the directory is present with cached result subdirectories, while cache policy is controlled by `.gitignore`.

**`knowledge/genres/`:**
- Purpose: Store measured profiles built from reference folders and consumed by validation/mixing tools.
- Generated: Yes, by profile scripts such as `scripts/build_profile.py`, with optional manual curation through conventions in `mcp_server/ableton_claude/knowledge.py`.
- Committed: Yes for the current `knowledge/genres/deep_house.profile.json`.

**`mcp_server/.venv/`:**
- Purpose: Local uv-managed Python environment.
- Generated: Yes.
- Committed: No.

**`mcp_server/.pytest_cache/` and `scripts/__pycache__/`:**
- Purpose: Test and Python bytecode caches.
- Generated: Yes.
- Committed: No.

**`.planning/codebase/`:**
- Purpose: Generated codebase maps for GSD planning and execution.
- Generated: Yes.
- Committed: Workflow-dependent.

---

*Structure analysis: 2026-09-25*
