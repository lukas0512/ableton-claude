# Lessons learned on real tracks

These were each learned the hard way, on real projects driven through this connector.
They take precedence over general habits. Measure before you believe any of them applies.

## A good start of a track: what the "Fiction" set (127 BPM, tech house) does right

Read from the arrangement of a set the producer judged a good start. Copy the method, not the notes.

- **The story is written down.** Every locator names a section and its job: "INTRO - pulse + voice",
  "BREAK - rhythm stays", "TENSION - repeating cell", "TURNAROUND - controlled handover",
  "OUTRO - DJ". Clip names say why the clip is there ("prepared exit", "theme replies",
  "selected peak sections"). Name sections and clips by intent before you place them.
- **Form (160 bars, about 5 min):** intro 8, groove A 16, hook 8, break 8, groove B 40,
  main break 8, tension 12, drop 12, turnaround 4, final groove 28, DJ outro 16.
  Tension and drop are 12 bars, not 16: shortening a phrase is itself a transition.
- **Contrast comes from the kick and bass leaving, not from the drums disappearing.**
  Clap, hats and perc run the whole track ("percussion stays connected"), only 1.5 dB lower in
  the breaks, 4 dB lower in the intro, 2 dB lower in the last 8 bars. The kick sits out the
  intro (enters bar 9), the first break and the whole main break + tension (20 bars). The bass
  leaves for the main break and comes back with the kick at the drop.
- **The kick prepares its exits.** The kick clip before each break is a "prepared exit" variant
  (it drops out early), so the break is announced, not cut.
- **One bass pocket, kept.** The approved bassline stays the same for the whole track; only a
  "gradual handover" variant at the turnaround. The groove is the identity; don't re-write it
  per section. Chain: Analog mono saw → Saturator (Analog Clip, +3 dB drive, -3 dB out) →
  Compressor 4:1, 0.5 ms attack, 70 ms release, sidechained → Utility → EQ Eight.
- **The hook is disclosed in stages.** Theme clips: "hint" → "variation + space" → "growing
  suspense" → "final anticipation" → full. It plays 8 bars on, then leaves space; never a
  continuous loop.
- **Some elements are reserved for peaks.** A second hat layer ("Lift") plays only in selected
  peak sections. The shaker "enters in chapters" (in and out every 8-16 bars, -3 dB in breaks)
  and stops 2 beats before the drop: a small silence before the impact.
- **The voice is a character, not a loop.** Short 1-2 bar spoken phrases (-1 to -4 dB clip
  gain) at phrase ends, answering the theme; "ready" lands in the 2 bars before the drop.
- **Transitions are small and made from the track's own material.** A reverse of the same
  voice as anticipation, a 2-bar "air" handover after breaks, a small impact at section
  starts (track at -20 dB, clip -2 dB), a build roll of only 2 bars behind the voice. No long
  generic risers.
- **Level hierarchy (fader dB):** kick -6.5; lead -7.5; bass -8; voice -8.8; clap -13;
  hats -17; perc -20; FX -20/-22; stabs -21.5; shaker -22. Foundation and protagonist in
  front, movement behind.
- **References live in the set**, muted at the top and level-matched (-11 dB on a mastered
  reference), for A/B at any moment. **Rejected ideas are archived** (muted "ARCHIVE" track),
  not deleted: reversible.
- Master: one Limiter, True Peak mode, ceiling -1.8 dB. The master isn't where the track is
  made.

## The producer's taste (stated by the producer who trained this connector)

- Crisp drums; groove on the clap/snare and on the hats, not only the hats.
- Transitions that are cared for; variation that keeps the track interesting; surprises without
  clichés; a story like a film: one protagonist, reveal then return, energy in the drop after
  the main break, groove kept in the break.
- Less is more: every element has a purpose. Keep FX under the drums (crashes about -15 dB,
  risers -20, FX loops -14/-16, open hats -18, ghost snare -16). A first pass that put 2-6 kHz
  at 4.5 % of the energy (references 1.6-3.2 %) and filled the 4 bars before the drop killed
  the drop.

## Arrangement and energy

- The drop must be louder than the bars before it and bring the kick back. Check the drop
  jump (`analyze_tension`) against the references, not the section averages. A kick that
  returns in the build steals the drop. Keep risers under the section they announce.
