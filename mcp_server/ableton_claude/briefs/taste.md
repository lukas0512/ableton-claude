# The producer's quality bar (his feedback, distilled)

Every rule below is something the producer who trained this connector asked for or rejected,
mostly while building "From The Streets" (a 125 BPM house remix of two 90s rap records,
2026-10-20, 27 versions), plus earlier tracks. He judged v27 "ok, já considerado ok, but it
can still be polished": treat that as the floor for the next track, not the goal. Quotes are
his words. Numbers are what made the rule pass when measured.

Before handing any version: run `quality_gate` (static checks of the set), then render and
measure, and run `quality_gate(render=…, previous=…, study=…)` once more: a section that
scores worse than the previous version (audiobox CE/PQ) is a warning to listen to. He listens in Live while you work: after each pass start playback for him at the
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

- **Every drop gets the formula of the strongest one** (Let The Rhythm, 2026-10-20: "o
  primeiro drop tem muito mais força que os outros"). The first hook hit hardest because it
  was the only one with a 2-bar kick hole, a stab pickup in the last half bar and stab + ride
  + voice + crash all landing together; later drops came back without the stab/ride or the
  voice. Give each drop that whole entrance, and drop 2 every layer plus the voice. Measured:
  grooves and drops sat within 0.3 LU (-7.6..-8.0 LUFS) under the limiter: the contrast has
  to come from what enters, not from level.
- **A break in a club track stays "pista"** ("break muito sem energia, fraquinho, não tem
  build up"): kick out but every percussion layer, the stab and the filtered bass keep
  going; nothing drops out two bars early. The build brings the kick back from bar 5 of 8:
  quarters, 8ths, then 16ths up to the 2-beat breath, its velocity rising (Simpler
  Vol<Vel 100 %; leave every normal kick at 127). Passed: -9.6, -8.9, -8.4, -8.1, -8.2 LUFS
  per bar, drop -7.4. Too-loud 8th kicks put the bar before the drop over the drop (-6.2).
- **A flat break is one you can read in numbers** ("no break falta um movimento, falta tensão no
  build up", TECHNO #8 v3). 16 bars within -14.0..-14.4 RMS with the bass's sub on, centroid 520-545 Hz,
  highs moving 1 dB over the build; the reference's 2nd break sat 7-10 dB under its drop with
  its centroid at 1.8-3.5 kHz. v4: bass and loop out, the drop's riff dissolving through a low-pass,
  a filter arc opening further each 4 bars, harmony over the riff's pedal, the build's highs +2.8 dB,
  the last bar the voice alone. Measured only, not yet heard.

- **A build is a climb to just under the drop** ("fazer mesmo pressão, subir bem a energia no build up pra
  cair num drop forte", TECHNO #8 v4). Both drops get the same arc, shorter for drop 1: sub out, the
  high-passed kick gaining weight through 8ths and 16ths, the opening synth pumping from that kick, the riff
  climbing the scale, one bar of voice alone. Measured v8, not yet heard: -14.1 to -11.9 RMS, highs +4 dB,
  breath -23.8, drop -9.7 with the low band up 16 dB and a sub falling onto the root.

- **Melodies must sit in the track's timbres** ("agudinho estranho... os acentos uma oitava muito acima...
  noção dessas melodias", TECHNO #8 v5). Solo every melody against the loop it belongs with, band by band
  and note by note; move a note that rings outside the track's register before reaching for EQ. "Duro" was
  the same part: a resonance 13 dB over the rest, nearly mono, full-length notes.

- **Ear candies at the turns**, from the track's own material: its vocal phrase reversed
  through a reverb into each drop, a reverse cymbal, an F# sub boom on the drop downbeat, the
  phrase's last syllable thrown into a baked 3/16 ping-pong echo at phrase ends and before
  drops, a soft reverse cymbal at each drop's 9th bar. ("falta mais earcandies e detalhes")

- **Monotony is measured, then broken by absence** (From The Streets v28: "às vezes tá muito
  repetitiva e monótona... groove por ausência, uns glitches"). v27 had every kick phrase
  within -8.8..-9.2 LUFS and a loudness range of 2.7 LU. Take things away for a moment
  instead of adding layers: the bass resting beats 2-4 while the riff answers, the kick out
  for beats 3-4, a full drum stop for two beats in the middle of a drop, the 16th hats out
  for two bars. Each hole gets one glitch made from the track's own voice or riff (the
  title's first syllable stuttering 16ths -> 32nds falling in pitch, the title in a tape
  stop, the riff's attack bit-crushed in 32nds, the hook chop reversed then gated), never
  on top of a transition FX.
- **The second break + build must not outstay** ("ficou muito grande"): 16 + 8 bars passed
  where 16 + 16 was too long. A special layer (the breakbeat) is a sauce, not a bed ("fica
  por muito tempo e não dando só o sauce na hora certa"): it enters for the last 4 bars of
  the break, drives the build's chops, and in the drop only answers at phrase ends (2 bars
  every 8), never 16 bars straight.

- **A shortened build must still rise** ("falta um pouco de tensão e release bem feito"):
  cutting a build's first half left only its loudest bars. Rebuild the arc by subtraction:
  first half without clap, off-beat hats and perc loop, everything back for two bars, then
  one bar a cappella (the music out, the voice and its echo) and the drop. Passed: -10.8,
  -9.7/-9.4 (highs +3.5 dB), a cappella -12.1/-12.7, drop -8.2 LUFS.

- **Build to drop, measured on the references, not invented** ("olhe referências... não
  invente qualquer coisa"). Sexy Vibes (9 refs), the 8 bars before a drop: the kick's sub
  (40-100 Hz) is gone, 35-50 dB under the drop; a high-passed kick often keeps pulsing in
  quarters in 120-250 Hz (Ssero, Mood Child); the bass stays only filtered; in the last bar
  the low end and body fall further while the highs (hats, voice, FX) keep their level; the
  drop brings the sub back +35-40 dB. Our bar-long a cappella cut the highs too: that is what
  "killed the energy". Build the filtered kick on its own track (same sample, EQ HP 48 dB at
  180 Hz, into the drum bus). Never change the main kick's Vol<Vel for it: with every kick note
  at 127 it still made the kick louder and the bass, keyed by the kick, vanished in the drops.
  No looped one-bar cells repeating the same words through the build ("loops batidos falando
  a coisa errada"); a fill (909 tom run) and the title's syllable stuttering are the pre-drop.

- **A build must start at or above the break and climb to its last bar** ("o build up não faz
  pressão e alívio, tá fraquinho e reto"). v35's build opened 2-3 LU under the break it followed.
  Carry the break's groove into the build and open it: a low-passed loop with its filter rising
  450 Hz -> 1.8 kHz and +6 dB over the build, the high-passed kick gaining weight (HP 400 -> 150 Hz),
  density up in the last bar of the climb (kick and clap in 8ths), then one bar with the lows out.
  Passed (2-bar averages): -10.2, -9.9, -8.7, breath -11.2, drop -7.9 LUFS.
- **Pressure and relief, measured every version** ("pressão e alívio dos drops pode ser
  melhor", Murder v31). v30 sat at -8.0..-8.4 LUFS from bar 9 to 176: the breaks only 2 LU
  under the drops and build 1's top bars over drop 1 (-7.8 vs -8.2). One gain map for the
  music loops (grooves -1.5, breaks -2.5, the build climbing 0 -> +4.5 dB, drop 2 +1.5), the
  breaks' sub ~8 dB under the drop, the high-passed kick pulsing through every build (HP 400
  -> 150 Hz, 8ths in the last 2 bars, velocity 70 -> 120), the record's choir re-struck every
  bar under an opening filter as the riser, the drop's sub never played inside a build.
  Passed: break -12.6, build -12.7 -> -11.5 -> -10.3, a cappella, drop 1 -8.6; build 2 -12.4
  -> -10.4, drop 2 -8.4.
- **A clip envelope on a device parameter stays where it ended**: every other clip on that track
  needs its own envelope holding its value (the groove's low-pass at 450 Hz in the break, the HP
  kick at 180 Hz in intro/outro), or the next pass plays with the build's last setting.
- **A stem's "other" loop can carry the original DJ's scratches**: keep the groove, lose the
  scratches with a low-pass (~450 Hz); he deleted the whole loop once because the scratches were
  too loud, and the break lost its bass-line groove with it.

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

- **A solo in the breakdown is thematic and played by hand** ("humanizar muito mais o começo
  desse solinho, fazer algo mais temático e esticar mais no break, às vezes fica vazio"):
  take the theme from the vocal hook's melody (pitch-track it: "lift your hands" = C#5 A4
  F#4, 5-3-1), state it alone, answer it, harmonise it, lift it an octave, and carry it into
  the tension (call/answer, then compressed every half bar up high). Humanise: lay back on
  beats, push the anticipations, +-6 ms scatter, velocity/length variation, half-step
  graces, ghost repeats, rolled double stops. A breakdown with no low end at all (sub 1 %)
  read as empty: keep the filtered bass under it (sub ~40 %).
- **Swing**: on Let The Rhythm he asked for "mais groove e mais swing": 54 % -> ~58 %
  (Swing 16ths 57 at 115 % on every MIDI part; the loops that already carry ~54 % get the
  54 groove on top, timing only). Subtract percussion in the grooves rather than add.

- **Parts must converse, not stack** ("sem groove, só vários elementos tocando várias coisas sem
  sentido, sem se conversar, sem sentimento", Project #6 v2, 2026-10-28). v2 layered pack loops
  from different packs, each busy on its own (a stab loop ~11 attacks a bar, a bass loop ~8 notes
  with several on the kick) over two drum kits at once. Measure every loop's onsets on the 16th
  grid before choosing it; keep ONE drum system; let the sparse harmonic loop (4 off-beat hits a
  bar, like the references) be the stab and write the bass in its holes and the kick's (ear: 100 %
  off the beat, 0 % with the kick). Hats need phrase variation, never a pasted bar: his accent map,
  a pocket every 2nd bar, a breath on a downbeat, a 32nd flutter into each phrase. A lead voice
  needs company: a second phrase answering it and ad-libs under the drops.

- **One pocket, checked at the sample** ("parece que são grooves diferentes", Project #6 v5): two
  hat "one-shots" were 7 s files whose first hit came at 234 ms, so every hat note sounded half a
  beat late; the piano's swing had been counted twice (28 ms against the hats' 15). Trim every
  one-shot to its attack before it goes into a Simpler, and bake one off-16th delay into every
  written part (the pool groove only on kit parts at the same amount).
- **Stabs are short and dry** ("muita cauda o timbre"): a sliced chord let ring until the next hit
  smeared the groove; cut each hit at ~140 ms (references: 70 % of stabs ~110 ms), keep the sends
  low (plate -24, long tail -26). Held chords only in the breaks.

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

- **Find the record's own tempo and pocket before cutting a voice** ("o chop ficou meio quadrado,
  meio sem groove, fora de warp alguns, não tão alinhado com o groove e o bounce do projeto", TECHNO
  #8 v3). Unwarped chops of a 123.6 BPM voice placed one by one in a 128 track slid and read square,
  though each attack was on the grid. Read the source's onsets on its pinned beat grid: this voice's
  4-beat cell (0, .75, 1.25, 1.75, 2.25, 3) already shared the riff's off-16ths. Warp every piece
  and keep it on its own beat phase; let the riff and its audio double leave room where the voice
  answers, so the voice continues the riff. He then asked for delay and reverb, light with moments
  of more: the chops stay dry-ish and the calls carry the echo.

- **Voices enter and leave like a record, not a cut** ("cortados na forma certa... entrando
  e saindo mais na boa... pra não parecer que foi cortado"). Phrases cut on the source's bar
  lines start or end mid-word (v29: the City call ended at -16 dB, hook B opened at -18).
  Re-cut from the vocal stem: find the phrase by cross-correlation, move each edge to the
  nearest gap between words (-26 dB under the phrase peak), fade 8 ms in / 40 ms out. Dense
  rap often has no gap for 1.5 s: then let the phrase dissolve (150 ms fade) into an echo of
  its last syllable. Echoes live on their own track (VOX - throws), unwarped, a 3/16
  ping-pong at the track's tempo, darker each repeat, into the voices' plate.
- **Not where the ear expects it** ("às vezes os vocais tão em lugares bem óbvios... a track
  um pouco previsível"): a call every 4 or 8 bars on the same pick-up becomes wallpaper. Keep
  the call at the theme's first statement and before breaks; move the others mid-phrase (beat
  2.5 of bar 2 of 4), drop the ones that only repeat the pattern, and let the drop's hook
  enter in its second 8 (in a kick hole), not on the drop's downbeat.

- **His call pattern** (From The Streets v31, he fixed two calls himself): one statement before
  a hook, never the same call twice in a row ("o vocal está repetindo 2x, aí perde o hook");
  the first call with its pick-up, cut on the next bar line (31.875 -> 33.0); a later call
  without the pick-up, starting on the downbeat, one bar (40.0 -> 41.0). The same one-bar
  call on the drop's downbeat (65). A phrase clip must never be left looping longer than its
  phrase: `quality_gate` now fails on it ("phrase repeats").

- **One channel per vocal role** ("separar em canais diferentes os vocais que são diferentes...
  e dá pra dar energia"): calls (the theme), hooks, radio versions, the second voice's answers,
  each with the source channel's chain copied, all into one vocal bus and one plate. Then each
  gets its own energy and level against the kick (limiter off): hooks got a parallel Glue
  (4:1, 50 % wet, +2 dB) and +1 dB saturation, and still read -10 LU under the kick, so +1.7 dB
  to the approved -8.3; calls were hot at -6.5 LU (-1.5 dB); the Murder answers +1.5 dB to sit
  with the City.

- **The energy curve, measured against the references** ("mix profissional e com sentimento,
  pensando na dinâmica e avanço da música"). Sexy Vibes medians, each section type against the
  loudest 8 bars: intro -4.2 LU, groove -0.7, break -3.8, drop -0.9, outro -6.4. From The Streets
  v34 read intro -0.7, break -1.9, outro -0.5: a kick alone already fills the limiter, so the
  track started at the top and never advanced. Fix by subtraction and filtering, not faders:
  the kick high-passed (sub off) for the first and last 8 bars (the same HP kick channel as
  the build), the break bass only in each break's second half, loops/atmos/hook clip gain -2
  to -3 dB inside the breaks. v35: intro -3.7, break -2.6, LRA 2.5 -> 3.3 LU. A track with
  volume automation (the guitar's energy map) takes its trim as clip gain, never a fader move.

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

- **One atmosphere** ("não tá tudo na mesma atmosfera"): the loops sat in one reverb, the
  voices in a plate, the FX in a third, the clap almost dry. Put every melodic part and
  voice in the same plate, a shared long tail (an atmos return) low under all of them, every
  drum in the same short room. Width above 200 Hz: v27 drops read 6-7 % side/mid against
  the Sexy Vibes references' 6-56 % (median ~16 %): pan the two loops apart and widen the
  music bus (Utility 140 %, bass mono 120 Hz), not the drums, bass or lead voice.

- **Fix the balance in the elements, not on the master** ("acerta o sub e o ar nos
  elementos"). Measure each element soloed with the master glue and limiter OFF (through the
  limiter everything soloed reads the same level) and remember the master EQ is still in that
  path: moving a correction off the master changes every solo reading. From The Streets v29:
  sub 47 % -> 44 % and low 40 % -> 43 % (Sexy Vibes 35-46 / 42-54) from kick -3.5 dB @50 +2.5
  @90, bass fader -1.5 (back to -3 LU under the kick) +3 dB @85 (the E1's 2nd harmonic, root
  untouched); air from undoing the drum bus's -2.5 dB shelf @9k (now -1.5 @7k + 2 dB shelf
  @14k), +2 dB @13k on the hats and a 12 dB slope on their drawn low-pass; the 630 Hz excess
  was the City vocal (-2.5 @630, +1.5 @1.6k, +2 @5k on the VOX bus) and a narrow resonance
  in the City synth. The master EQ then only keeps HP 32, +1 @85, -1 @45 and a 2 dB air shelf.

- **Every voice and scratch on its own fader** ("os scratchs com o vocal Murder estão na mesma
  clip e os scratchs ficam demais às vezes"): a loop cut from the record carries rap and
  scratch with the riff. Split it (riff / voice+scratch) so the scratch can sit lower (-4 dB
  passed first) without touching the riff. Chops built from a syllable must be tuned and in
  key, the second bar answering the first ("a primeira frase tá certa, o resto desafina").

- **A "strange high" that relaxes in the breaks is a resonance in a loop** ("tô sentindo um agudo
  estranho... quando cai no break dá um alívio, como se fosse um ruído", From The Streets v39):
  the City synth stem carried two narrow peaks 113 Hz apart (1.99 / 2.11 kHz, +17/+16 dB over
  their surroundings) that beat into a rough texture. He picked, by ear from four 8-bar A/B
  files, the synth notched (-5 dB @2.05 kHz Q6, -3 @3.33 kHz Q6, low-pass 7 kHz) over taming
  the 909 ride. Look for narrow peaks per soloed element; the aesthetics model cannot hear it.
- **Each pre-drop gets a voice of its own** ("o pré-drop não tem nada pra caracterizar e
  chamar a galera"): City a cappella into drop 1, the Murder trade's first line a cappella
  into drop 2, cut at its natural pause and thrown into delay + plate. Open hats breathe:
  out for the first 8 bars of a drop, back with the hook ("o open hat tá muito corrido").

- **No long tails on voices or scratches** ("reverb gigante no scratch + Murder vocal, fica uma
  cauda gigante no fundo... tudo alinhado e colado"): a 4 s atmos send on the voices smeared
  the whole mix. Voices, throws, chops and scratches: the 1.4 s plate only. A shared long
  return is glue for the loops at most, short (2 s) and low (-20).

- **Gain staging: the kick at -10 dBFS, everything else under it, the master pulls the rest**
  ("vamos fazer a mix sempre com o kick em -10 e o resto em cima disso, lembrando o kick ser o
  elemento mais alto da track; depois esse espaço que vai sobrar puxamos com a master, pra ter
  algo com mais qualidade e mais colado", Murder v31, 2026-10-28). Measure with the master
  chain off: the kick's channel and its share of the master input peak at -10 dBFS, no element
  peaks or reads louder than the kick, the mix lands ~-4.5 dBFS / -17.6 LUFS in a drop. When
  every channel moves, move what reacts to level with it (bus compressor thresholds, keyed
  compressors, bus saturators' drive/output, a bus limiter's ceiling) or the balance changes.
  Then the master: no headroom trim, its Glue doing the glue (2:1, 10 ms, range 4, ~-19 dB
  threshold), no makeup gain into the soft clipper (+2 dB there crushed every kick: the drop
  read -7.4 at crest 7.7), the TP limiter +13. Passed: drop -8.4 LUFS at crest 8.7 (v30 -8.0
  at 8.6), break -12.3, whole -9.35, -0.33 dBTP.

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

## 9. The standard of his reference folder, measured (Dub House Streets, 2026-10-22)

He: "analisar os detalhes e o porquê das músicas que escolhi: o groove das drums, o timbre do
baixo, os stabs e keys... criar um padrão de bom gosto, medido nos detalhes". 13 tracks
separated (htdemucs) and measured; medians [p25..p75]. This is the target his tracks are
judged against; where the references differ, it is a choice to make with him.

- **Drums**: kick 4x4 (never broken), clap on 2+4, 16th hats; one swing for hats and claps
  (~56-57 %). Hat accents: the off-beat "and" +7.5 dB over the on-beat, the "e"/"a" 7 dB under it,
  ~12 hits/bar, ~27 % ghosts. A quiet busy mid-perc layer (~11 hits/bar, 30 % ghosts). Variation
  from percussion (1.3 pattern changes / 16 bars), not hats; the kick drops out for one bar ~3x per
  32 groove bars, mostly on a phrase's 8th bar. Claps dry (~87 ms to -20 dB). No snare rolls.
- **Bass**: 95 % of notes off the beat, 7 % with the kick; ~5.4 notes/bar, ~2 16ths long, cut not
  decaying. Kick and bass share time by note placement more than sidechain: bass -19 dB at the
  kick, back within 3 dB after ~190 ms. Tone warm and dark, even harmonics (2nd -2, 3rd -11,
  above 300 Hz -28 dB), mono, register B1-C2.
- **Stabs/keys**: in ~63 % of bars at -15 dB under the drums; 70 % short (~110 ms), 74 % off the
  beat, mid register (~780 Hz), wide; m9/maj9/7sus4, ≤2 changes per 8 bars; movement from filter
  sweeps (~5 sweeps of 4+ bars).
- **Vocals**: voiced only ~33 % of the time; phrases short (median 1.2 beats, 90 % ≤ 4 beats, 3 %
  ≥ 8 beats): chops and one-liners repeated as a hook (bar-to-bar correlation 0.7+), not verses;
  -16 dB under the drums, dry, narrower than the music. Rap verses over house read "fora da
  música, fora de warp" (Murder pista, 2026-10-22).
- **Arrangement**: 16 bars drums, bass at 17, something changes every ~4 bars; breaks drop the
  kick (and the bass half the time) and keep clap, hats, stabs and the hook, 1-4 LU under the drop;
  drops land on kick + bass returning, not on FX. The theme: a short vocal hook over the off-beat
  bass, stabs colouring it, drums never stopping.
- Full data: the study `dub_house_streets` and the analysis scripts (taste_standard) in the
  session that produced this; re-measure with the same method for a new reference folder.

**What he rejected from that standard in practice (Murder pista v18-v21, 2026-10-22):** the guitar
riff cut to "colour" spans ("quando o riff da música sai parece que a track morre"), one-bar
kick-outs and perc rests ("estragou o arranjo"): keep the record's riff continuous under the drop
and the kick 4x4. And the low end must never vanish: in breaks and builds a low-passed sub plays
the bass riff ~8 dB under the drop (out only for the 2-beat breath) -- "quando tirar o médio não
pode ficar sem sub, que faz o movimento e o groove". A re-created Simpler loses its detune: the
bass carried +14 cents to sit with the record; 0 cents made it "sem peso".
