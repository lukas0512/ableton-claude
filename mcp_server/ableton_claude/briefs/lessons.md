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

## Drums the producer loves: "Let The Rhythm" (127 BPM, 2026-10-18)

The producer called these drums "very good, lots of movement, strong timbres". The whole kit
is in the app: `music_drum_kit("let_the_rhythm")` gives every part's role, why, step pattern,
micro-timing, sample, chain, level, sends and where it plays (`notes=True` for the exact
loops). Start a new track's drums from it; what makes it work:

- **Layers with jobs, not copies.** 16th closed hat as a quiet motor (-10.7 dB, velocities
  78-106, no fixed accent); three off-beat layers on the "&": a shaker one-shot ~5 ms early
  (pushes), a hat on the grid (body), a third one held back for lifts (out of groove B1 and
  the breaks). Under them a played shaker loop and a played percussion loop (warped, -12 and
  -16.5 dB) add human timing MIDI does not have.
- **The backbeat grooves.** Clap and snare layered on one syncopated 2-bar pattern: 2 and 4,
  beat 4 held, a 16th pickup before 4, the "& of 1" in bar 2, a 32nd velocity ramp before
  every 8th bar. Measured on the master the clap lands ~20 ms behind the grid (laid back).
- **Latin movement in the mids, never in the bass's register.** Congas/bongos (Percussion Core
  Kit) on syncopated 16ths with a triplet bar every 4; a 909 low tom on the "e"/"a" 16ths;
  later a 909 rim/ghost groove. Low 808 toms in the same rhythm as the bass were rejected.
- **One feel.** Every MIDI part except the kick on "Swing 16ths 54" at 115 %, velocity 30 %,
  random 2 %. Measured: off-beat 16ths 11 ms late, on-beat 16ths ~11 dB under the off-beat
  8ths. Groove files: User Library/Grooves/Claude/Let The Rhythm hats|clap.agr.
- **One room, glued.** Almost every drum sends -21 to -22.5 dB to one DRUMVERB; the DRUMS group
  has a Glue (2:1, 10 ms, range 4 dB) and a -2.5 dB shelf at 9 kHz; kick, bass and sub share a
  LOW END bus. Percussion panned as a kit (-0.35 to +0.35), kick/clap/snare centred.
- **Reserved elements.** The ride only in hook, drop, final groove and groove C, low (-13.4 dB,
  HP 350 Hz); a 909 crash only on section downbeats; no snare rolls anywhere.

## Arrangement and energy

- Audition arrangement work with continuous playback after the focused transition
  checks. A test loop can hide the later development: a set with changes at bars
  65/73/105/113 still repeats the same chapter if transport remains looped at 49–81.
  Name the chapter clips and leave the final playback moving through the form.
- A drop releases the expectation established by its build. Inspect loudness, low-end
  and pulse return, transient contrast and spectral space independently: equal-LUFS
  drops can work. `production_review` reports every detected drop and its local context;
  `analyze_tension` covers the main break. A kick returning early can reduce one source
  of contrast, but is not automatically wrong. Audition the whole transition.
- Bass amount, harmonic openness, density, gates and stereo width are independent.
  A closed bass can be heavy; an open bass can sit quietly. Measure separated bass
  against drums and compare like sections. Filter/envelope changes are sound design;
  MIDI durations do not specify synth release. Check low-band mono loss before raising
  gain on a bass that disappears in mono.
- Natural development retains an anchor and changes phrase endings, rests, accents or
  timbre with purpose. Independent timing/pitch randomness is not a model of feeling.
  Explicit emotional words guide hypotheses; neither a minor key nor a feature score
  proves how the listener feels. Audition and listener feedback decide.
- A short test render that starts in a breakdown has no kick for the beat grid: render from a
  stretch with kick, or every beat-relative measure shifts.
