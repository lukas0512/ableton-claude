# ableton-claude

Lets Claude drive Ableton Live and measure what comes out of it.

```
Claude Code ──MCP──▶ mcp_server (Python) ──TCP 9878──▶ ClaudeBridge (Remote Script, inside Live)
                         │                                   │
                         └── analysis: LUFS, true peak,      └── Live Object Model: tracks, arrangement
                             bands, stereo, per-section          clips, MIDI, devices, envelopes, cues,
                                                                 transport, master render (Resampling)
```

## Pieces

| Path | What |
|---|---|
| `remote_script/ClaudeBridge/__init__.py` | Control surface: TCP server, runs requests on Live's main thread. Changes need the control surface re-selected (or Live restarted). |
| `remote_script/ClaudeBridge/handlers.py` | All commands. Hot-reloadable with the `reload` command. |
| `mcp_server/ableton_claude/server.py` | MCP tools for Claude. |
| `mcp_server/ableton_claude/analysis.py` | Objective mix measurements and flags. |
| `scripts/install_remote_script.sh` | Copies the Remote Script into the User Library. |

## Setup

1. `scripts/install_remote_script.sh`
2. Restart Live. In **Settings → Link, Tempo & MIDI**, pick **ClaudeBridge** in a free
   Control Surface slot, Input and Output **None**.
3. Register the MCP server:
   ```bash
   claude mcp add --scope user ableton-claude -- uv run --directory ~/dev/ableton-claude/mcp_server ableton-claude-mcp
   ```

## Rendering

Live has no export API. `render_start` records the master into a new audio track through
the **Resampling** input (monitoring off, so no feedback), in real time; `render_wait`
waits, analyzes the WAV and removes the temporary track. The WAV lands in the project's
`Samples/Recorded` folder.

## Tests

```bash
cd mcp_server && uv run pytest -q
```

The bridge tests stub Live's modules and exercise the server, dispatch, batch and reload.
They do not cover Live's API itself — that is verified against a running Live.

## Limits worth knowing

- Arrangement automation of track parameters is not writable through Live's API; use
  clip envelopes (`clip_envelope`), which follow the clip.
- Renders take real time.
- Browser search walks Live's browser on the main thread; the first search of a category
  is slow, later ones are cached.
