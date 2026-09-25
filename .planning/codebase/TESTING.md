# Testing Patterns

**Analysis Date:** 2026-09-25

## Test Framework

**Runner:**
- pytest `>=8`, declared in the `dev` dependency group in `mcp_server/pyproject.toml`.
- Config: no dedicated pytest configuration is present; collection follows pytest defaults from `mcp_server/tests/test_*.py`.
- Current offline result: `102 passed in 5.23s` from `cd mcp_server && uv run pytest -q` on 2026-09-25. The 102 collected cases come from 91 test functions plus parametrization in `mcp_server/tests/test_music.py`.

**Assertion Library:**
- Plain Python `assert` plus `pytest.approx`, `pytest.raises`, parametrization, fixtures, `monkeypatch`, and `tmp_path`, as used in `mcp_server/tests/test_music.py`, `mcp_server/tests/test_bridge_plumbing.py`, `mcp_server/tests/test_knowledge.py`, and `mcp_server/tests/test_analysis.py`.
- NumPy and generated WAV fixtures provide numerical ground truth in `mcp_server/tests/test_analysis.py`, `mcp_server/tests/test_music.py`, `mcp_server/tests/test_loops.py`, `mcp_server/tests/test_references.py`, and `mcp_server/tests/test_timbre.py`.

**Run Commands:**
```bash
cd mcp_server && uv run pytest -q
cd mcp_server && uv run pytest -q tests/test_music.py
cd mcp_server && uv run pytest -q tests/test_bridge_plumbing.py
cd mcp_server && uv run python ../scripts/smoke_live.py
cd mcp_server && uv run python ../scripts/smoke_live.py --force
```
- The first four commands are documented in `CLAUDE.md` and `README.md`; `--force` in `scripts/smoke_live.py` permits mutation of a non-empty Set and therefore must only be used on an explicit disposable copy.
- Watch mode: not configured in `mcp_server/pyproject.toml`.
- Coverage command: not configured because pytest-cov/coverage is not declared in `mcp_server/pyproject.toml`.

## Test File Organization

**Location:**
- Keep offline tests in the separate `mcp_server/tests/` tree, grouped by production area rather than co-located with modules.
- Keep the real-Live integration smoke workflow in `scripts/smoke_live.py`; it requires a running Ableton Live instance with `remote_script/ClaudeBridge/` installed.
- No CI workflow is present alongside `mcp_server/pyproject.toml`; offline and Live smoke verification are currently operator-run.

**Naming:**
- Name files `test_<module-or-capability>.py`: `mcp_server/tests/test_analysis.py`, `mcp_server/tests/test_music.py`, and `mcp_server/tests/test_bridge_plumbing.py`.
- Name cases `test_<expected_behavior>()`: `test_mp3_true_peak_is_held_below_the_target()` in `mcp_server/tests/test_export.py` and `test_batch_refuses_waiting_commands()` in `mcp_server/tests/test_bridge_plumbing.py`.

**Structure:**
```text
mcp_server/
├── ableton_claude/               # production MCP, DSP, music, and client modules
└── tests/
    ├── test_bridge_plumbing.py   # loopback socket/dispatch with stub Live modules
    ├── test_music.py             # theory, generation, sample analysis
    ├── test_analysis.py          # synthetic-audio measurement tests
    ├── test_ear.py               # grid/drums/bass/harmony/MIDI/library tests
    └── test_*.py                 # feature-focused offline tests
scripts/
└── smoke_live.py                 # destructive-but-cleaned-up real Live integration smoke
```

## Test Structure

**Suite Organization:**
```python
# Pattern from mcp_server/tests/test_music.py
@pytest.mark.parametrize("seed", range(12))
def test_call_and_response_obeys_its_rules(seed):
    out = melody.call_and_response("G", "minor_hexatonic", CHORDS, seed=seed)
    scale = theory.Scale("G", "minor_hexatonic")
    assert not melody.audit(out["call"], scale, CHORDS[:2])
    assert not melody.audit(out["response"], scale, CHORDS[2:])
```