- A short test render that starts in a breakdown has no kick for the beat grid: render from a
  stretch with kick, or every beat-relative measure shifts.

## Sound selection and timbre

- Measure elements, not just the master (`analyze_timbre`). A thin, ticky mix came from one
  sample (an 808 maracas, 2 ms at 10 kHz) and a sine-like bass: no master EQ could fix it.
  Choose samples with `find_samples`.
- Never high-pass a bass or pad above its root: a 34 Hz cut under a C1 bass made the ear and
  the key reading hear G minor (the 3rd harmonic took over).
- A round (sine) bass gets body from biased saturation: symmetric clipping adds only odd
  harmonics. Rectifier saturation (half/full wave) adds infrasonic thumps that make the
  limiter pump the kick.
- High-passing a tambourine removes its tap and it drags.

## Loops, tuning and groove

- A construction kit's loops are balanced at unity. Start from unity, then fit each loop to
  the references' band powers and stem balance (a first mix sat every non-kick layer 4-14 dB
  under the kick, and its breaks fell 9-12 LU).
- Pack loops can be out of tune with their own kit (a vocal ~55 cents sharp of the stab).
  Measure before layering; fix with `set_clip(warping=True, warp_mode="complex_pro",
  detune=cents)`. Auto-warp can overshoot a loop's end (32.8 beats for 16): pin `end_marker`.
  Grooves and detune only act on warped clips.
- A pack loop carries feel and timbre together, a one-shot neither: pick the one-shot by the
  genre's timbre (`find_samples`) and place it with the references' per-16th feel
  (`groove_loop`). The median template is flatter than most references (54.8 % vs 55-76 %):
  pass `swing_pct`. Straight loops beside it pull the swing back down; swing them too.
  (The 55-76 % may come from the profile swing that ignored the beat's phase until
  2026-10-05: re-check against the hats' self-referenced swing before relying on it.)
- One swing, one key. Swing is always the off-beat 16ths against the same hits' on-beats
  (`samples.swing_of`); an excerpt-based measure that ignored the beat's phase read two
  straight (~50 %) references as 60 and 66 %. The key comes from the ear when it heard the
  track: the full-mix third above the bass reads the root's 5th harmonic and turned a
  D minor track major. Many house tracks play the tonic chord both minor and major
  (modal mixture, `tonic_chord` in a study): keep that colour, don't "fix" it.
- Swing: compare the hats against their own on-beats (`swing_self_pct`). The kick grid lags
  ~30 ms on soft kicks and made a 58 % groove read 46 %.

## Mixing in Live through this connector

- Buses: Live's API makes no group tracks. Route tracks into an audio track
  (`set_track_output`) that monitors "in". Set a fresh audio track's input to "No Input" first
  (`set_track_input`), or monitoring "in" feeds the interface's mic into the mix.
- Returns get Live's letter prefix: create "Room", address it as "return:C-Room". A real
  sidechain is `set_device_input` (Compressor, Gate, Auto Filter).
- Set a device's parameters only after `load_device` returns: values set during the load are
  reset to the preset defaults.
- A one-bar slice of a loop: `set_clip(looping=True, loop_start, loop_end)` then
  `trim_clip(end_beat)`; markers alone keep the clip's length.

## The ear (what the analysis can and cannot hear)

- Chords are read from spectral peaks in 110-1500 Hz only. Over a bass pedal, read the upper
  chord without the bass and write a slash chord. Chord roots in a busy breakdown are right
  only about half the time: say so.
- Measurements catch technical problems; they do not judge groove or taste. Say so, and ask
  the producer to listen.

## Safety with the producer's project

- Work on a copy, never the original. Live has no save API: ask the producer to press
  Cmd+S / Ctrl+S before a risky stage.
- Every change through `ableton_command` / `ableton_batch` is journaled: `change_log` shows
  it, `revert_changes` puts the old values back exactly. Deletes and range edits are not
  revertible this way: archive (mute) instead of deleting, or use `live_undo`.
- Live starts playback at its start marker, not the playhead; renders check the recorded
  length. Renders are real time and need an audio output device: "playback never started"
  usually means the interface was unplugged (Live > Settings > Audio).
