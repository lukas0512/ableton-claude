"""MCP server exposing Ableton Live (via ClaudeBridge) and audio analysis to Claude."""
import time

from mcp.server.fastmcp import FastMCP

from . import analysis, client, knowledge, mixing, references, timbre
from .music import groove, harmony, melody, samples, theory

INSTRUCTIONS = """\
Drives Ableton Live through the ClaudeBridge Remote Script (127.0.0.1:9878).

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
  create_audio_clip(track, path, beat|bar, name, warp, gain_db, pitch)
  set_clip(track, clip, name, muted, pitch, gain_db, looping, loop_start, loop_end, warping,
           start_marker, end_marker)   -- markers move content, they do not resize the clip
  mute_clips_in_range(track, muted, start_bar, end_bar)
  duplicate_clip(track, clip, beat|bar) | delete_clip(track, clip)
  delete_clips_in_range(track, start_bar, end_bar)
  duplicate_range(track, start_bar, end_bar, dest_bar, active_only=True)
  fill_range(track, src_start_bar, src_end_bar, start_bar, end_bar)  -- loop a phrase, cut the overhang
  trim_clip(track, clip, end_bar|end_beat)  -- only where nothing lies after the cut
  create_*_clip(..., envelopes=[{param, device, points:[[beat_in_clip, v],...],
                                 unit:raw|db|display}])
  clip_envelope(track, slot, points, param="volume"|"pan"|
                "send:0"|<param>, device, unit)  -- Session clips only (Live API limit)
  browse(query, roots=[instruments,audio_effects,midi_effects,drums,sounds,plugins,
         user_library,samples,packs]) | load_device(track, path|query)
  set_param(track, device, param, value|display|db) | set_device_on(track, device, on)
  delete_device(track, device) | move_device(track, device, position)
  (device = index | name | "Name#k" for the k-th of several | unique fragment;
   set_param also takes item="Low Shelf" for list parameters)
  set_cue(name, beat|bar) | delete_cue(name|beat|bar) | clear_cues | transport(action=play|stop|continue|locate, beat|bar)
  set_loop(on, start_bar, end_bar)
  record_master(start_bar, end_bar, name) | record_status | record_abort
  grooves | set_groove(name, timing, random, velocity, quantization, groove_amount)
  apply_groove(track, groove=None, start_bar, end_bar)  -- pool grooves on arrangement clips
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
    (a profile exists when the user has run scripts/build_profile.py on a folder).
 2. genre_plan_structure(genre, minutes): section lengths from the profile; then write
    the story (what enters, leaves, asks and answers in each section).
 3. Understand the material: analyze_sample / analyze_bassline on stems; get_notes on MIDI.
 4. Generate parts inside the song's vocabulary (music_*), place them, set locators.
 5. render_start + render_wait with the locator sections: check the energy curve and
    fix the arrangement first. The drop must *release*: louder than the last 4 bars
    before it (deep house references: +3.7 LU median) and bringing the kick back (+26 dB):
    a kick that returns in the build steals the drop. Keep risers under the section they
    announce. End the build on a dominant (V7sus4 stays inside a hexatonic minor).
 6. One groove: swing every 16th-based drum part with the same pool groove
    (apply_groove) at the swing the song's own tonal loops have (analyze_sample).
 7. compare_to_genre / mix_toward_genre on the render: broad EQ and limiter drive only;
    trust the references over rules of thumb (deep house keeps ~90 % below 250 Hz).
 8. analyze_timbre on the render: kick, bass, hats, clap and breakdown against the
    references. Fix outliers at the source: find_samples ranks a library's one-shots by
    the genre's timbre; a round (sine) bass gets body from biased saturation (Dynamic
    Tube bias: symmetric clipping only adds odd harmonics); dry claps/hats get a short
    room; dark or wide pads get filter, EQ and width.
 9. Re-render and compare again. Measurements catch technical problems; they do not
    judge groove or taste: say so, and ask the user to listen.
"""

mcp = FastMCP("ableton-claude", instructions=INSTRUCTIONS)


@mcp.tool()
def ableton_status() -> dict:
    """Song overview: tempo, cues, every track (kind, volume, devices, clip counts, bar span),
    returns and master chain."""
    return client.call("get_song")


@mcp.tool()
def ableton_command(cmd: str, args: dict | None = None) -> object:
    """Run one ClaudeBridge command. See the server instructions for the command list."""
    return client.call(cmd, args or {})


@mcp.tool()
def ableton_batch(commands: list[dict]) -> list:
    """Run many commands in one Live main-thread tick.
    commands: [{"cmd": "create_midi_clip", "args": {...}}, ...]. Each result has ok/result
    or ok/error; a failure does not stop the rest."""
    return client.batch(commands)


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
                       seed: int = 0) -> dict:
    """Deep house kit pattern on Live's Drum Rack layout (kick 36, clap 39, closed hat 42,
    open hat 46, shaker 70, rim 37), with swing, accents and humanisation."""
    return groove.pattern("deep_house", bars, swing, seed=seed, parts=parts)


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
    Build the profile first with scripts/build_profile.py <folder> <genre>."""
    prof = knowledge.load_profile(genre)
    if not prof:
        return {"error": "no profile for %r; run scripts/build_profile.py <folder> '%s'"
                % (genre, genre)}
    return references.compare_to_profile(path, prof)


@mcp.tool()
def mix_toward_genre(path: str, genre: str, apply: bool = False,
                     ceiling_db: float = -1.5) -> dict:
    """Compare a rendered mix with a genre profile. With apply=True, also move the Live
    master toward it: an EQ Eight before the bus compressor with at most four broad,
    capped bands, limiter drive toward the genre's median loudness (never below its
    lower-quartile crest), and the limiter ceiling. Re-render to check the result."""
    return mixing.toward_profile(path, genre, apply=apply, ceiling=ceiling_db)


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


def main():
    mcp.run()


if __name__ == "__main__":
    main()
