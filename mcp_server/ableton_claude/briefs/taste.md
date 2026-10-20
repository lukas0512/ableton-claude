# The producer's quality bar (his feedback, distilled)

Every rule below is something the producer who trained this connector asked for or rejected,
mostly while building "From The Streets" (a 125 BPM house remix of two 90s rap records,
2026-10-20, 27 versions), plus earlier tracks. He judged v27 "ok, já considerado ok, but it
can still be polished": treat that as the floor for the next track, not the goal. Quotes are
his words. Numbers are what made the rule pass when measured.

Before handing any version: run `quality_gate` (static checks of the set), then render and
measure. He listens in Live while you work: after each pass start playback for him at the
section you changed (`transport(action="play", bar=…)`) and say what to listen for.

## 1. It is a club track ("não é um pop", "pensa em alto-falantes")

- **Form**: intro A drums only (16, DJ) → intro B, layers entering one by one (16) → groove
  (16) → break 1 (8) + build 1 (8) → DROP 1 (32, its lead layer entering in the 2nd 8) →
  main break (16) + a bigger build (16) → DROP 2 (32, everything from bar 1, the strongest)
  → outro A (16) → outro B drums only (16). 192 bars at 125 BPM, ~6 min. "Faltam dois drops,
  o intro, o outro."