**Patterns:**
- Assert musical invariants instead of exact full generated payloads: pitch-class membership, register bounds, voice-leading movement, reproducibility, rhythmic echo, and phrase boundaries in `mcp_server/tests/test_music.py` and `mcp_server/tests/test_harmony_arranger.py`.
- Use deterministic seeds for generated music and timing humanization in `mcp_server/tests/test_music.py` and `mcp_server/tests/test_loops.py`.
- Generate small synthetic audio signals with known frequencies, clicks, levels, phase, and section boundaries in `mcp_server/tests/test_analysis.py`, `mcp_server/tests/test_music.py`, `mcp_server/tests/test_references.py`, and `mcp_server/tests/test_timbre.py`.
- Use tolerances for DSP output (`pytest.approx` or explicit absolute bounds) rather than bit equality in `mcp_server/tests/test_analysis.py`, `mcp_server/tests/test_ear.py`, and `mcp_server/tests/test_timbre.py`.
- Exercise expected failures with `pytest.raises(ValueError)` in `mcp_server/tests/test_music.py`, `mcp_server/tests/test_harmony_arranger.py`, and `mcp_server/tests/test_knowledge.py`.
- Include the actual result as the assertion message when diagnosing a complex measurement, as in `mcp_server/tests/test_export.py`, `mcp_server/tests/test_timbre.py`, and `scripts/smoke_live.py`.

## Mocking

**Framework:** pytest fixtures/`monkeypatch`, simple fakes, and temporary module injection; no standalone mocking library is declared in `mcp_server/pyproject.toml`.

**Patterns:**
```python
# Pattern from mcp_server/tests/test_harmony_arranger.py
class FakeLive:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, args=None):
        self.calls.append((cmd, args))
        if cmd == "duplicate_range":
            return {"copied": 3}
        return {}
```
```python
# Pattern from mcp_server/tests/test_bridge_plumbing.py
monkeypatch.setitem(sys.modules, "_Framework", fw)
monkeypatch.setitem(sys.modules, "_Framework.ControlSurface", cs)
monkeypatch.setitem(sys.modules, "Live", types.ModuleType("Live"))
```

**What to Mock:**
- Mock the injected `call` dependency when testing orchestration in `mcp_server/ableton_claude/arranger.py` and `mcp_server/ableton_claude/mixing.py`; assert emitted bridge commands and safety bounds.
- Stub `_Framework`, `Live`, and the ControlSurface only for socket/dispatch behavior in `mcp_server/tests/test_bridge_plumbing.py`.
- Monkeypatch data directories for profile and cache tests, following `mcp_server/tests/test_knowledge.py`, so tests never alter `knowledge/genres/` or ignored runtime caches under `knowledge/`.
- Use `tmp_path` for generated audio, MIDI, JSON, and MP3 artifacts in `mcp_server/tests/test_analysis.py`, `mcp_server/tests/test_ear.py`, `mcp_server/tests/test_export.py`, and `mcp_server/tests/test_knowledge.py`.

**What NOT to Mock:**
- Do not mock NumPy/SciPy/SoundFile/pyloudnorm calculations when testing acoustic claims; synthesize known signals and call the real implementation as done in `mcp_server/tests/test_analysis.py` and `mcp_server/tests/test_timbre.py`.
- Do not claim Live Object Model compatibility from the stub bridge fixture. The module docstring in `mcp_server/tests/test_bridge_plumbing.py` explicitly limits it to request routing, main-thread dispatch, error propagation, batching, and reload.
- Do not mock the real-Live smoke path in `scripts/smoke_live.py`; its purpose is to catch API behavior unavailable outside Ableton.

## Fixtures and Factories

**Test Data:**
```python
# Pattern from mcp_server/tests/test_analysis.py and test_music.py
t = np.arange(int(seconds * sample_rate)) / sample_rate
x = amplitude * np.sin(2 * np.pi * frequency * t)
sf.write(tmp_path / "tone.wav", x.astype(np.float32), sample_rate)
```
```python
# Pattern from mcp_server/tests/test_bridge_plumbing.py
@pytest.fixture()
def bridge(monkeypatch):
    # install stub Live/_Framework modules, bind a free loopback port,
    # run update_display on a background thread, then disconnect after yield
    ...
```

**Location:**
- Helpers are local to the test module that needs them: `_tone()` and `_clicks()` in `mcp_server/tests/test_music.py`, `_bar_clicks()` in `mcp_server/tests/test_export.py`, and the `bridge` fixture in `mcp_server/tests/test_bridge_plumbing.py`.
- No shared `conftest.py` or fixture package exists under `mcp_server/tests/`; introduce one only when multiple modules need the same fake Live object model or audio builders.
- The one repository profile fixture is `knowledge/genres/deep_house.profile.json`; tests that modify profile lookup instead use `tmp_path` and monkeypatching in `mcp_server/tests/test_knowledge.py`.

## Coverage

