# ableton-claude

Lets Claude compose in, arrange, drive and measure Ableton Live.

```
Claude Code ──MCP──▶ mcp_server (Python) ──TCP 9878──▶ ClaudeBridge (Remote Script, inside Live)
                     │                                  │
                     ├─ music: theory, voice leading,   └─ Live Object Model: tracks, arrangement
                     │  call & response, grooves,          clips, MIDI, presets, devices, clip
                     │  sample understanding               envelopes, locators, transport,
                     ├─ arranger: songs from phrases       master render (Resampling)
                     └─ analysis: LUFS, true peak, bands, stereo, per section
```

## Pieces

| Path | What |
|---|---|
| `remote_script/ClaudeBridge/__init__.py` | Control surface: TCP server and inbox. Almost never changes. |
| `remote_script/ClaudeBridge/handlers.py` | Every command and the main loop. Hot-reloaded by `reload` (it re-installs the main loop on the running control surface, so no Live restart). |
| `mcp_server/ableton_claude/server.py` | MCP tools. |
| `mcp_server/ableton_claude/music/` | `theory` (scales, chords, roman numerals, voice leading), `harmony` (progressions with anticipation, swing), `melody` (call and response), `groove` (swung patterns, build rolls), `samples` (key, tempo, swing, role, bass notes). |
| `mcp_server/ableton_claude/arranger.py` | Builds an arrangement from a library of phrases stashed past the song. |
| `mcp_server/ableton_claude/analysis.py` | Objective mix measurements and flags. |
| `scripts/build_deep_house.py` | Worked example: rebuilds a project into a 6-minute deep house track with a story. |
| `scripts/render_and_analyze.py` | Renders a bar range and measures it per locator section. |
| `scripts/smoke_live.py` | Integration test against a running Live. |
| `scripts/repair_clip_time.py` | Repairs clips whose `Time` disagrees with `CurrentStart` in an `.als`. |

## Setup

1. `scripts/install_remote_script.sh`
2. Start Live. In **Settings → Link, Tempo & MIDI**, pick **ClaudeBridge** in a free
   Control Surface slot, Input and Output **None**.
3. `claude mcp add --scope user ableton-claude -- uv run --directory ~/dev/ableton-claude/mcp_server ableton-claude-mcp`

After editing `handlers.py`: `scripts/install_remote_script.sh`, then the `reload` command.

## MCP tools

| Tool | Does |
|---|---|
| `ableton_status`, `ableton_command`, `ableton_batch`, `ableton_reload_bridge` | Read and drive Live (the command list is in the server instructions). |
| `render_start`, `render_wait`, `analyze_audio`, `compare_to_reference` | Record the master and measure it. |
| `music_chords` | Roman numerals → chord symbols in a key. |
| `music_progression` | Voice-led chord part (held common tones, anticipation). |
| `music_call_and_response` | Call that asks, response that answers, audited against the rules. |
| `music_drum_pattern`, `music_build_roll` | Swung deep house kit, build-up roll. |
| `analyze_sample`, `analyze_bassline` | Key, BPM, swing, role; bass notes per beat. |

## Things Live's API does not do, and the workarounds

| Limit | Workaround |
|---|---|
| No export / render | Record the master into a track through the **Resampling** input, in real time. |
| Arrangement clips cannot get new automation envelopes | Build the clip in Session with its envelopes, then `duplicate_clip_to_arrangement`. |
| No API for an arrangement clip's length (`end_marker` moves content only) | A clip dropped on another truncates it: drop a copy at the cut, delete the copy. |
| No track-level arrangement automation | Clip envelopes on the clips themselves. |
| Playhead moves apply a tick later, and `continue_playing` ignores them | Commands that move the playhead are generators that wait for Live; playback uses `start_playing`. |
| Frozen tracks play their old freeze file | Do not move clips on frozen tracks; unfreeze in Live first. |
| No save | Save in Live (`Cmd+S`). |

## Tests

```bash
cd mcp_server && uv run pytest -q                      # offline: music, analysis, bridge plumbing
uv run python ../scripts/smoke_live.py [--force]       # against a running Live
```
