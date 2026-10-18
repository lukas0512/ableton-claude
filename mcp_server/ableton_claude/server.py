"""MCP server exposing Ableton Live (via ClaudeBridge) and audio analysis to Claude."""
import os
import time

from mcp.server.fastmcp import FastMCP

from . import analysis, client, genres, journal, knowledge, library, loops, mixing, references, tension, timbre, validate
from .music import club, groove, harmony, melody, pocket, samples, theory

INSTRUCTIONS = """\
Drives Ableton Live through the ClaudeBridge Remote Script (127.0.0.1:9878).

Before you change anything in a project, call `producer_brief` and work by it: inspect,
diagnose, prioritize, modify in small groups, verify by render, compare, repeat.
Every change is journaled: `change_log` lists it, `revert_changes` restores what it
replaced (keep or revert after each render), `live_undo` is Live's own undo.
References for the track being made: `study_references(name, paths|folder|from_live)`
studies ~5 of them (measured and heard) in the background; `study_status` returns a brief
(what they share and why, where they disagree, a section plan). The study's name then
works as `genre` in every genre tool. Propose ideas from it and ask before changing the set.

Start with `ableton_status`. Use `ableton_command` for any bridge command and
`ableton_batch` to run many in one Live tick (much faster for building arrangements).

Addressing: track = index | exact name | unique name fragment | "master" | "return:<i|name>".
Clip (arrangement) = index in time order | {"at": beat} | clip name.
Times: pass `beat` (quarter notes from song start, 0-based) or `bar` (1-based).

Bridge commands (args):
  ping | get_song | get_track(track, clips=True) | get_device(track, device)
  get_notes(track, clip)
  set_tempo(bpm) | create_track(kind=midi|audio, name, index=-1) | delete_track(track)
  create_return(name)  -- sends to it get the next send index
  set_track(track, name, volume_db, pan, mute, solo, arm, monitoring=in|auto|off)
  set_send(track, send, db)
  create_midi_clip(track, length, notes=[[pitch,start,dur,vel],...], name, beat|bar, loop)
  add_notes(track, clip, notes, replace=False)
  create_audio_clip(track, path, beat|bar, name, warp, gain_db, pitch, detune, warp_mode,
                    beats, length, envelopes)  -- beats pins the file to that many beats
                    (auto-warp guesses wrong); length loops it to that many beats
  set_clip(track, clip, name, muted, pitch, gain_db, looping, loop_start, loop_end, warping,
           start_marker, end_marker, detune, warp_mode)   -- markers move content, they do not
           resize the clip; detune is cents (-50..49) and, like warp_mode (beats|tones|texture|
           repitch|complex|complex_pro), needs warping on: measure a loop's tuning before use
  mute_clips_in_range(track, muted, start_bar, end_bar)
  duplicate_clip(track, clip, beat|bar) | delete_clip(track, clip)
  delete_clips_in_range(track, start_bar, end_bar)
  duplicate_range(track, start_bar, end_bar, dest_bar, active_only=True)
  fill_range(track, src_start_bar, src_end_bar, start_bar, end_bar)  -- loop a phrase, cut the overhang
  shift_clips(track, from_bar, bars)  -- move every clip from from_bar on by bars (negative = earlier);
           clear the destination first (cuts a section out of the arrangement)
  trim_clip(track, clip, end_bar|end_beat)  -- only where nothing lies after the cut
  create_*_clip(..., envelopes=[{param, device, points:[[beat_in_clip, v],...],
                                 unit:raw|db|display}])
  clip_envelope(track, slot, points, param="volume"|"pan"|
                "send:0"|<param>, device, unit)  -- Session clips only (Live API limit)
  browse(query, roots=[instruments,audio_effects,midi_effects,drums,sounds,plugins,
         user_library,samples,packs]) | load_device(track, path|query)
  set_param(track, device, param, value|display|db) | set_device_on(track, device, on)
  set_device_prop(track, device, prop, value)  -- EQ Eight global_mode (0 stereo, 1 L/R, 2 M/S), edit_mode, oversample
  copy_device(src_track, src_device, track, device)  -- clone a patch (params + Wavetable
           tables/voicing) onto a device of the same class, e.g. from a frozen track
  delete_device(track, device) | move_device(track, device, position)
  (device = index | name | "Name#k" for the k-th of several | unique fragment;
   set_param also takes item="Low Shelf" for list parameters)
  set_cue(name, beat|bar) | delete_cue(name|beat|bar) | clear_cues | transport(action=play|stop|continue|locate, beat|bar)
  set_loop(on, start_bar, end_bar)
  record_master(start_bar, end_bar, name) | record_status | record_abort
  grooves | set_groove(name, timing, random, velocity, quantization, groove_amount)
  apply_groove(track, groove=None, start_bar, end_bar)  -- pool grooves on arrangement clips
  warp_markers(track, clip) | set_warp_markers(track, clip, beats=16 | markers=[[beat, s],..])
           -- a loop of known length gets its exact tempo (auto-warp guessed 122.83 and 252)
  api_probe(expr)  -- eval a read-only expression against Live's API (exploration)
  track_routing(track) | set_track_output(track, dest="Drum Bus"|"Main"|"Sends Only")
  set_track_input(track, source="No Input"|<track>|"Ext. In")  -- a bus = audio track with
           monitoring "in", input "No Input" (else the mic feeds back) and members routed in
  device_inputs(track, device) | set_device_input(track, device, source="Kick", channel="Post Mixer")
           -- a real sidechain for Compressor / Gate / Auto Filter
    (audio clips must be warped; Beats mode suits drums)

Rendering needs an audio output device: if the interface is unplugged Live's engine
stops and renders fail with "playback never started" (Live's Log.txt then shows
"Audio In Out: Output Device: No Device"). Ask the user to reconnect or pick a device.

Rendering records the master in real time into a new track via Resampling, so a
render takes as long as the music it captures.

Composing: the music_* tools return notes ready for create_midi_clip. Keep new material
inside the song's scale (analyze_sample on its loops tells you the key and the swing),
land strong beats on chord tones, and give a call a response that echoes its rhythm.
Build arrangements left to right per track (fill_range cuts overhangs by overwriting).

A good track, step by step:
 1. genre_knowledge(genre): conventions plus numbers measured from the user's references
    (learn_genres(pasta) trains one profile per genre subfolder in the background).
 2. genre_plan_structure(genre, minutes): section lengths from the profile; then write
    the story (what enters, leaves, asks and answers in each section).
 3. Understand the material: analyze_sample / analyze_bassline on stems; get_notes on MIDI.
 4. Generate parts inside the song's vocabulary (music_*), place them, set locators.
 5. render_start + render_wait with the locator sections, then analyze_tension: check
    the energy curve and fix the arrangement first. The drop must *release*: louder than the last 4 bars
    before it (use the selected genre's measured tension profile) and bringing the kick back:
    a kick that returns in the build steals the drop. Keep risers under the section they
    announce. End the build on a dominant (V7sus4 stays inside a hexatonic minor).
 6. One groove: swing every 16th-based drum part with the same pool groove
    (apply_groove) at the swing the song's own tonal loops have (analyze_sample).
 7. compare_to_genre / mix_toward_genre on the render: broad EQ and limiter drive only;
    trust the selected references over rules of thumb.
 8. analyze_timbre on the render: kick, bass, hats, clap and breakdown against the
    references. Fix outliers at the source: find_samples ranks a library's one-shots by
    the genre's timbre and groove_loop places the winner with the references' per-16th
    feel (a pack loop carries its timbre and feel together, a one-shot neither); a
    construction kit starts from its own unity balance; never high-pass a bass or pad
    above its root (it moves the heard key); a round (sine) bass gets body from biased
    saturation (Dynamic
    Tube bias: symmetric clipping only adds odd harmonics); dry claps/hats get a short
    room; dark or wide pads get filter, EQ and width.
 9. validate_against_genre on the full render: every dimension at once.
    The ear goes further: listen(path) hears form, drum steps and swing, bassline, chords
    and layer balance; genre_principles(genre) says what the references share and why it
    works; compare_by_ear(render, genre) says what to change in producer terms.
    Before synthesizing a part, look in the user's sample packs: library_search (roles,
    key, tempo) and library_midi (royalty-free pack MIDI, transposed). Grooves: a reference's
    feel becomes a Groove Pool file with extract_groove.
10. Re-render and compare again. Measurements catch technical problems; they do not
    judge groove or taste: say so, and ask the user to listen.
"""

