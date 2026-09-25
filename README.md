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
| `mcp_server/ableton_claude/analysis.py` | Objective mix measurements and technical flags. |
| `mcp_server/ableton_claude/references.py` | Learns a genre from reference tracks: tempo (0.02 BPM), bass-anchored key, swing, loudness, 1/3-octave shape, and structure (kick on the beats vs bass on the off-beats, per bar). |
| `mcp_server/ableton_claude/knowledge.py` | Curated genre conventions (deep house, tech house, minimal, UK garage, soulful, disco) plus measured profiles; plans section lengths. |
| `mcp_server/ableton_claude/mixing.py` | Turns a profile comparison into a few broad, capped EQ bands and limiter drive, and applies them on the Live master. |
| `knowledge/genres/*.profile.json` | Measured genre profiles (built from your own reference folders). |
| `scripts/build_deep_house.py` | Worked example: rebuilds a project into a 6-minute deep house track with a story. |
| `scripts/render_and_analyze.py` | Renders a bar range and measures it per locator section. |
| `scripts/smoke_live.py` | Integration test against a running Live. |
| `scripts/repair_clip_time.py` | Repairs clips whose `Time` disagrees with `CurrentStart` in an `.als`. |
| `scripts/build_profile.py` | `build_profile.py <folder> <genre>`: builds a genre profile (cached, resumable). |
| `scripts/mix_to_profile.py` | `mix_to_profile.py <render> <genre> [--apply]`: compares a mix with a genre and moves the master toward it. |

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
| `genre_knowledge`, `genre_plan_structure` | What a genre is (conventions + measured numbers); a section plan for N minutes. |
| `analyze_reference`, `compare_to_genre`, `mix_toward_genre` | Measure a reference; hold a mix against a genre; move the Live master toward it. |
| `analyze_timbre`, `find_samples`, `groove_loop` | Kick, bass, hats, clap and breakdown against the genre; rank a folder's one-shots by that timbre; place a one-shot on the references' per-16th feel as a loop. |
| `validate_against_genre`, `analyze_tension` | Every measure at once; break depth, build and drop against the references. |

## The ear

Claude does not hear audio, so the connector translates it. `listen(path)` separates a
track into drums, bass, harmony and vocals (Demucs), puts it on a beat and bar grid
(Beat This), and transcribes it:

- drums on the 16-step grid, per instrument (kick, clap/perc, hats): which steps are
  played, accents, microtiming, swing measured against the hats' own on-beats;
- the bassline as MIDI: register, degrees, the typical bar, how often it lands with the kick;
- chords per beat with Roman numerals, pedal points as slash chords, key, harmonic rhythm;
- what plays in every bar, the sections that follow, and each layer's level and width
  against the drums.

The result is a listening report in words plus the heard MIDI, cached per file.
`scripts/listen_folder.py` hears a folder of references; `scripts/build_principles.py`
pools them into what the genre shares and why it works (`genre_principles`), and
`compare_by_ear` holds a render against them in producer terms. `extract_groove` turns a
reference's feel into a Live groove file (Groove Pool).

The user's sample packs are a resource too: `library_index` indexes them (role, loop or
one-shot, tempo and key from the names), `library_search` finds material in key and tempo,
`library_midi` reads royalty-free pack MIDI transposed to the song's key. A pack loop
carries its producer's feel and timbre together and a one-shot carries neither, so
`find_samples` picks the one-shot by the genre's measured timbre and `groove_loop` places
it with the references' per-16th micro-timing, accents and timing variation (pooled from
their ear reports into the genre's `ear.drums.<role>.template`), giving the genre's sound
with the genre's groove. Pack material can also be out of tune with itself: measure, then
`set_clip(warping=True, warp_mode="complex_pro", detune=cents)`.

Measured on our own tracks, where the truth is known: tempo, bars, form, entries, the
bassline (G1/D2 off the kick) and the hats' swing come out right; the chroma votes with
spectral peaks in 110-1500 Hz only, so a C minor organ and stab read Cm / Cm9 and the
finished mix reads C minor, Cm7 (summing every bin had turned the root's overtones into
"Cmaj9"). Chord roots in a busy breakdown are still right only about half the time.

## Teaching it a genre

```bash
uv run python scripts/build_profile.py "~/Desktop/.../2026 Tracks/Tech House" "tech house"
```

Every track in the folder is measured once (cached by content in `knowledge/cache.json`),
then aggregated into medians and middle-half ranges. The profile is statistics over real
records: it says where a mix or an arrangement is unusual for the genre, not whether it
is good. Where profile and conventions disagree on numbers, the profile wins.

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