- A sustained pad added to a break at -6 dB made the break (-9.5 LUFS) louder than the
  drop (-10.1): the producer heard it at once ("muito alto"). Measure every break against
  its drop before calling it done. In the producer's tech house references only the kick
  leaves every break; bass stays in 75 %, harmony in 90 %, and the last 4-8 bars strip to
  harmony + voice. For a percussive record, tension came from tribal toms (3-against-4
  accents, crescendo), a short marimba riff in the clap's gaps and clip-envelope
  automation (HPF + verb on the roll, delay throws), not from a pad.
- Check sections at 4-bar resolution, not only the whole break: a strip that removes bass,
  clap and hats dipped 3 LU before the drop where the references dip ~0.15 LU and keep
  the highs rising. Keep the hats/shaker into the drop and stop them one beat early.

## Parts that converse

- A new hook must leave the existing one its rhythmic space. An organ with 9 hits per
  2 bars (3 of them a 16th from the stab's 3 hits) "covered almost everything" and the
  producer lost the stab's characteristic groove. Lay the step grids side by side first;
  give the newcomer the gaps (here 3 hits on steps 10, 13 and 29) and a register above.
- Print who plays in each 4-bar block before rendering (clips per track, muted excluded):
  "busy" usually means three melodic voices plus the vocal in the same block.
- The ear reads an organ voiced A-C#-E-G# without the F# as "Amaj7": rootless voicings
  are heard as their own chord when they dominate the mids.

## Master chain order

- An automated filter after the master limiter overshoots it: the LIVE 2 intro HPF sat
  after a True Peak limiter at -1 dB and still peaked at 0 dBFS in bars 12-16 (every other
  bar stayed under). Find where peaks happen (bars above the ceiling) before raising the
  ceiling; move effects in front of the limiter (`move_device`, automation follows).
- A filtered intro in front of the limiter gets less gain reduction and comes out louder
  (LIVE 2: -15 → -12.4 LUFS). Re-check intro/break contrast after any master change.
- Tracks outside a group cannot be routed into it (groups are not output targets). Use an
  empty audio track inside the group as a bus: input "No Input", monitoring "in",
  volume 0 dB, then `set_track_output` to it.

- Check `first_beat_s` before trusting any beat-relative number. A render whose 16-bar
  intro has its kick high-passed away gave first_beat 0.43 s (earlier renders 0.03 s) and
  then read the kick at 133 Hz, the clap below the kick and 72 % swing, while the kick sat
  exactly where it did before. Bands, width and loudness stay valid; re-measure the rest
  on a render that starts with a kick.
- Club master that landed inside the producer's references: Auto Filter → Utility (Bass
  Mono 120 Hz) → Glue (2:1, 30 ms, auto, range 2 dB) → Limiter (True Peak, -1 dB). Side
  energy below 120 Hz -27 → -37 dB (refs -38.7), crest 9.8 dB (refs 9.55), mono fold-down
  loss in the drop 0.18 LU.

- A sub sine on a resampled bass's MIDI played an octave above the audio (the source synth
  was transposed): +4.3 dB at 80-120 Hz ("embolado") and -1.8 dB at 25-50 Hz (corr -0.47
  against the bass fundamental). A/B the layer on/off over 8 bars and measure per band
  and the correlation of the added part before trusting it; here Transpose -12 fixed it
  (+4.8 dB at 25-50, corr 0.02, nothing added above 80 Hz).
- Renders record the master: a channel left soloed renders silence everywhere else. Check
  `[t.name for t in song.tracks if t.solo]` before a measuring render.

- Compare a section's spectrum only with references measured the same way (same filter
  bank, a 30 s full stretch of each reference, curves relative to 500 Hz-2 kHz). Against
  the profile's full-track third-octave curve every band read HIGH. Measured like for like,
  "falta sub / embolado" was too much sub, not too little: +16 dB at 40 Hz and +4-7 dB at
  160-250 Hz. These references keep almost nothing below 35 Hz and the weight at 45-65 Hz.
  Fixed with one sub source (HP 55 Hz on the resampled bass), a 38 Hz HP on the sine, a
  34 Hz 48 dB HP on a kick+bass+sub bus, and 200 Hz cuts on bass and music.