def _instructions():
    return INSTRUCTIONS + "\n\n" + knowledge.genre_context()


mcp = FastMCP("ableton-claude", instructions=_instructions())


def _refresh_genres():
    mcp._mcp_server.instructions = _instructions()

BRIEFS = os.path.join(os.path.dirname(__file__), "briefs")


def _brief(name: str) -> str:
    with open(os.path.join(BRIEFS, name + ".md"), encoding="utf-8") as f:
        brief = f.read()
    if name == "producer":
        brief = brief.replace("GENRE CONTEXT: {genre_context}", knowledge.genre_context())
    return brief


@mcp.tool()
def producer_brief() -> str:
    """The working brief for every production or mix task: how to inspect, diagnose,
    prioritize, change and verify a project, and the lessons learned on real tracks.
    Read it before changing anything."""
    return _brief("producer") + "\n\n" + _brief("lessons")


@mcp.prompt(name="produce", description="Take the open Live project to a club-ready release, by the producer brief.")
def produce_prompt(goal: str = "") -> str:
    task = goal or "Transform the open project into a professional, club-ready production."
    return producer_brief() + "\n\n## Task\n\n" + task


@mcp.resource("brief://producer", mime_type="text/markdown")
def producer_resource() -> str:
    return producer_brief()


@mcp.tool()
def ableton_status() -> dict:
    """Song overview: tempo, cues, every track (kind, volume, devices, clip counts, bar span),
    returns and master chain."""
    return client.call("get_song")


def _before(cmd, args):
    """State the bridge does not report itself, read before the change."""
    if cmd == "add_notes" and args.get("replace"):
        try:
            return {"notes": client.call("get_notes", {"track": args["track"],
                                                       "clip": args["clip"]})}
        except client.BridgeError:
            return None
    return None


def _journaled(cmd, args=None):
    """client.call that journals the change (see journal.py) so it can be reverted."""
    args = args or {}
    before = _before(cmd, args)
    result = client.call(cmd, args)
    rid = journal.record(cmd, args, result, before)
    if rid is not None and isinstance(result, dict):
        result = dict(result, change_id=rid)
    return result


@mcp.tool()
def ableton_command(cmd: str, args: dict | None = None) -> object:
    """Run one ClaudeBridge command. See the server instructions for the command list.
    Changes are journaled: the result carries a change_id for revert_changes."""
    return _journaled(cmd, args)


@mcp.tool()
def ableton_batch(commands: list[dict]) -> list:
    """Run many commands in one Live main-thread tick.
    commands: [{"cmd": "create_midi_clip", "args": {...}}, ...]. Each result has ok/result
    or ok/error; a failure does not stop the rest. Changes are journaled."""
    befores = [_before(c.get("cmd"), c.get("args") or {}) for c in commands]
    out = client.batch(commands)
    for c, b, r in zip(commands, befores, out):
        if r.get("ok"):
            rid = journal.record(c.get("cmd"), c.get("args") or {}, r.get("result"), b)
            if rid is not None:
                r["change_id"] = rid
    return out