**Requirements:** None enforced. `mcp_server/pyproject.toml` declares pytest but no coverage tool or threshold, and no CI configuration is present.

**View Coverage:**
```bash
# Not currently available from declared dependencies in mcp_server/pyproject.toml.
# Add pytest-cov to the dev group before standardizing this command:
cd mcp_server && uv run pytest --cov=ableton_claude --cov-report=term-missing
```

**Observed coverage shape:**
- Strong behavioral coverage exists for pure music generation in `mcp_server/tests/test_music.py` and `mcp_server/tests/test_harmony_arranger.py`.
- Strong synthetic-signal coverage exists for measurement, export, reference, timbre, tension, loop, and ear algorithms in `mcp_server/tests/test_analysis.py`, `mcp_server/tests/test_export.py`, `mcp_server/tests/test_references.py`, `mcp_server/tests/test_timbre.py`, `mcp_server/tests/test_tension.py`, `mcp_server/tests/test_loops.py`, and `mcp_server/tests/test_ear.py`.
- Partial protocol coverage exists for TCP framing, main-thread dispatch, generator commands, batch independence, reload, parameter-display conversion, warp shaping, and one render-start guard in `mcp_server/tests/test_bridge_plumbing.py`.
- No offline tests exercise the FastMCP tool registry, generated tool schemas, stdio transport, or end-to-end tool calls in `mcp_server/ableton_claude/server.py`.
- No offline tests model most mutation handlers in `remote_script/ClaudeBridge/handlers.py`: track/clip/device deletion, range fill/trim, routing, cues, groove mutation, device loading, record cleanup, and warp-marker replacement rely primarily on `scripts/smoke_live.py` or manual use.
- `mix_toward_genre(apply=True)` in `mcp_server/ableton_claude/mixing.py` has plan-level unit coverage in `mcp_server/tests/test_mixing.py`, but no test covers the full mutation sequence, partial batch errors, missing `Pro-L 2`, or rollback/compensation behavior.

## Test Types

**Unit Tests:**
- Test pure theory, generation, DSP, profile, library, arrangement planning, and serialization in `mcp_server/tests/` with deterministic inputs and no Live dependency.
- Treat the musical generation claims as constrained algorithm tests, not subjective quality tests. `mcp_server/tests/test_music.py` proves scale adherence, voice-leading bounds, groove placement, call/response rules, reproducibility, key estimation, tempo estimation, and swing estimation.
- Treat measurement claims as calibrated synthetic-fixture tests. `mcp_server/tests/test_analysis.py`, `mcp_server/tests/test_references.py`, and `mcp_server/tests/test_timbre.py` assert known loudness, peak, band, phase, grid, structure, and timbre properties.

**Integration Tests:**
- `mcp_server/tests/test_bridge_plumbing.py` is an offline protocol integration test across a real loopback socket, queued main-thread dispatch, stub ControlSurface, and real `remote_script/ClaudeBridge/handlers.py` import.
- `scripts/smoke_live.py` is the real Ableton integration test. It creates MIDI/audio tracks and clips, loads devices, writes envelopes, fills/trims/deletes ranges, renders two bars, analyzes the WAV, then deletes created tracks/cue and restores tempo.
- The current smoke test assumes a specific Desktop sample glob in `scripts/smoke_live.py`; a missing file makes `create_audio_clip` fail, so it is not portable or CI-ready.
- The current smoke cleanup addresses tracks and the cue by fixed names in `scripts/smoke_live.py`; name collisions and interrupted runs can leave state behind, so run it only on a disposable Set copy as required by `CLAUDE.md`.

**E2E Tests:**
- No automated model-to-MCP-to-bridge-to-Live end-to-end test exists. `mcp_server/ableton_claude/server.py` is not launched by the pytest suite, and `scripts/smoke_live.py` calls `mcp_server/ableton_claude/client.py` directly rather than invoking MCP tools.
- No cross-client conformance test proves model agnosticism. `mcp_server/ableton_claude/server.py` uses standard FastMCP tools, but `README.md` setup is Claude CLI-specific and the tool descriptions/brand strings still refer to Claude.

## Common Patterns

