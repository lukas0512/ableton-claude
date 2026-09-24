# ableton-claude

Start with README.md (pieces, tools, Live API limits) and the MCP server instructions in
`mcp_server/ableton_claude/server.py` (the step-by-step workflow for making a track).

Rules that cost real time to learn:

- Drive Live only through ClaudeBridge commands. Never write new clips into an `.als`
  file: stale `Time` attributes produced ghost clips Live cannot delete, and a retry loop
  on them froze Live's main thread.
- After editing `remote_script/ClaudeBridge/handlers.py`: run
  `scripts/install_remote_script.sh`, then send `reload`. No Live restart is needed.
  Commands that must wait for Live (playhead moves, locators, renders) are generators.
- Anything that runs on Live's main thread must be bounded: no unbounded retries, no
  O(n^2) loops over thousands of clips.
- Renders are real time. Do not run heavy CPU work (reference analysis) while one runs.
- Judge a mix against a genre profile (`knowledge/genres/*.profile.json`), not against
  rules of thumb. Build profiles with `scripts/build_profile.py <folder> <genre>`.
- The user's projects: work on a copy, never the original. Live has no save API: the
  user saves with Cmd+S.
- A render that fails with "playback never started" usually means Live has no audio
  output device (an interface was unplugged). Check Live's `Log.txt` for
  `Audio In Out: Output Device: No Device` before touching the code; only the user can
  pick a device (Live > Settings > Audio).
- Set a device's parameters only after `load_device` returns (it now waits for the
  device list to settle): values set during the load were reset to the preset defaults.
- Measure elements, not just the master: `timbre_report.py` / `analyze_timbre` found the
  "thin, ticky" first mix came from one added sample (808 maracas, 2 ms at 10 kHz) and a
  sine-like bass, which master EQ could never fix. Choose samples with `find_samples`.
- The drop must be louder than the bars before it and bring the kick back; check
  `drop_jump_lu` against the references, not the section averages.
- Live starts playback at its start marker (`Song.start_time`), not the playhead: a
  click in the arrangement once turned a 97-145 render into 125-145. `_goto` moves both
  and a render refuses playback that starts anywhere else; render_and_analyze checks the
  recorded length.
- A short test render that starts in a breakdown has no kick for the beat grid: take the
  grid from a stretch with kick, or kick/bass and every beat-relative measure swap.
- Swing: compare `swing_self_pct` (off-beats against the hats' own on-beats). The kick
  grid lags ~30 ms on soft kicks and made a 58 % groove read 46 %.
- Rectifier saturation (Roar half/full wave) adds infrasonic thumps that make the
  limiter pump the kick. High-passing a tambourine removes its tap and it drags.
- One check for everything: `scripts/validate_render.py` / `validate_against_genre`.

Tests: `cd mcp_server && uv run pytest -q` (offline) and
`uv run python ../scripts/smoke_live.py --force` (against a running Live).