@mcp.tool()
def change_log(last: int = 20) -> list:
    """The latest changes sent to Live in this session: command, arguments, the values they
    replaced, and whether revert_changes can put them back."""
    return journal.recent(last)


@mcp.tool()
def revert_changes(ids: list[int] | None = None, last: int = 1) -> dict:
    """Put back what the given changes (change_id) or the last N changes replaced, newest
    first. Deletes and range edits cannot be reverted here: use live_undo or the user's
    saved copy. Re-render afterwards to confirm the revert (the VERIFY step)."""
    done, skipped = [], []
    for rec in journal.find(ids, last):
        inv = journal.inverse(rec)
        if inv is None:
            skipped.append({"id": rec["id"], "cmd": rec["cmd"], "why": "not reversible here"})
            continue
        try:
            for cmd, args in inv:
                client.call(cmd, args)
        except client.BridgeError as e:
            skipped.append({"id": rec["id"], "cmd": rec["cmd"], "why": str(e).split("\n")[0]})
            continue
        journal.mark_reverted(rec)
        done.append({"id": rec["id"], "cmd": rec["cmd"], "restored": rec["before"]})
    return {"reverted": done, "skipped": skipped}


@mcp.tool()
def live_undo(steps: int = 1) -> dict:
    """Live's own undo (Cmd+Z), at most 50 steps. Live groups API changes into undo steps
    its own way, so prefer revert_changes and check the state after this."""
    return client.call("undo", {"steps": steps})


@mcp.tool()
def ableton_reload_bridge() -> dict:
    """Hot-reload the handlers module inside Live after it was reinstalled."""
    return client.call("reload")


@mcp.tool()
def render_start(start_bar: float, end_bar: float, name: str = "Claude Render") -> dict:
    """Start recording the master bus (bars [start_bar, end_bar)) into a new audio track.
    Runs in real time. Poll with render_wait."""
    return client.call("record_master",
                       {"start_bar": start_bar, "end_bar": end_bar, "name": name})


@mcp.tool()
def render_wait(timeout_s: float = 540, analyze: bool = True, target: str = "club",
                sections: list[dict] | None = None, delete_track: bool = True) -> dict:
    """Wait for the running render, then analyze the recorded WAV.
    sections: [{"name", "start_bar", "end_bar"}] relative to the render start (bar 1).
    delete_track removes the render track from the set (the WAV file stays on disk)."""
    deadline = time.time() + timeout_s
    st = client.call("record_status")
    while st["state"] in ("recording", "finalizing") and time.time() < deadline:
        time.sleep(1.0)
        st = client.call("record_status")
    if st["state"] != "done":
        return {"status": st}
    out = {"status": st}
    if analyze:
        tempo = client.call("get_song")["tempo"]
        out["analysis"] = analysis.analyze(st["file"], target=target, sections=sections,
                                           tempo=tempo)
    if delete_track:
        try:
            client.call("delete_track", {"track": st["name"]})
        except client.BridgeError as e:
            out["delete_error"] = str(e)
    return out


@mcp.tool()
def analyze_audio(path: str, target: str = "club", sections: list[dict] | None = None,
                  tempo: float | None = None) -> dict:
    """Measure a WAV/AIFF: LUFS, true peak, crest, band balance, tilt, stereo, and flags.
    target: club (-8 LUFS) | streaming (-14 LUFS)."""
    return analysis.analyze(path, target=target, sections=sections, tempo=tempo)


@mcp.tool()
def compare_to_reference(path: str, reference_path: str) -> dict:
    """Loudness-matched band-by-band comparison of a mix against a reference track."""
    return analysis.compare(path, reference_path)


@mcp.tool()
def music_chords(tonic: str, mode: str, numerals: list[str]) -> list[str]:
    """Roman numerals to chord symbols, e.g. G minor ['i7','III7','VII','IV7sus4'] ->
    ['Gm7','Bbmaj7','F','C7sus4']. Modes: minor, dorian, major, mixolydian, phrygian,
    lydian, harmonic_minor, melodic_minor."""
    sc = theory.Scale(tonic, mode)
    return [theory.roman(sc, n) for n in numerals]


@mcp.tool()
def music_progression(chords: list[str], bars_per_chord: float = 2, low: int = 53,
                      high: int = 77, voices: int = 4, anticipate: float = 0.5,
                      hold_last_bars: float = 0, velocity: int = 88) -> dict:
    """Voice-led chord part (common tones held, minimal movement, no low-register mud).
    anticipate = beats each change lands early (0.5 = the 'and' of 4).
    Returns notes for create_midi_clip and the voicings by name."""
    notes, vs = harmony.progression_notes(chords, bars_per_chord, low, high, voices,
                                          anticipate, velocity, hold_last_bars=hold_last_bars)
    return {"notes": notes, "length_beats": (len(chords) * bars_per_chord + hold_last_bars) * 4,
            "voicings": [[theory.note_name(p) for p in v] for v in vs],
            "movement_semitones": theory.movement(vs)}


@mcp.tool()
def music_call_and_response(chords: list[str], tonic: str = "G",
                            mode: str = "minor_hexatonic", phrase_bars: int = 2,
                            seed: int = 7, swing: float = 50.0,
                            call_range: list[int] = [62, 79],
                            response_range: list[int] = [55, 74]) -> dict:
    """A call (first half of `chords`, one chord per bar) that rises and ends on an open
    degree, and a response that echoes its rhythm and resolves to the tonic or third.
    Each part's notes start at 0: put the response `phrase_bars` bars after the call.
    Keep the seed to repeat the motif across the song; change chords to re-harmonise."""
    out = melody.call_and_response(tonic, mode, chords, phrase_bars, tuple(call_range),
                                   tuple(response_range), seed)
    if swing != 50.0:
        out["call"] = harmony.swing(out["call"], swing)
        out["response"] = harmony.swing(out["response"], swing)
    sc = theory.Scale(tonic, mode)
    out["audit"] = (melody.audit(out["call"], sc, chords[:phrase_bars]) +
                    melody.audit(out["response"], sc, chords[phrase_bars:]))
    return out