**Async Testing:**
```python
# Pattern from mcp_server/tests/test_bridge_plumbing.py
def main_thread():
    while not stop.is_set():
        bridge.update_display()
        time.sleep(0.01)

threading.Thread(target=main_thread, daemon=True).start()
response = _rpc(port, "ping")
assert response["ok"]
```
- The production bridge uses synchronous sockets plus queued generator jobs rather than `asyncio`; test tick-based completion with a bounded background loop in `mcp_server/tests/test_bridge_plumbing.py`.
- Real-time render polling is bounded by deadlines in `scripts/smoke_live.py` and `mcp_server/ableton_claude/server.py::render_wait()`; new tests must use short simulated clocks or fake calls rather than sleeping for real render durations.

**Error Testing:**
```python
# Pattern from mcp_server/tests/test_bridge_plumbing.py
response = _rpc(port, "set_tempo", {})
assert not response["ok"]
assert "TypeError" in response["error"]
```
```python
# Pattern from mcp_server/tests/test_music.py
with pytest.raises(ValueError):
    theory.parse_chord("Gxyz")
```
- Test errors at both layers: domain functions should raise a precise exception; bridge requests should return `{ok: false, error, trace}` as implemented in `remote_script/ClaudeBridge/handlers.py`.
- For partial batches, assert every item result because `remote_script/ClaudeBridge/handlers.py::dispatch()` intentionally continues after a failure.

## Music-Generation Verification

**What is verified:**
- Harmonic correctness and bounded voice leading are verified with pitch-class and movement assertions in `mcp_server/tests/test_music.py` and `mcp_server/tests/test_harmony_arranger.py`.
- Rhythmic generation is verified for four-on-the-floor kicks, swing offsets, accelerating rolls, silence before the drop, deterministic humanization, and measured groove templates in `mcp_server/tests/test_music.py` and `mcp_server/tests/test_loops.py`.
- Melody generation is verified over 12 seeds for scale membership, register, open/closed phrase endings, rhythmic echo, phrase containment, and reproducibility in `mcp_server/tests/test_music.py`.
- Arrangement primitives are verified at the command-plan level with `FakeLive` in `mcp_server/tests/test_harmony_arranger.py` and at the real-Live smoke level in `scripts/smoke_live.py`.
- Audio analysis that judges the generated result is verified against synthetic truth in `mcp_server/tests/test_analysis.py`, `mcp_server/tests/test_references.py`, `mcp_server/tests/test_timbre.py`, and `mcp_server/tests/test_tension.py`.

**What is not verified:**
- No test asks an MCP client/model to plan and produce a complete song through `mcp_server/ableton_claude/server.py`, then validates the actual Live Set and render.
- No golden-set test measures whether generated tracks are musically compelling or whether genre reports correlate with human listeners. `mcp_server/ableton_claude/analysis.py` explicitly limits its claims to technical measurements, and `mcp_server/ableton_claude/server.py` instructs the model to ask the user to listen.
- No regression fixture validates the documented full workflow in `mcp_server/ableton_claude/server.py::INSTRUCTIONS` from genre planning through composition, render, comparison, correction, and re-render.
- Chord recognition limitations are acknowledged in `README.md`, but no acceptance threshold dataset is versioned under `mcp_server/tests/` for busy commercial-style mixes.

## Mutation-Safety Verification

**Existing safeguards under test:**
- `mcp_server/tests/test_bridge_plumbing.py` verifies that generator commands yield across ticks, waiting commands are refused inside a batch, handler exceptions propagate, and render recording is aborted when playback starts away from the requested beat.
- `scripts/smoke_live.py` checks clip-envelope refusal for Arrangement clips, read-back of volume, fill/trim/delete counts, render completion, analysis, cleanup, and tempo restoration against a running Live instance.
- Bounded deletion/retry, main-thread dispatch, render start validation, and input-monitoring guidance live in `remote_script/ClaudeBridge/handlers.py` and `CLAUDE.md`; only a subset is automatically tested.

