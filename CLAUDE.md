# ableton-claude

Start with README.md (pieces, tools, Live API limits) and the MCP server instructions in
`mcp_server/ableton_claude/server.py` (the step-by-step workflow for making a track).

Lessons for whichever AI drives the connector live in
`mcp_server/ableton_claude/briefs/lessons.md` (served by `producer_brief`): add new production
lessons there, not only here. The method is `briefs/producer.md`. The producer's own feedback,
distilled into rules with the numbers that passed, is `briefs/taste.md` (also served by
`producer_brief`): when he gives new feedback on a track, fold it in there. Run the
`quality_gate` tool before handing any version over: it catches the mistakes that reached him.

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
- Evaluate drop release through pulse/low-end return, transient contrast, timbre and
  expectation as well as loudness. Equal-LUFS drops can work. Use `production_review`
  for all detected drops and `analyze_tension` for the main break; audition in context.
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
- A construction kit's loops were balanced at unity: the first After Midnight mix sat every
  non-kick layer 4-14 dB under the kick and its breaks fell 9-12 LU. Start from unity, then
  fit each loop's band powers to the references' 1/3-octave curve and stem balance.
- Never high-pass a bass or pad above its root: a 34 Hz cut under a C1 bass made the ear
  and the key reading hear G minor (the 3rd harmonic took over).
- Pack loops can be out of tune with their own kit: the After Midnight vocal sat ~55 cents
  sharp of the stab. Measure before layering; fix with `set_clip(warping=True,
  warp_mode="complex_pro", detune=cents)`. Live's auto-warp can overshoot a loop's end
  marker (32.8 beats for a 16-beat loop): pin `end_marker`. Grooves and detune only act on
  warped clips.
- A pack loop carries its feel and timbre together, a one-shot neither: `find_samples`
  picks the one-shot by the genre's timbre and `groove_loop` / `loops.from_template`
  places it with the references' per-16th feel. The median template reads flatter than
  most references (54.8 % vs 55-76 %): pass `swing_pct`. Straight loops next to it pull
  the measured swing back down; swing them too (warp + `apply_groove`). The 55-76 % may
  be from the old profile swing, which ignored the beat's phase (fixed 2026-10-05): one
  swing everywhere now, `samples.swing_of`; studies take the key from the ear.
- The ear's chroma votes with spectral peaks only, 110-1500 Hz: summing every bin let the
  noise floor and the root's 5th/15th harmonics turn a C minor organ into "Cmaj9"; below
  110 Hz the 5.4 Hz bins smear C2 into D and F. Harmonic-series chord templates made it
  worse. Check any harmony change on the kit's organ and stab (Cm, Cm9).
- A kick's low band rises twice (click, then the pitch sweep landing ~60 ms later): the
  validation grid takes the earlier hump, or a 64 ms late first beat merges the intro into
  the groove and shifts every beat-relative measure.
- Buses: Live's API makes no group tracks; route tracks into an audio track
  (`set_track_output`) that monitors "in". A fresh audio track's input is Ext. In (the
  interface's mic): set it to "No Input" first (`set_track_input`) or monitoring "in"
  feeds the room back into the mix. Returns get Live's letter prefix: create "Room" and
  address it as "return:C-Room". A device's sidechain is `set_device_input` (Compressor,
  Gate, Auto Filter).
- A one-bar slice of a loop in the arrangement: `set_clip(looping=True, loop_start,
  loop_end)` then `trim_clip(end_beat)`; markers alone keep the clip's length.
- One check for everything: `scripts/validate_render.py` / `validate_against_genre`.
- The ear's grid: Beat This reports beats on 20 ms frames and adds half-beat detections
  in kickless sections; fit tempo with the phase comb in ear/grid.py, never the median gap.
- Drum hearing is grid-synchronous (every 16th slot checked for an attack) with a
  smoothing window of at least one cycle of the band's lowest tone: a 5 ms window made a
  52 Hz kick ripple into a second kick 120 ms later. Judge claps by the energy they
  sustain after the crack; at the peak a kick's click is as loud.
- Over a bass pedal, read the upper chord without the bass and write a slash chord.
- If files on the Desktop suddenly fail with "Operation not permitted", macOS withdrew
  the Desktop permission (Privacy & Security > Files and Folders); only the user can
  restore it. The Ableton project and renders live on the Desktop.

Tests: `cd mcp_server && uv run pytest -q` (offline) and
`uv run python ../scripts/smoke_live.py --force` (against a running Live).