@mcp.tool()
def music_drum_pattern(bars: int = 1, swing: float = 56.0, parts: list[str] | None = None,
                       seed: int = 0, style: str = "deep_house") -> dict:
    """Deep_house or tech_house starting kit on Live's Drum Rack layout (kick 36, clap 39,
    hats 42/46, shaker 70, rim 37). Swing/accent/humanisation; measured reference grooves
    take priority. Select style explicitly for tech house."""
    return groove.pattern(style, bars, swing, seed=seed, parts=parts)


@mcp.tool()
def music_drum_kit(name: str = "let_the_rhythm", bars: int = 8, parts: list[str] | None = None,
                   notes: bool = False, pitch_map: dict | None = None) -> dict:
    """Drum kits learned from the producer's finished tracks (kits/*.json): per part the
    role, why it works, step pattern per bar, micro-timing (ms), velocity range, sample,
    device chain, fader, pan, drumverb send and where it plays in the arrangement, plus
    the groove-pool setting and bus chains. notes=True adds each part's exact loop tiled
    over `bars` for create_midi_clip (pitch_map {part: pitch} to play on other pads; a
    Simpler plays at 60). Use it to build drums in the producer's own style."""
    from .music import kits
    if not name:
        return {"kits": kits.names()}
    kit = kits.load(name)
    out = kits.summary(kit)
    if parts:
        out["parts"] = {k: v for k, v in out["parts"].items() if k in parts}
    if notes:
        out["notes"] = kits.pattern(name, bars, parts, pitch_map)
    return out


@mcp.tool()
def music_pocket_sketch(style: str = "tech_house", tonic: str = "G", mode: str = "minor",
                        bars: int = 8, bpm: float = 126., swing: float = 56., seed: int = 7,
                        drum_layers: int = 4, clap_delay_ms: float = 5.,
                        percussion_delay_ms: float = 0.) -> dict:
    """Coordinated drums+bass, stable anchors, shared swing, 3–5 drum voices, purposeful
    rests. Returns main/stripped alternatives for A/B, no Live edits. Notes use default
    Drum Rack pitches; inspect pads first. Timing already baked in: avoid double swing.
    $result field='main.kick' or 'stripped.bass' selects a part. Recipe, not trend evidence.
    bars: even 2–64; bpm: 60–200; swing: 50–66; delays in ms at supplied tempo."""
    return pocket.sketch(style, tonic, mode, bars, bpm, swing, seed, drum_layers,
                         clap_delay_ms, percussion_delay_ms)


@mcp.tool()
def music_club_motif(part: str = "bass", tonic: str = "G", mode: str = "minor",
                     bars: int = 8, swing: float = 54., seed: int = 7,
                     density: str = "normal", articulation: str = "short",
                     development: str = "restrained", octave: int | None = None) -> dict:
    """Tech-house bass/hook in 4/4: repeated two-bar identity, swing, final turnaround.
    density: sparse/normal/busy; articulation: short/sustained; development:
    restrained/evolving. octave defaults to 1 for bass, 4 for hook (C4=MIDI60).
    Same seed relates bass/hook. Gates leave kick room; audible release/filter/weight
    need sound-design and audition. Returns notes for create_midi_clip; no Live edits."""
    return club.motif(part, tonic, mode, bars, swing, seed, density, articulation, development, octave)


@mcp.tool()
def music_build_roll(bars: int = 8, pitch: int = 39) -> list:
    """Build-up roll: quarters, 8ths, 16ths, 32nds in the last bar, rising velocity, last
    beat empty so the drop lands on silence. pitch 60 plays a Simpler at its root."""
    return groove.build_roll(bars=bars, pitch=pitch)


@mcp.tool()
def analyze_sample(path: str, tempo: float | None = None) -> dict:
    """What a sample is: key (with confidence), BPM, bars, loop length, swing %, role
    guess (kick/bass/hats/tonal/fx) and its strongest pitch classes."""
    return samples.analyze_sample(path, tempo=tempo)


@mcp.tool()
def analyze_bassline(path: str, tempo: float, bars: int = 8) -> list:
    """Dominant low note per beat (30-300 Hz) of a bass or 808 loop, as note names."""
    mono, sr = samples.load_mono(path, max_seconds=bars * 4 * 60.0 / tempo + 2)
    return [theory.note_name(n) if n else None for n in samples.bass_notes(mono, sr, tempo,
                                                                           max_bars=bars)]


@mcp.tool()
def learn_genres(pasta: str) -> dict:
    """Train a genre from each immediate subfolder of pasta (folder path).
    Audio inside each genre is scanned recursively, without the study's 12-track cap.
    Measures profiles, fingerprints, timbre and tension; hears references if the ear is
    installed. Runs in the background with a resumable content cache. Audio stays in
    place; profiles, briefs and caches go in ~/Music/Ableton Claude/.
    Use learn_genres_status(pasta) for progress. Do not render during training."""
    try:
        if client.call("record_status").get("state") in ("recording", "finalizing"):
            return {"error": "a render is running: learn genres after it (renders are real time)"}
    except client.BridgeError:
        pass
    try:
        return genres.start(pasta, on_done=_refresh_genres)
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
def learn_genres_status(pasta: str) -> dict:
    """Progress and per-genre results of learn_genres; includes the updated genre context."""
    return genres.status(pasta)