- Cutting a section: clear the range, then `shift_clips(track, from_bar, -bars)` on every
  track. Address tracks by index when names repeat (three "CLOSED/OPENHH" tracks: by name
  every cut landed three times on the first one; the bridge now refuses repeated names).
  Track automation does not move with clips: check `automation_state` on each track's
  parameters past the cut first. Live deletes no group's last child: delete the group.
- Inserting time: shift from the earliest boundary first with cumulative offsets (+16 at
  65, then +8 at 145, then +12 at 161), because `shift_clips` moves everything after its
  boundary. Before filling a gap with 8-bar copies, move the next section out of the way:
  a copy that reaches into it overwrites it. After any shift, scan for short clips in
  untouched regions: an early `shift_clips` found its copies with `x not in before` and
  left 1-bar strays (it now finds them by position).
- Setting an automated parameter through the API does not override its automation (state
  stays "playing"): to drop a master filter sweep, remove the device.

- A True Peak limiter at +17-19 dB input had stopped adding loudness (+2 dB in gave +0.13
  LU): the kick hits were already pinned. Soft-clip first, then limit: Limiter (Soft Clip,
  +19 dB, ceiling -0.3) → Limiter (True Peak, -1 dB). The drop went -9.24 → -7.90 LUFS with
  the kick's 40-120 Hz punch unchanged (7.79 → 7.89 dB); +22 dB gained 0.2 LU more and lost
  punch. Full track -8.57 LUFS, crest 9.2, inside these references.
- A FabFilter Pro-L 2 AU exposes no style, true-peak or oversampling and shows gain and
  ceiling as unlabelled 0-1 values: it cannot be set or verified from here. EQ Eight's
  Mid/Side mode is the device property `global_mode` (now `set_device_prop`).
- A render is the master recorded in real time: any play/stop in Live during it cuts the
  file (68 s and 241 s of 355). Check the file's duration before measuring it.

## Automation through clip envelopes

- Live's API writes no Arrangement track automation. Movement goes into clip envelopes:
  `create_midi_clip` / `create_audio_clip(envelopes=[...])` takes device parameters,
  `volume`, `pan` and `send:<n>` (unit `db`). Copies made by `fill_range` keep them.
- A device parameter that already has track automation is the producer's: add a second
  device for clip envelopes (or use volume/sends), never fight their lane.
- `create_audio_clip` auto-warp guessed 1.14 beats for a 33-beat recording: pass
  `beats` (file seconds x BPM / 60) and `length`.
- Rack macros run 0-127, not 0-1: envelopes of 0.25-0.75 on an Instrument Rack's
  "Filter Cutoff" macro held the organ at ~20 Hz and the producer "barely saw the organ".
  Read `p.min`/`p.max` and `str_for_value` before writing any envelope.
- `set_param(display=220)` on a time parameter set Wavetable's Amp Decay to 20 s (a bare
  number reads as the display's largest unit): pass the unit, `display="220 ms"`, and read
  the returned display.
- An answer cloned from the hook's own synth (`copy_device`) blends, but the same chord an
  octave up sounded "too equal": change its role (single-note melody instead of chords,
  pluck envelope, other wavetable position, own delay and pan) and keep the family.
- "More body and tail" on a syncopated answer does not mean longer notes everywhere:
  doubling every hit and dropping to mid-register triads "lost the groove". Keep the
  short off-beat hits that carry the groove; lengthen only the phrase's last note and add
  tail with release/reverb.