- **Layering**: never several parts entering on the same bar ("a entrada no 17 muito brusca,
  muita coisa entrando junto"): one new layer per 4 bars in the intro.
- **DJ friendly**: intro and outro drums only; no vocals in the first and last 16 bars.
- **Energy contrast**: grooves vs hooks measured flat (0.3 LU) and read as "sem dinâmica";
  create it by subtraction (the snare layer and reserved hats only in hooks/drops, toms
  only in the second half of grooves), not by adding.

## 2. Tension and release

- Breaks: refs keep 3.8-5 LU under the drop. Falling in one bar by 6-9 LU is "brusco": a soft
  crash on the break's first beat, a reverb wash of the drop's riff, the hats darkening over
  two bars.
- Builds rise: refs +0.2 LU and +0.3-0.6 dB of highs per bar. Ramp the build's own parts
  (riff, City synth, bass teaser high-passed so the drop's sub is the release) with clip
  volume envelopes under opening filters.
- The breath: the last 2 beats before every drop empty (refs dip 3.6 LU there).
- **Pre-drop with character**: the whole track stops one bar, the title line a cappella, its
  last word into the delay, a reversed crash, a DJ rewind, then the drop with a doubled
  crash and a sub boom. "Algo característico da track."
- He rejects snare-roll builds and generic risers ("apelativo"), but asked for a breakbeat
  in the main break that chops faster through the build (beats → 8ths → 16ths): tension made
  from the track's own material is welcome.
- Drop 2 must land harder than drop 1 ("o drop tá fraquinho"): the break layer under the
  kick, boom and crash +3 dB, loops +1.5 dB, every reserved layer from bar 1.

## 3. Groove and drums

- **One pocket**: every 16th part swings the same (kit: off-16ths +10.8 ms at 125); a hat
  at +15.7 ms against congas/bass at +10.8 and a shaker at -10.4 read as "bateria desconexa,
  os hats perdidos". The clap leans 5 ms late, the shaker shot 5 ms early, nothing else.
- Hats carry the kit's accent map (on-beat 16ths ~11 dB under the off-beat 8ths; Simpler
  Vol<Vel 100 %); flat velocities read "muito retos". Vary them: a pocket every 2nd bar, a
  32nd flutter at phrase ends.
- The clap is the anchor, the continuous hats sit behind it ("hi-hat contínuo alto"): clap
  ~-9 LU vs the kick, hat 16ths ~-16, off-beat hat ~-15.
- Clap: 2 and 4, one pickup every 4th bar, a short tail (Classic Simpler, short notes,
  60 ms release); a 300 ms room on the sample plus a generic reverb read "fora da bateria,
  muito reverb".
- Glue: a DRUMS bus (Glue 2:1, 10 ms, range 4 dB, threshold ~-22, high shelf -2.5 dB at
  9 kHz, soft-sine saturation 2 dB at 35 %) and one short room (0.8 s) for every drum.
- **Fills matter** ("use fills, são importantes"): conga runs every 8-bar phrase end, a 909
  tom run on bigger turns, clap pickups; never on top of a transition FX.

## 4. Low end ("tem que sair ar do alto-falante quando bater o kick")

- The kick is the loudest element; everything is set from it ("o kick mais alto e todo o
  resto se guiando pelo kick").
- The original's own bass riff beats a generic one ("esse baixo combinou muito"), at the
  record's octave so the sub is its fundamental ("o baixo está sem sub"); no separate sine
  sub on the same octave (phase).
- The kick owns the first ~150 ms: bass sidechain 6:1, 0.1 ms attack, 110-140 ms release.
  Low band <120 Hz mono (correlation ~1), no DC, ~symmetric.
- Low-end curve against the references' 1/3-octave middle half: 32 Hz and 125-200 Hz are
  where "embolado" lives; cut on the part that makes it, never high-pass a bass above its
  root, and clamp the register after transposing (no notes under the bus high-pass).
- Polish: bass Saturator ~35 % wet, low-pass 3 kHz, +1.5 dB at 110 Hz definition.

## 5. Harmony, timbre, the hook

- Harmony comes from the originals: their demucs "other" stems as 2-bar loops (a guitar riff
  he loved, a synth). A generic preset (House Stab) was "timbre estranho, toca muitas
  vezes, não combina com o vocal".
- A synth loop's 3-10 kHz buzz ("buzzy") is filtered (open = 6 kHz, never 18 kHz).
- Loops give movement: never shorten them to make room ("não devia ter encurtado"); duck them
  under the bass (compressor keyed by BASS) so they speak in its holes.
- The theme (the title line) is the teaser at the turns and the lead of the hooks; disclose
  it in stages.

## 6. Voices

- Sparse beats busy: the v14 dynamic (few phrases, space between) was better than trading
  lines; 4-bar statements with the riffs answering.
- Two sources must sound like one record: measure both soloed, match level within 1 LU and
  tone per band (an mp3 source was 4-6 dB darker above 2 kHz), same bus, same plate, the
  same sends ("parecem samples diferentes", "na mesma atmosfera").
- Warp rap per syllable: markers on detected onsets moved 60 % onto the 16th + the kit's
  swing (31 → 14 ms deviation). Chops for repetition start at a real syllable onset,
  unwarped; grid slices of a warped phrase are "mal warpada, feia".
- Scratches are FX, never part of the music: rare, at bar changes, on their own track, low
  ("o scratch tá alto, roubando a música"). A rap hook that repeats the intro bar for bar
  is usually the DJ's scratch: use the verses instead.
- Story: the voice far (radio band) in the intro, real and close in the break (its filter
  opening over 2 bars), the title a cappella before the drop.

## 7. Mix process (measured, every time)

- Solo every element over the same 8 drop bars with the master limiter off and compare
  integrated LUFS with the soloed kick. Targets that passed: bass -3, clap -9, City hook
  -8.3, rap -8.3 (both voices equal), lead riff -12, back synth -16/-18, atmosphere -20,
  ride -20, tom -18, breakbeat -10 (in its break), reverb returns ~-20 each.
- Per 1/3-octave band, list the elements within 6 dB of the loudest: cut the lower-priority
  one there (kick -3 dB at 400 Hz, congas -2 at 315, riff -2 at 630 / +1.5 at 1.6 kHz,
  voices -2.5 at 350, Murder matched to City).
- Gain staging: every source ~-6 dBFS into its effects (Simplers at -12 dB); a hot source
  "saturado em cima do clipado" is a mistake he will see in the meters.
- After any fader move on a track with clip volume envelopes call `re_enable_automation`.
- Master for his car / a beach club: EQ (HP 28 Hz, +1 dB 3.5 kHz, +1 dB air) → Glue 2:1
  slow, range 3 → Limiter True Peak -1 dBTP; -9.6 LUFS integrated, drops -8.9, crest ~8 dB.

## 8. Project hygiene ("muito desorganizado")

- Delete rejected experiments (the script recreates them); originals as muted REF tracks on
  top; buses LOW END / DRUMS / VOX / MUSIC (kick-ducked) / FX; colours by band and role
  (red low end, orange drum body, yellow hats, brown percussion, green harmony, cyan
  atmosphere, violet voice, pink FX, grey refs). Live's API cannot group or reorder tracks:
  tell him, he groups with Cmd+G.
- Never leave a measurement or render track in the set: one left playing doubled the loops
  in the drop for four versions.

## Still to polish (his last notes on v27)

Not perfect yet: the drop-2 impact can grow, the voices and the breakbeat can glue further,
more ear candy with character (US gangster rap meets UKG), and a lighter, summery, bouncy
master for a beach club.