@mcp.tool()
def list_genres() -> list[dict]:
    """The user's trained genre names, reference counts and profile paths."""
    return knowledge.trained_genres()


@mcp.tool()
def genre_knowledge(genre: str) -> dict:
    """What a genre is: curated conventions (tempo, harmony and progressions, drums, bass,
    arrangement moves, palette, mix) plus, when a profile was built from the user's own
    references, the measured numbers (BPM, swing, keys, loudness, spectrum, structure)."""
    return knowledge.get(genre)


@mcp.tool()
def genre_plan_structure(genre: str, minutes: float, bpm: float | None = None) -> dict:
    """Section plan for a new track in a genre (intro, groove, breakdown, build, drop,
    outro), sized from the measured reference profile when there is one."""
    return knowledge.plan_structure(genre, minutes, bpm)


@mcp.tool()
def analyze_reference(path: str, bpm: float | None = None) -> dict:
    """Measure one reference track: loudness, 1/3-octave shape, stereo, BPM, key, swing,
    and its structure (intro, breaks, drop, outro in bars). Takes ~10-30 s per track."""
    return references.analyze_reference(path, bpm)


@mcp.tool()
def compare_to_genre(path: str, genre: str) -> dict:
    """Hold a mix against a genre profile: loudness, band shares and 1/3-octave bands that
    fall outside the references' middle half, with the move (dB) toward their median.
    Build the profile first with learn_genres(pasta), one subfolder per genre."""
    prof = knowledge.load_profile(genre)
    if not prof:
        return {"error": "no profile for %r; use learn_genres(pasta), one subfolder per genre"
                % genre}
    return references.compare_to_profile(path, prof)


@mcp.tool()
def mix_toward_genre(path: str, genre: str, apply: bool = False,
                     ceiling_db: float = -1.5) -> dict:
    """Compare a rendered mix with a genre profile. With apply=True, also move the Live
    master toward it: an EQ Eight before the bus compressor with at most four broad,
    capped bands, limiter drive toward the genre's median loudness (never below its
    lower-quartile crest), and the limiter ceiling. Re-render to check the result."""
    return mixing.toward_profile(path, genre, apply=apply, ceiling=ceiling_db, call=_journaled)


@mcp.tool()
def validate_against_genre(path: str, genre: str) -> dict:
    """The whole check in one call: structure, loudness, band balance, groove/harmony/
    timbre fingerprint (incl. swing measured against the hats' own on-beats), element
    timbre and tension/release of a render, each against the genre references' middle
    half with a verdict, plus how many measures sit inside it. Use it after every full
    render; fix the 'low'/'high' rows that are not deliberate choices."""
    return validate.report(path, genre, echo=lambda *a: None)


@mcp.tool()
def analyze_tension(path: str, genre: str, bpm: float | None = None) -> dict:
    """Tension and release around the main break of a render, against the genre's
    references: break depth, how far kick and bass drop out, the build's ramp, the
    pre-drop dip, and the drop's jump in loudness, kick and bass. Loudness alone does
    not establish release; use production_review for all drops and independent cues.
    Needs scripts/build_tension.py '<genre>' once (reads the cached references)."""
    a = references.analyze_reference(path, bpm=bpm)
    ours = tension.for_track(a["bars_matrix"], a["segments"])
    if ours is None:
        return {"error": "no break followed by a full section found", "segments": a["segments"]}
    prof = (knowledge.load_profile(genre) or {}).get("tension")
    if not prof:
        return {"tension": ours, "error": "no tension profile; run scripts/build_tension.py '%s'" % genre}
    return {"break_bars": ours["break_bars"], "drop_bar": ours["drop_bar"],
            "compare": tension.compare(ours, prof)}


@mcp.tool()
def analyze_timbre(path: str, genre: str, bpm: float | None = None) -> dict:
    """Element timbre of a rendered mix against the genre's references: kick pitch and
    length, kick-vs-bass weight, bass harmonics, hat brightness/length/level, clap presence
    and tail, breakdown brightness/warmth/width. Each gets the references' middle half and
    a verdict (low/ok/high). Needs scripts/build_timbre.py <folder> <genre> once."""
    a = references.analyze_reference(path, bpm=bpm)
    ours = timbre.timbre_file(path, a["bpm"], a["first_beat_s"], a["segments"], a["bars_matrix"])
    prof = knowledge.load_profile(genre) or {}
    if not prof.get("timbre"):
        return {"timbre": ours,
                "error": "no timbre profile; run scripts/build_timbre.py <folder> '%s'" % genre}
    return {"compare": timbre.compare(ours, prof["timbre"]), "segments": a["segments"]}


@mcp.tool()
def find_samples(folder: str, genre: str, element: str = "hat", limit: int = 10) -> list:
    """Measure every one-shot under `folder` (Live's Core Library one-shots, a pack, the
    user's sample folders; cached after the first run) and rank them by closeness to the
    genre's measured timbre for `element`: hat (brightness + length), clap (tail) or kick
    (body pitch + length). Load the winner with browse + load_device."""
    import os
    prof = knowledge.load_profile(genre) or {}
    if not prof.get("timbre"):
        return [{"error": "no timbre profile; run scripts/build_timbre.py <folder> '%s'" % genre}]
    cache = os.path.normpath(os.path.join(knowledge.KNOWLEDGE_DIR, "..", "samples_cache.json"))
    rows = timbre.measure_folder(folder, cache_path=cache)
    return timbre.find_samples(rows, prof["timbre"], element)[:limit]