- A comp locked to the bass grooves because it stays in one register: lifting every second
  phrase an octave (to free the stab's register) "didn't swing the same" and was reverted.
- Low 808 toms (100-200 Hz, off-beat) "fought the bass's rhythm" wherever the bass played
  and were removed there; extra movement at the end came from a 909 rim/ghost groove
  (rims on 3/6/11/14, nothing below 200 Hz). Keep added percussion out of the bass's
  register and syncopations.
- A clip envelope on "volume" writes absolute fader values while the clip plays: fades
  drawn 0 dB → -40 dB held an ambience at 0 dB whatever its fader said. Draw the plateau at
  the level you want (here -21 dB), or fade with clip gain instead.
- With groove random > 0, two renders of the same bars differ: never measure a layer by
  subtracting an on/off pair; render it soloed (solo keeps its sends' returns) and unsolo.
- This producer hears a snare roll build as "apelativo" (cheap) and asked for tension from
  the track's own elements: the drop's own part previewed filtered and opening, the bass
  filter closing with resonance, the hook's cell in 16ths, a suspended dominant pad, a vocal
  echo thrown into a 2-beat gap. Don't reach for snare rolls or risers by default.
- Frozen tracks refuse new clips ("Clips cannot be created on frozen tracks"): copy their
  existing clips with `fill_range` instead, and do not delete a clip there you cannot
  recreate.

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
- Inspect the loaded modulation device's actual parameters: Auto Pan-Tremolo
  (`AutoPan2`) exposes Panning/Tremolo, Time Mode and Rate rather than the older
  Auto Pan controls. Verify the resulting displayed sync cycle and depth. A
  four-bar pan cycle can alternate a two-bar reply between sides; keep kick/sub
  centred and verify low-band as well as upper-band mono loss after rendering.
- Converting beat boundaries to samples can make two nominally equal passages
  differ by one sample. Copy to the destination's exact frame count, rather than
  assuming independently rounded boundaries produce equal array lengths.

## The ear (what the analysis can and cannot hear)

- Chords are read from spectral peaks in 110-1500 Hz only. Over a bass pedal, read the upper
  chord without the bass and write a slash chord. Chord roots in a busy breakdown are right
  only about half the time: say so.
- Measurements catch technical problems; they do not judge groove or taste. Say so, and ask
  the producer to listen.
- A confirmed source and complete word boundaries do not establish that a vocal
  belongs with the harmony and pocket. When its fit is rejected, verify the
  instrumental conversation in the producer's preferred passage before repeating
  a phrase across the whole arrangement. Present a short musical preview early;
  peak and mono results do not answer feedback about character or generic writing.
- After removing a vocal, reassess both breaks independently: a previously filled
  16-bar passage can become a hole when kick and bass disappear together. Preserve
  a recognizable drum/bass pulse or shorten the withdrawal, develop the established
  hook across the handover, and reserve deep-sub contrast for the actual arrival.
  Risers alone do not restore musical continuity. If the producer follows Live and
  declines repeated exports, verify source/clip continuity and use native playback;
  do not automatically start another full-track master recording.
- A break can still feel disconnected with kick/sub present if their levels,
  open hats, harmonic filter and motif all reset at the same locator. Inspect
  individual bars across the disputed edge, carry the actual preceding phrase
  through it, and stagger withdrawals. Noise lifts into a lower-energy section
  can promise the wrong arrival. Bass pickups and quiet harmonic tails may cross
  bar lines; do not cut every musical voice into self-contained eight-bar blocks.
- Check sampled chord pitches before changing harmony: a Bm9 key and Bm stab
  may share the correct tonic but still need complementary registers and a
  moving upper voice. Preserve a liked timbre/call rhythm, reduce duplicated
  extensions where needed, and resolve deliberate string dissonances. Transposing
  an entire sampled chord is not independent voice leading. Harmonic-band
  extraction also shares partials between notes; do not describe it as perfect
  polyphonic separation or claim aesthetic success from pitch-class checks.

## Safety with the producer's project

- Work on a copy, never the original. Live has no save API: ask the producer to press
  Cmd+S / Ctrl+S before a risky stage.
- Every change through `ableton_command` / `ableton_batch` is journaled: `change_log` shows
  it, `revert_changes` puts the old values back exactly. Deletes and range edits are not
  revertible this way: archive (mute) instead of deleting, or use `live_undo`.
- Inserting tracks renumbers Live's untouched default names (for example 1-MIDI
  becomes 18-MIDI). Before an authorized cleanup, verify the current layout against
  the snapshot. For verified contiguous old tracks, delete from the end by current
  index; do not address a stale default name or mistake a new track for an old one.
- Live starts playback at its start marker, not the playhead; renders check the recorded
  length. Renders are real time and need an audio output device: "playback never started"
  usually means the interface was unplugged (Live > Settings > Audio).
- Verify collected media paths, not just the dismissal of Collect All and Save:
  one collect during playback left the new User Library references external; a
  repeat with transport stopped copied and relinked all ten files successfully.

## Groove study: repetition, subtraction and evidence

- For new house/tech-house 4/4 foundations, `music_pocket_sketch` generates coordinated
  drums/bass and a stripped alternative with the same anchors. Inspect actual BPM,
  key and Drum Rack mapping. Existing material should be inspected, not replaced by default.
- MIDI swing and role offsets are already baked in. Avoid accumulating another groove.
  First compare subtraction, then swing, role offsets and articulation separately.
  MIDI gate space does not prove acoustic separation: audition kick decay/bass release.
- Keep a repeatable cell and a focused phrase-ending change. Optional percussion can
  answer bass rests; empty slots are opportunities, not obligations to fill.
- Evidence: Ableton Live 12 Using Grooves distinguishes Timing/Random/Velocity;
  Making Music, Arranging as a Subtractive Process and Unique Events motivate these
  experiments. Witek et al. (2014), doi:10.1371/journal.pone.0094446 studied preference
  for intermediate syncopation in drum breaks, not a universal swing optimum.
- For 'current' sound, verify release dates and relevant reference audio. Compare equivalent
  sections at matched perceived level; unknown dates remain unknown. Record hypothesis,
  changed variable, A/B listening preference and limits; do not turn one choice into a rule.

## Traps found re-arranging TH130 (2026-10-17)

- `record_abort` leaves the half-recorded render track in the set, unmuted. On TH130 it
  replayed an old mix of bars 1-93 over the new one: the producer heard "muddy synths",
  a "strange bass" and a sudden drop at bar 93 where the recording ended. After an abort
  or a timed-out `render_wait`, list the tracks and delete any render track.
- Creating an audio clip over an existing arrangement clip overwrites that range. A
  40-bar kick file placed at bar 49 and then trimmed to 53 erased the kick from 57 to 89.
  Place clips only into empty space, or use a source as long as the gap.
- Breaks: a drop of 8-9 LU (kick, bass and the harmonic stems all out at once) is what
  "too abrupt, no groove" sounds like. Leave in steps: kick stays 4 bars with the bass out,
  then the bass (no sub) takes over when the kick leaves; the references fall ~3.4 LU.
- A build that only swells a pad reads "dry, no energy". Measured fix: an accelerating
  roll in the track's own clap, rising keys velocity, a louder riser, groove (bass without
  sub) running to half a bar before the drop: +1.5 LU over 8 bars, drop +2.6 LU.
- Never shorten a kick's tail with a Gate without checking the stem's raw peak: a -10 dB
  threshold over a kick stem peaking at -9 dBFS let ~55 ms through and dropped the rest of
  every hit 12 dB. The producer heard "the track has no kick". Measure the whole hit
  (peak and 35-130 Hz body against the off-beat), not only `kick_decay_ms`.
- The master limiter decides who wins: at +9 dB input it flattened every kick to the
  ceiling while the off-beat bass passed, so the bass read louder than the kick. Set the
  balance with no limiter first (kick peak >= 5 dB over the off-beat, body ~5-8 dB over the
  bass), then add drive. One bass layer: a sine sub under an FM bass beat against a 53 Hz kick.
