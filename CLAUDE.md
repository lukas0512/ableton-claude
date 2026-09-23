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

Tests: `cd mcp_server && uv run pytest -q` (offline) and
`uv run python ../scripts/smoke_live.py --force` (against a running Live).