@mcp.tool()
def groove_loop(shots: dict, out: str, bpm: float, role: str = "hats", genre: str = "deep house",
                bars: int = 4, steps: list | None = None, seed: int = 0,
                swing_pct: float | None = None) -> dict:
    """Build a WAV loop from one-shots placed with the genre's measured groove for `role`
    (hats, clap or kick): per-16th micro-timing, accents and timing variation pooled from
    the references' ear reports (genre_principles). `shots` maps a step 0-15 or "default"
    to a file (pick them with find_samples: e.g. an open hat on the off-beat 8ths 2/6/10/14,
    a closed one elsewhere); `steps` limits the steps played; `swing_pct` re-centres the
    off-beat 16ths (the median template sits flatter than most references: compare with
    the genre's swing_self_pct). Place the WAV with create_audio_clip(warp=False): it is
    exactly `bars` long at `bpm`."""
    from .ear import why
    prof = knowledge.load_profile(genre) or {}
    tmpl = ((prof.get("ear") or {}).get("drums", {}).get(role) or {}).get("template")
    if not tmpl:
        tmpl = why.groove_template(why.load_reports(), role)
    if not tmpl or not tmpl.get("n"):
        return {"error": "no %s groove measured; run listen_folder.py and build_principles.py" % role}
    y = loops.from_template(shots, tmpl, bpm, bars=bars, steps=steps, seed=seed, swing_pct=swing_pct)
    loops.write(out, y)
    return {"file": out, "bars": bars, "bpm": bpm, "from_references": tmpl["n"],
            "steps": [(s["step"], s["offset_ms"], s["accent_db"]) for s in tmpl["steps"]
                      if s["offset_ms"] is not None and (steps is None or s["step"] in steps)]}


# ---------------------------------------------------------------------------- the ear

def _key_arg(key):
    """'G minor' / 'Gm' / 'F# major' -> (pc, mode) or (None, None)."""
    if not key:
        return None, None
    pc, mode = library._key(key.replace(" ", "_"))
    return pc, mode


def _slim(rep):
    from .ear import listen as EL
    d = rep["drums"]
    return {"summary": rep["summary"], "file": rep["file"], "bpm": rep["grid"]["bpm"], "key": rep["key"],
            "bars": rep["grid"]["n_bars"], "form": EL.form(rep["arrangement"]["sections"]),
            "sections": rep["arrangement"]["sections"], "entries": rep["arrangement"]["first_bar"],
            "drums": {"main_patterns": d.get("main_patterns"),
                      "hats": {k: d["hats"].get(k) for k in ("swing_pct", "late_ms_offbeat_vs_onbeat", "timing_spread_ms")},
                      "by_section": d.get("by_section")},
            "bass": {k: v for k, v in rep["bass"].items() if k != "notes"},
            "harmony": {k: rep["harmony"].get(k) for k in ("key", "key_confidence", "loops", "changes_per_8_bars",
                                                            "qualities", "bars")},
            "mix": rep["mix"], "perception": {k: v for k, v in rep.get("perception", {}).items() if k != "bars"},
            "reliability": rep.get("reliability", EL.reliability(rep)), "id": rep["id"]}


@mcp.tool()
def listen(path: str, bpm: float | None = None) -> dict:
    """Hear a track like a producer: tempo and bar grid, key, form (which elements play in
    each section and when each enters), drum patterns on the 16-step grid with swing,
    microtiming and accents, the bassline (register, degrees, typical bar, how it dodges
    the kick), chords with Roman numerals and harmonic rhythm, and how loud and wide each
    layer sits against the drums. Stems via Demucs, beats via Beat This; ~20 s per file on
    first listen, cached after. The heard parts are saved as MIDI (see heard_midi)."""
    from .ear import listen as EL
    return _slim(EL.listen(path, bpm_hint=bpm))


@mcp.tool()
def production_intent(prompt: str, genre: str | None = None) -> dict:
    """Translate explicit PT/EN feeling/bass requests into independent hypotheses:
    amount, harmonic openness, density, articulation and stereo width. Includes a
    deliberate composition/audition process. Unknowns remain unknown; no Live edits,
    no extra model call and no claim to recognise listener emotion."""
    from . import intent
    return intent.plan(prompt, genre)


@mcp.tool()
def production_review(path: str, prompt: str = "", genre: str | None = None,
                      reference_path: str | None = None, bpm: float | None = None,
                      start_bar: int | None = None, end_bar: int | None = None) -> dict:
    """Hear a render's independent bass characteristics per section and every detected
    break/drop: weight, harmonic openness, mono loss, rhythmic occupancy, transients,
    low-end/pulse return and LUFS contrast. Optional direct reference takes priority
    over learned genre section distributions. Provides evidence/listening hypotheses,
    never an emotion/professional score. Optional start_bar/end_bar focus on whole
    intersecting sections; full-song responses explicitly disclose omitted rows.
    No Live edits; heavy first listen, cached later."""
    from . import production_review as review
    from .ear import listen as EL, perception
    rep = EL.listen(path, bpm_hint=bpm)
    target = None
    source = {"kind": "none", "note": "No compatible reference comparison available."}
    if reference_path:
        ref = EL.listen(reference_path)
        target = perception.profile([ref])
        source = {"kind": "direct_reference", "file": ref["file"], "n_tracks": 1}
    elif genre:
        prof = knowledge.load_profile(genre) or {}
        target = (prof.get("ear") or {}).get("perception")
        source = {"kind": "genre", "genre": genre, "compatible_tracks": (target or {}).get("n_tracks", 0)}
    out = review.review(rep, prompt, target, start_bar, end_bar)
    out["reference_source"] = source
    # Keep the evidence readable in desktop tool context; callers can narrow the range.
    out['omissions'] = {}
    for key, limit in (('findings', 3), ('sections', 6), ('transitions', 4)):
        values = out[key]
        out['omissions'][key] = {'total': len(values), 'omitted': max(0, len(values) - limit)}
        out[key] = values[:limit]
    rows = out['section_comparison']['rows']
    out['omissions']['comparison_rows'] = {'total': len(rows), 'omitted': max(0, len(rows) - 12)}
    out['section_comparison']['rows'] = rows[:12]
    out['narrow_result'] = 'Use start_bar/end_bar around a reported drop/section for omitted evidence; cached audio analysis is reused.'
    return out