**Required tests before exposing this as a general model-agnostic MCP product:**
- Add a fake Live Object Model suite under `mcp_server/tests/` for every mutating handler in `remote_script/ClaudeBridge/handlers.py`, including exact targets, ranges, preconditions, read-back, retry bounds, and cleanup on each failure point.
- Add contract tests for destructive command classification around `ableton_command()`/`ableton_batch()` in `mcp_server/ableton_claude/server.py`: `delete_*`, `clear_cues`, routing, recording, overwrite-like duplication/trim, master-chain edits, and `api_probe` must be distinguishable from reads.
- Add tests proving that a failed multi-step mutation cannot silently report success. Prioritize `mcp_server/ableton_claude/mixing.py::toward_profile()`, `mcp_server/ableton_claude/arranger.py::drop_library()`, `remote_script/ClaudeBridge/handlers.py::_trim_at()`, and `scripts/smoke_live.py` cleanup.
- Add collision tests for duplicate track/device/cue names and ambiguous fragments in `_track()`, `_device()`, `_param()`, `_pick()`, and smoke cleanup in `remote_script/ClaudeBridge/handlers.py` and `scripts/smoke_live.py`.
- Add interruption tests for `record_master()`/`record_abort()` in `remote_script/ClaudeBridge/handlers.py`: restore arm states, metronome, loop, record mode, transport, and temporary render track across missing resampling, playback failure, timeout, disconnect, and user stop.
- Add property/fuzz tests for malformed MCP JSON payloads, extreme beats/bars, negative/zero lengths, NaN/Infinity, huge note arrays, huge batches, path errors, and invalid indices at `mcp_server/ableton_claude/server.py`, `mcp_server/ableton_claude/client.py`, and `remote_script/ClaudeBridge/handlers.py`.
- Add a security regression test that rejects method calls and side effects through `api_probe()` in `remote_script/ClaudeBridge/handlers.py`; the current `eval()` implementation does not enforce the docstring's read-only claim.
- Add real-Live tests on a generated temporary WAV rather than the user-specific Desktop glob in `scripts/smoke_live.py`, and tag them by supported Live/OS versions.
- Add post-test Set-diff assertions in `scripts/smoke_live.py`: tempo, tracks, clips, cues, devices, routing, arm/monitor states, transport markers, loop, metronome, and record mode must match the pre-test snapshot except for explicitly retained output files.

## Model-Agnostic MCP Verification

- Add FastMCP in-process tests for tool listing and JSON schema generation from `mcp_server/ableton_claude/server.py`; ensure defaults, union/null types, nested command shapes, and tool descriptions serialize under the supported `mcp` range in `mcp_server/pyproject.toml`.
- Add stdio protocol tests that launch the `ableton-claude-mcp` entry point declared in `mcp_server/pyproject.toml`, perform MCP initialization, list tools, call read-only tools with an offline bridge, and verify standard MCP error responses.
- Add the same conformance flow through at least two independent MCP clients; do not use Claude-specific prompt behavior as the assertion. The generic contract is the schema and response data in `mcp_server/ableton_claude/server.py`.
- Add snapshot tests for all tool names/descriptions/schemas in `mcp_server/ableton_claude/server.py` so a change cannot silently break other models or clients.
- Add capability-policy tests that expose read-only analysis/music tools without a running Live instance and gate Live mutations separately. The current `mcp_server/ableton_claude/server.py` registers both categories on one unrestricted server.
- Add portability tests for Linux/Windows/macOS path handling in analysis and library tools under `mcp_server/ableton_claude/`; current instructions and smoke fixtures in `CLAUDE.md`, `README.md`, and `scripts/smoke_live.py` assume macOS and Desktop paths.
- Add timeout/cancellation/concurrency tests for multiple MCP clients calling `mcp_server/ableton_claude/client.py` and the single Live main-thread queue in `remote_script/ClaudeBridge/__init__.py`; include overlapping render requests and queued commands during a deferred command.
- Add compatibility tests across the lower/upper supported MCP versions from `mcp_server/pyproject.toml` and supported Ableton Live versions; `mcp_server/tests/test_bridge_plumbing.py` currently hard-codes only a fake Live `12.4.2` version response.

## Operational Readiness Gate

- Require the offline `uv run pytest -q` suite from `mcp_server/pyproject.toml` on every change through CI.
- Require `scripts/smoke_live.py` on a disposable Live Set for changes to `remote_script/ClaudeBridge/handlers.py`, `remote_script/ClaudeBridge/__init__.py`, `mcp_server/ableton_claude/client.py`, or mutating tools in `mcp_server/ableton_claude/server.py`.
- Require a render-and-validate scenario using `scripts/render_and_analyze.py` and `scripts/validate_render.py` for changes to music generation, arrangement, mixing, reference analysis, timbre, tension, or ear modules under `mcp_server/ableton_claude/`.
- Require an MCP conformance suite before advertising compatibility with arbitrary models. The executable is already a standard FastMCP entry point in `mcp_server/pyproject.toml`, but its transport/schema path has no automated tests.
- Keep subjective quality as a human acceptance step. The boundary is explicit in `mcp_server/ableton_claude/analysis.py` and the workflow instructions in `mcp_server/ableton_claude/server.py`.

---

*Testing analysis: 2026-09-25*