@mcp.tool()
def remix_plan(path: str, genre: str = "tech house", target_bpm: float | None = None,
               target_tonic: str | None = None, source_bpm: float | None = None) -> dict:
    """Analyze an original and plan a remix: source grid/key reliability, hook activity
    candidates in bars/seconds, tempo ratio, safe transpose suggestion and warp/mix checks.
    Target BPM comes from the genre profile or declared conventions unless provided.
    Does not export stems, import audio or edit Live. Audition candidates and artifacts."""
    from . import remix
    from .ear import listen as EL
    context = knowledge.get(genre)
    if target_bpm is None:
        measured = context.get("measured") or {}
        target_bpm = (measured.get("bpm") or {}).get("median")
        if target_bpm is None:
            bpms = (context.get("conventions") or {}).get("bpm")
            if not bpms:
                raise ValueError("No measured/conventional tempo for genre; provide target_bpm")
            target_bpm = sum(bpms) / len(bpms)
            tempo_basis = "genre convention; creative starting point"
        else:
            tempo_basis = "measured reference median"
    else:
        tempo_basis = "explicit target_bpm"
    out = remix.plan(EL.listen(path, bpm_hint=source_bpm), genre, target_bpm, target_tonic)
    out["target"]["tempo_basis"] = tempo_basis
    return out


_STUDIES = {}


def _live_reference_files():
    """Audio files of the clips on the set's reference tracks (name contains "REF")."""
    files = []
    for t in client.call("get_song")["tracks"]:
        if "REF" not in t["name"].upper() or t["kind"] != "audio":
            continue
        for c in client.call("get_track", {"track": t["i"]}).get("clips", []):
            if c.get("file") and c["file"] not in files:
                files.append(c["file"])
    return files


@mcp.tool()
def study_references(name: str, paths: list[str] | None = None, folder: str | None = None,
                     from_live: bool = False) -> dict:
    """Study a handful of reference tracks (about 5) for the track being made: measured
    and heard, then saved as a profile named `name` that every genre tool accepts, plus a
    study brief (study_status / reference_study). Give file paths, a folder, or
    from_live=True for the audio on the set's tracks named "REF". Files dropped in the
    study's folder (returned) are included. Runs in the background, a few minutes for 5
    tracks; do not start a render meanwhile."""
    from . import study
    job = _STUDIES.get(name)
    if job and job["state"] == "running":
        return {"state": "running", "log": job["log"][-5:]}
    try:
        if client.call("record_status").get("state") in ("recording", "finalizing"):
            return {"error": "a render is running: study after it (renders are real time)"}
    except client.BridgeError:
        pass  # Live is not needed to study files
    if from_live:
        paths = list(paths or []) + _live_reference_files()
    folder_ = study.collect(name, paths, folder)
    job = {"state": "running", "log": [], "started": time.time(), "folder": folder_}
    _STUDIES[name] = job

    def work():
        try:
            job["result"] = study.run(name, folder_, log=job["log"].append)
            _refresh_genres()
            job["state"] = "done"
        except Exception as e:
            job["state"], job["error"] = "failed", "%s: %s" % (type(e).__name__, e)

    import threading
    threading.Thread(target=work, name="study:" + name, daemon=True).start()
    return {"state": "running", "folder": folder_,
            "files": [os.path.basename(p) for p in study.audio_files(folder_)],
            "next": "call study_status('%s') every minute or so" % name}


@mcp.tool()
def study_status(name: str, wait_s: float = 50) -> dict:
    """Progress of study_references; waits up to wait_s for it to finish. When done,
    returns the study brief."""
    from . import study
    job = _STUDIES.get(name)
    if not job:
        brief = study.load_brief(name)
        return {"state": "done", "study": brief} if brief else {"error": "no study %r" % name}
    end = time.time() + max(0.0, min(wait_s, 55.0))
    while job["state"] == "running" and time.time() < end:
        time.sleep(1.0)
    out = {"state": job["state"], "elapsed_s": round(time.time() - job["started"]),
           "log": job["log"][-6:]}
    if job["state"] == "done":
        out["study"] = job["result"]
    if job["state"] == "failed":
        out["error"] = job["error"]
    return out


@mcp.tool()
def reference_study(name: str | None = None) -> object:
    """A finished study brief by name; without a name, the list of studies."""
    from . import study
    if name:
        return study.load_brief(name) or {"error": "no study %r" % name}
    if not os.path.isdir(study.STUDIES_DIR):
        return []
    return sorted(d for d in os.listdir(study.STUDIES_DIR)
                  if os.path.exists(os.path.join(study.STUDIES_DIR, d, "study.json")))


@mcp.tool()
def genre_principles(genre: str) -> dict:
    """What a genre's references share, measured by ear, each habit with the reason it
    works: drum patterns per step and swing, how the bass takes turns with the kick,
    degrees, harmonic rhythm and chord qualities, what breaks keep, when elements enter,
    and each layer's level against the drums. Build with scripts/build_principles.py."""
    prof = knowledge.load_profile(genre) or {}
    if not prof.get("ear"):
        return {"error": "no ear principles for %r: run scripts/listen_folder.py <folder> then "
                         "scripts/build_principles.py '%s'" % (genre, genre)}
    return prof["ear"]


@mcp.tool()
def compare_by_ear(path: str, genre: str, bpm: float | None = None) -> dict:
    """Listen to a render and say, in producer terms, where it leaves the genre's habits
    (bass colliding with the kick, swing, chord motion, break length, drum steps, layer
    balance) and which way to move."""
    from .ear import listen as EL, perception, why
    prof = knowledge.load_profile(genre) or {}
    if not prof.get("ear"):
        return {"error": "no ear principles for %r" % genre}
    rep = EL.listen(path, bpm_hint=bpm)
    return {"summary": rep["summary"], "reliability": rep.get("reliability", EL.reliability(rep)),
            "differences": why.compare(rep, prof["ear"]),
            "perception": perception.compare(rep.get("perception", {"sections": []}), prof["ear"].get("perception", {}))}


@mcp.tool()
def extract_groove(path: str, name: str | None = None, part: str = "hats") -> dict:
    """Turn a track's feel into a Live groove file: one bar of 16ths placed where its hits
    land (median microtiming per step) with its accents, written to the User Library
    (Grooves/Claude). Load it with load_device(track, path=<browser_path>) to put it in
    the Groove Pool, then apply_groove to clips. part: hats | clap | kick."""
    from .ear import groove_file, listen as EL
    rep = EL.listen(path)
    tmpl = rep["drums"].get(part, {}).get("template")
    if not tmpl:
        return {"error": "no %s groove heard in %s" % (part, rep["file"])}
    nm = name or "%s %s groove" % (os.path.splitext(rep["file"])[0][:40], part)
    out = groove_file.write(nm, groove_file.notes_from_template(tmpl, rep["grid"]["period"]))
    return {"file": out, "browser_path": "user_library/Grooves/Claude/" + os.path.basename(out),
            "swing_pct": rep["drums"][part].get("swing_pct"),
            "offsets_ms": [t["offset_ms"] for t in tmpl], "accents_db": [t["accent_db"] for t in tmpl]}


@mcp.tool()
def heard_midi(path: str, part: str, start_bar: int = 1, bars: int = 8) -> list:
    """Notes the ear heard in a track (part: bass | chords | drums) from start_bar for
    `bars` bars, re-based to 0 and ready for create_midi_clip. For studying and re-voicing
    a groove or progression; do not reuse a commercial track's melody or bassline as is."""
    from .ear import listen as EL, midi
    rep = EL.listen(path)
    parts = dict(midi.read_notes(os.path.join(EL.CACHE_DIR, rep["id"], "heard.mid")))
    key = {"bass": "bass (heard)", "chords": "chords (heard)", "drums": "drums (heard)"}[part]
    a, b = (start_bar - 1) * 4.0, (start_bar - 1 + bars) * 4.0
    return [[p, round(t - a, 4), d, v] for p, t, d, v in parts.get(key, []) if a <= t < b]


# ------------------------------------------------------------------------- the library

@mcp.tool()
def library_index(roots: list[str] | None = None) -> dict:
    """Index the user's sample folders (role, loop or one-shot, tempo and key from the
    names, length). Without roots, re-index the last folders. Fast: names and headers only."""
    if not roots:
        idx = library.load_index()
        roots = idx["roots"] if idx else []
    if not roots:
        return {"error": "give the sample folders to index"}
    idx = library.build_index(roots)
    return {"n": idx["n"], "roots": roots, "by_role": library.summary(idx)}


@mcp.tool()
def library_search(role: str | None = None, text: str | None = None, key: str | None = None,
                   bpm: float | None = None, loop: bool | None = None, genre: str | None = None,
                   limit: int = 15) -> list:
    """Find ready material in the user's sample packs before synthesizing it. role: kick,
    clap, snare, hat, shaker, perc, ride, crash, drum_loop, top_loop, bass, chord, pad, lead,
    vocal, fx, midi. key e.g. 'G minor' (tonal material must match or be relative/a fifth
    away); bpm ranks loops by tempo; genre e.g. 'deep house|house'. Place audio with
    create_audio_clip(track, path, bar); read MIDI with library_midi."""
    pc, mode = _key_arg(key)
    rows = library.search(role=role, text=text, key_pc=pc, mode=mode, bpm=bpm, loop=loop,
                          genre=genre, limit=limit)
    return [{k: r.get(k) for k in ("path", "role", "midi_role", "loop", "bpm", "key_pc", "mode", "dur_s", "score")}
            for r in rows]


@mcp.tool()
def library_midi(path: str, to_key: str | None = None) -> list:
    """Notes of a sample-pack MIDI file (royalty-free material), optionally transposed from
    the key in its file name to `to_key` (e.g. 'G minor'), ready for create_midi_clip:
    [[pitch, start_beat, dur_beats, velocity]] per track."""
    from .ear import midi
    tracks = midi.read_notes(path)
    shift = 0
    if to_key:
        src_pc, _ = library._key(os.path.splitext(os.path.basename(path))[0])
        dst_pc, _ = _key_arg(to_key)
        if src_pc is not None and dst_pc is not None:
            shift = (dst_pc - src_pc) % 12
            shift = shift - 12 if shift > 6 else shift
    return [{"track": name, "transposed": shift,
             "notes": [[p + shift, round(t, 4), round(d, 4), v] for p, t, d, v in notes]}
            for name, notes in tracks]


def main():
    # stdio for desktop clients (Claude, Cursor, LM Studio); --http serves Streamable HTTP
    # on 127.0.0.1:8000/mcp for clients that connect by URL (ChatGPT, through a tunnel).
    import sys
    if "--http" in sys.argv:
        mcp.settings.port = int(os.environ.get("ABLETON_MCP_PORT", "8000"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
