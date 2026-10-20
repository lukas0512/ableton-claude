"""From The Streets: a 122 BPM house mashup of B-Legit "City 2 City" (the base) and UGK
"Murder" (the main break), built on the producer's Let The Rhythm drums.

Both originals read E minor (City 2 City 92.0 BPM, Murder 86.0 BPM). Vocals come from
htdemucs two-stem separation; phrases are cut bar-aligned at source tempo and warped in
Live (Complex Pro), so the rap keeps its pitch and runs 1.33x / 1.42x faster.
Repeated-vocal analysis: City 2 City hook at source bars 20-27 (again 40-47, 56-63);
Murder hook at bars 41-48 (also the intro). Audition: bar offsets can be one off.

Stages, in order: `python build_from_the_streets.py phrases|tracks|clips|mix|cues`.
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))
from ableton_claude import client, server, stem_remix  # noqa: E402
from ableton_claude.music import kits  # noqa: E402

BPM = 122.0
END = 145                                  # first bar after the song
ROOT = Path("/Users/lukasgalhardo/Desktop/TRACKS 2027/From the streets")
STEMS = ROOT / "stems/htdemucs"
OUT = ROOT / "Remix 122"
KIT = "user_library/Samples/Claude/Nobody Kit/"
LOG = []

SOURCES = {
    "CITY": dict(stem=STEMS / "02. B-Legit - City 2 City (Original Mix)/vocals.wav",
                 bpm=92.017, downbeat=0.2322),
    "MURDER": dict(stem=STEMS / "03 - UGK (Underground Kingz) - Murder/vocals.wav",
                   bpm=86.015, downbeat=0.8976),
}
# name: (source, first source bar, bars)
PHRASES = {
    "City verse 1": ("CITY", 9, 8), "City hook A": ("CITY", 20, 8),
    "City verse 2": ("CITY", 28, 8), "City hook B": ("CITY", 40, 8),
    "City hook C": ("CITY", 56, 8), "City verse 3": ("CITY", 64, 8),
    "City call": ("CITY", 20, 1),
    "City hook B half": ("CITY", 40, 4), "City hook B tail": ("CITY", 44, 4),
    "City verse 2 half": ("CITY", 28, 4), "City verse 3 half": ("CITY", 64, 4),
    "City trade 1": ("CITY", 40, 2), "City trade 2": ("CITY", 42, 2),
    "Murder trade 1": ("MURDER", 9, 2), "Murder trade 2": ("MURDER", 11, 2),
    "Murder verse 1": ("MURDER", 9, 8), "Murder verse 2": ("MURDER", 17, 8),
    "Murder verse 4": ("MURDER", 25, 8),
    "Murder hook": ("MURDER", 41, 8), "Murder call 2": ("MURDER", 41, 2),
    "Murder call": ("MURDER", 41, 1),
}
VOX = {
    # the City call (first bar of the hook) is the signature the producer liked: it
    # answers in every gap the verses leave, alternating with Murder before the break
    "VOX CITY": [(4, "City call"), (8, "City call"), (12, "City call"), (14, "City call"),
                 (16, "City call"), (17, "City verse 1"), (26, "City call"),
                 (28, "City call"), (30, "City call"), (32, "City call"),
                 (33, "City hook B"), (41, "City verse 2"), (50, "City call"),
                 (54, "City call"), (57, "City hook A"), (81, "City hook B"),
                 (92, "City call"), (96, "City call"), (97, "City verse 3"),
                 (106, "City call"), (108, "City call"), (110, "City call"),
                 (112, "City call"), (113, "City hook B"), (122, "City call"),
                 (124, "City call"), (126, "City call"), (128, "City call"),
                 (132, "City call"), (136, "City call")],
    "VOX MURDER": [(52, "Murder call"), (56, "Murder call"), (65, "Murder hook"),
                   (73, "Murder call 2"), (75, "Murder call 2"), (90, "Murder call"), (94, "Murder call"),
                   (120, "Murder call")],
}

# Drums: track -> (instrument, kit parts, fader dB, pan, reverb send dB, ranges [a, b))
DRUMS = {
    "KICK": (KIT + "SCHT_Kick1.wav", ["kick"], -2.3, 0, None, [(1, 65), (81, END)]),
    "CLAP": (KIT + "SCHT_Clap2.wav", ["clap"], -7.4, 0, -22.5, [(9, END)]),
    "SNARE": (KIT + "AT_Infinite_Space_Snare_One_Shot_Resonate.wav", ["snare"], -10.5, 0,
              -22.5, [(17, 77), (81, 137)]),
    "HAT 16ths": (KIT + "HL_CH_CLOSED_HAT_SHOT_010.wav", ["hat_16ths"], -10.7, 0, -22.5,
                  [(1, END)]),
    "HAT OFF - persona": (KIT + "SCHT_Hat_Persona.wav", ["hat_off_persona"], -6.0, .2, -21.2,
                          [(9, END)]),
    "HAT OFF - shaker shot": (KIT + "KMRBI_AW_Shaker_One_Shot_Chuga.wav",
                              ["hat_off_shaker_shot"], -8.8, .35, -21.2, [(9, 80.5), (81, END)]),
    "HAT OFF - imite": (KIT + "SCHT_Hat_Imite.wav", ["hat_off_imite"], -4.8, -.2, -21.2,
                        [(33, 41), (57, 65), (81, 97), (113, 129)]),
    "CONGAS": ("drums/Percussion Core Kit.adg", ["congas"], -9.8, .26, -21.2,
               [(17, 65), (81, 137)]),
    "TOM 909": ("drums/909 Core Kit.adg", ["tom_909"], -3.4, -.18, None,
                [(41, 65), (97, 129)]),
    "RIM 909": ("drums/909 Core Kit.adg", ["rim_909"], -3.0, .12, None, [(97, 129)]),
    "RIDE 909": ("drums/909 Core Kit.adg", ["ride"], -13.4, .1, -30,
                 [(33, 41), (57, 65), (81, 97), (113, 129)]),
    "CRASH 909": ("drums/909 Core Kit.adg", ["crash"], -8.0, 0, None, []),
}
CRASHES = [17, 33, 41, 57, 81, 97, 113]
LOOPS = {   # audio loops: track -> (file, source bpm, fader, pan, ranges)
    "SHAKER LOOP": ("PMLxSVTxCioz_Shaker_Acti_Black_Far_Away_122bpm.wav", 122, -12, -.35,
                    [(17, 80.5), (81, END)]),
    "PERC LOOP": ("SCBB_Perc_120_Perola2.wav", 120, -16.5, -.3, [(1, END)]),
}
LOOP_DIR = Path.home() / "Music/Ableton/User Library/Samples/Claude/Nobody Kit"
BASS_RANGES = [(17, 65), (81, 129)]
KEYS_RANGES = [(33, 41), (57, 65), (81, 97), (113, 121)]
BREAK = (65, 77)

SWING_S = 0.011 * BPM / 60     # off-beat 16ths 11 ms late (the kit's measured 54.7 %)
CLAP_LATE = 0.010 * BPM / 60   # laid-back backbeat
SHAKER_EARLY = -0.0052 * BPM / 60
CUES = [(1, "INTRO - pulse + City call"), (17, "GROOVE A - City verse 1, bass in"),
        (33, "HOOK - City 2 City"), (41, "GROOVE B - verse 2, Murder teases"),
        (57, "HOOK 2 - prepared exit"), (65, "MAIN BREAK - Murder hook, groove stays"),
        (77, "TENSION - Murder call, no kick"), (81, "DROP - kick + bass back, City hook"),
        (97, "GROOVE C - verse 3, rims"), (113, "FINAL HOOK"), (121, "FINAL GROOVE"),
        (129, "OUTRO - DJ")]


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args))
    return r


def beat(bar):
    return (bar - 1) * 4.0


# ---------------------------------------------------------------- phrases (offline)
# The methods live in the package now (ableton_claude/stem_remix.py, the rap_phrase,
# onset_chop, stem_loop, breakbeat_loop and place_loop tools); these wrappers keep this
# script's stages working with its own constants.
_hp = stem_remix.highpass
_edge = stem_remix.edge
syllable_onsets = stem_remix.syllable_onsets

PREROLL = stem_remix.PREROLL   # beats of source before each phrase's downbeat
BEATS_FILE = OUT / "source-beats.json"   # Beat This beats of the original mixes
QUANTIZE = stem_remix.QUANTIZE  # how far each syllable moves toward its 16th (1 = hard)


def source_sixteenths(src, bar, bars):
    """Source times (s) of every 16th of `bars` bars from `bar`, plus the end, on the
    originals' detected beats (stem_remix.source_sixteenths)."""
    s = SOURCES[src]
    detected = json.loads(BEATS_FILE.read_text())[src]["beats"]
    return stem_remix.source_sixteenths(s["bpm"], s["downbeat"], bar, bars, detected)


def quantized_markers(sixteenths, file_start, onsets):
    """Syllables moved QUANTIZE of the way onto the swung 16th (stem_remix.onset_markers).
    Murder's hook ran +25 ms late with half its syllables more than a quarter-16th off."""
    return stem_remix.onset_markers(sixteenths, file_start, onsets, SWING_S, QUANTIZE, PREROLL)


def warp_markers(sixteenths, file_start):
    """[[beat, seconds in file], ...] for the clip: the pre-roll, then every 16th, the
    off-beat 16ths moved late by the kit's swing so the rap rides the same pocket as the
    hats (a straight rap against 54.7 % hats read early)."""
    m = [[PREROLL + k / 4 + (SWING_S if k % 2 else 0.0), t - file_start]
         for k, t in enumerate(sixteenths)]
    return [[0.0, 0.0]] + m


def phrases():
    OUT.mkdir(exist_ok=True)
    cache, meta = {}, {}
    for name, (src, bar, bars) in PHRASES.items():
        s = SOURCES[src]
        if src not in cache:
            x, sr = sf.read(s["stem"], dtype="float32")
            # mono centre drops the stereo spill of the instrumental; HP below the voice
            mono = np.repeat(x.mean(axis=1, keepdims=True), 2, axis=1)
            cache[src] = (_hp(mono, 90, sr).astype(np.float32), sr)
        x, sr = cache[src]
        sixteenths = source_sixteenths(src, bar, bars)
        # half a beat of pre-roll keeps the pickup into beat 1 (rap lines start before it)
        a = sixteenths[0] - PREROLL * 60.0 / s["bpm"]
        take = x[int(a * sr): int(sixteenths[-1] * sr)].copy()
        # gentle downward expansion under the voice: separation bleed between words
        env = ndimage.uniform_filter1d(np.abs(take).mean(axis=1), size=int(.012 * sr))
        take *= np.clip((env / .02) ** .5, .3, 1.0)[:, None]
        take = _edge(take, sr)
        take *= .5 / max(float(np.abs(take).max()), 1e-6)
        path = OUT / f"{name} - src {bar}-{bar + bars - 1}.wav"
        sf.write(path, take, sr, subtype="PCM_24")
        raw = sf.read(s["stem"], dtype="float32")[0].mean(axis=1)
        ons = syllable_onsets(raw, sr, sixteenths[0], sixteenths[-1])
        meta[name] = dict(path=str(path), beats=bars * 4, source=src, source_bar=bar,
                          markers=quantized_markers(sixteenths, a, ons), n_syllables=len(ons))
    (OUT / "phrases.json").write_text(json.dumps(meta, indent=2))
    print("phrases", len(meta), OUT)


# ---------------------------------------------------------------- tracks + devices
def tracks():
    song = client.call("get_song")
    names = [t["name"] for t in song["tracks"]]
    assert "KICK" not in names, "already built: inspect before rebuilding"
    C("set_tempo", bpm=BPM)
    for t in song["tracks"]:
        if t["kind"] == "audio" and ("City 2 City" in t["name"] or "Murder" in t["name"]):
            C("set_track", track=t["i"], name="ARCHIVE original - " + t["name"][:40], mute=True)
    for name, (inst, _, fader, pan, send, _) in DRUMS.items():
        C("create_track", kind="midi", name=name)
        C("load_device", track=name, path=inst)
        if inst.endswith(".wav"):
            C("set_device_prop", track=name, device=0, prop="playback_mode", value=1)
        C("set_track", track=name, volume_db=fader, pan=pan)
        if send is not None:
            C("set_send", track=name, send=0, db=send)
    for name, (_, _, fader, pan, _) in LOOPS.items():
        C("create_track", kind="audio", name=name)
        C("set_track", track=name, volume_db=fader, pan=pan)
        C("set_send", track=name, send=0, db=-22)
    C("create_track", kind="midi", name="BASS")
    C("load_device", track="BASS", path=KIT + "C_BinBassTone_01_SP.wav")
    C("set_param", track="BASS", device=0, param="Volume", value=0)
    C("set_track", track="BASS", volume_db=-15.5)
    C("create_track", kind="midi", name="SUB")
    C("load_device", track="SUB", path="instruments/Operator")
    C("set_track", track="SUB", volume_db=-21)
    C("create_track", kind="midi", name="KEYS - house stab")
    C("load_device", track="KEYS - house stab", path="sounds/Guitar & Plucked/House Stab.adg")
    C("set_track", track="KEYS - house stab", volume_db=0)
    C("set_send", track="KEYS - house stab", send=0, db=-20)
    for name, send in (("VOX CITY", -24), ("VOX MURDER", -20)):
        C("create_track", kind="audio", name=name)
        C("set_track", track=name, volume_db=-2)   # rap ~8 dB under the drums
        C("set_send", track=name, send=0, db=send)
    print("tracks done")


# ---------------------------------------------------------------- clips
def _feel(notes, part):
    out = []
    for p, t, d, v in notes:
        sixteenth = round(t * 4) % 4
        shift = 0.0
        if part != "kick" and sixteenth in (1, 3):
            shift += SWING_S
        if part in ("clap", "snare"):
            shift += CLAP_LATE
        if part == "hat_off_shaker_shot":
            shift += SHAKER_EARLY
        out.append([p, max(0.0, round(t + shift, 4)), d, v])
    return out


def _drum_notes(part, bars):
    notes = kits.pattern("let_the_rhythm", int(np.ceil(bars)), [part])[part]
    notes = [n for n in notes if n[1] < bars * 4 - 1e-6]
    rack = {"tom_909", "ride", "rim_909", "crash", "congas"}   # Drum Rack pads keep pitch
    if part not in rack and all(n[0] == notes[0][0] for n in notes):   # a Simpler plays 60
        notes = [[60] + n[1:] for n in notes]
    return _feel(notes, part)


def drum_clips():
    for name, (_, parts, _, _, _, ranges) in DRUMS.items():
        for a, b in ranges:
            bars = b - a
            notes = [n for part in parts for n in _drum_notes(part, bars)]
            if name == "KICK" and b == 65:          # prepared exit: last beat out
                notes = [n for n in notes if n[1] < bars * 4 - 1]
            C("create_midi_clip", track=name, bar=a, length=bars * 4, notes=notes,
              name=f"{name.lower()} {a}-{int(b) - 1}")
    crash = kits.pattern("let_the_rhythm", 1, ["crash"])["crash"][0]
    for bar in CRASHES:
        C("create_midi_clip", track="CRASH 909", bar=bar, length=4,
          notes=[[crash[0], 0, 1, crash[3]]], name="section crash")
    for name, (f, src_bpm, _, _, ranges) in LOOPS.items():
        path = str(LOOP_DIR / f)
        info = sf.info(path)
        src_beats = round(info.duration * src_bpm / 60)
        for a, b in ranges:
            # an arrangement clip keeps the file's length: place one cycle, then fill
            C("create_audio_clip", track=name, path=path, bar=a, warp=True, beats=src_beats,
              warp_mode="beats", name=f"{name.lower()} {a}")
            fill_loop(name, a, b, src_beats)


def fill_loop(name, a, b, src_beats):
    C("set_clip", track=name, clip={"at": beat(a)}, looping=True, loop_start=0,
      loop_end=src_beats)
    cycle = int(src_beats // 4)
    # start after the source cycle: a duplicate onto the source replaces it and leaves
    # fill_range holding a dead clip handle
    C("fill_range", track=name, src_start_bar=a, src_end_bar=a + cycle, start_bar=a + cycle,
      end_bar=int(np.ceil(b)))
    if b != int(b):                       # stop 2 beats before the drop: a small silence
        last = [c for c in client.call("get_track", {"track": name})["clips"]
                if c["start"] < beat(b) < c["end"]]
        if last:
            C("trim_clip", track=name, clip={"at": last[0]["start"]}, end_beat=beat(b))


E = {"E1": 28, "B1": 35, "D2": 38, "E2": 40, "G2": 43, "A2": 45}
BIN_OFFSET = 60 - 24   # BinBassTone is a C1 (32.7 Hz) at Simpler's root 60: E2 -> 76
RIFF = [  # two bars, Em pedal, house tresillo (16th steps 0 3 6 10 14)
    ("E2", 0, .5, 112), ("E2", .75, .25, 96), ("G2", 1.5, .5, 104), ("E2", 2.5, .5, 108),
    ("D2", 3.5, .25, 92),
    ("E2", 4, .5, 112), ("E2", 4.75, .25, 96), ("B1", 5.5, .5, 100), ("D2", 6.5, .5, 104),
    ("E2", 7.5, .25, 94),
]
EM9 = [55, 59, 62, 66]
PROG = [EM9, [55, 59, 60, 64], [54, 57, 59, 64], EM9]       # Em9 Cmaj7 D6/9 Em9
STABS = [(.75, .25, 96), (2.5, .3, 92), (4.75, .25, 96), (5.5, .3, 90), (7.5, .25, 94)]


def _tile(cell, cell_beats, bars, gen):
    out = []
    for k in range(int(bars * 4 // cell_beats)):
        for n in gen(cell):
            out.append([n[0], n[1] + k * cell_beats, n[2], n[3]])
    return out


def harmonic_clips():
    for a, b in BASS_RANGES:
        bars = b - a
        bass = _tile(RIFF, 8, bars, lambda c: [[E[p] + BIN_OFFSET, t, d, v] for p, t, d, v in c])
        bass = _feel(bass, "bass")
        if b == 65:                      # bass leaves with the kick's prepared exit
            bass = [n for n in bass if n[1] < bars * 4 - 1]
        C("create_midi_clip", track="BASS", bar=a, length=bars * 4, notes=bass,
          name=f"bass riff Em {a}")
        sub = [[E["E1"], n[1], min(n[2], .45), 110] for n in bass if n[0] == E["E2"] + BIN_OFFSET]
        C("create_midi_clip", track="SUB", bar=a, length=bars * 4, notes=sub, name=f"sub E1 {a}")
    for a, b in KEYS_RANGES:
        bars = b - a
        keys = _tile(STABS, 8, bars, lambda c: [[p, t, d, v] for t, d, v in c for p in EM9])
        C("create_midi_clip", track="KEYS - house stab", bar=a, length=bars * 4,
          notes=_feel(keys, "keys"), name=f"Em9 stabs locked to bass {a}")
    a, b = BREAK
    chords = []
    for k in range(b - a):
        ch = PROG[k % 4]
        chords += [[p, k * 4.0, 3.0, 84] for p in ch] + [[p, k * 4 + 2.5 + SWING_S * 0, .3, 70]
                                                          for p in ch]
    C("create_midi_clip", track="KEYS - house stab", bar=a, length=(b - a) * 4, notes=chords,
      name="break: Em9 Cmaj7 D6/9 Em9")
    held = [[p, 0, 7.5, 80] for p in EM9] + [[p, 8, 5.5, 86] for p in EM9]
    C("create_midi_clip", track="KEYS - house stab", bar=77, length=14, notes=held,
      name="tension: Em9 held, out 2 beats before the drop")


def vocal_clips():
    meta = json.loads((OUT / "phrases.json").read_text())
    for track, calls in VOX.items():
        for bar, name in calls:
            m = meta[name]
            at, beats = beat(bar) - PREROLL, m["beats"] + PREROLL
            C("create_audio_clip", track=track, path=m["path"], beat=at, warp=False,
              name=f"{name} (src bar {m['source_bar']})")
            dur = sf.info(m["path"]).duration - .001     # the last 16th is the file's end
            C("set_warp_markers", track=track, clip={"at": at},
              markers=[[b, min(t, dur)] for b, t in m["markers"]])
            r = C("set_clip", track=track, clip={"at": at}, warping=True,
                  warp_mode="complex_pro", looping=False, start_marker=0, end_marker=beats)
            if r.get("length", beats) > beats + .02:
                C("trim_clip", track=track, clip={"at": at}, end_beat=at + beats)


# ---------------------------------------------------------------- v3 (2026-10-20 notes)
# "keys don't fit the vocal or the song, odd timbre, too many hits"; "main break empty, no
# harmony, no tension and release"; "kick and bass could glue more"; "vocal too far in
# front"; "focus on 'baby I'm in your city', the babe chops". The harmony and timbre now
# come from the originals' own instruments (htdemucs 'other' stems, 2-bar loops, both
# A440); the break moves the bass i - iv - VI - VII and holds the V under a Murder loop
# whose filter opens into the drop; kick, bass and sub share a LOW END glue bus.
STEMS4 = ROOT / "stems4/htdemucs"
LOOPS_V3 = {   # name: (source, first source bar, bars) - least vocal bleed, most typical
    "Murder keys": ("MURDER", 3, 2), "City synth": ("CITY", 85, 2),
}
BABES = [115.57, 117.50, 121.53, 105.37, 108.47]     # sustained notes in hook B (s)
BABE_DUR = [.87, .80, .64, .31, .54]
CHOPS = [(9, 0, 0), (72, 2, 1), (77, 0, 0), (78, 0, 1), (79, 0, 0), (79, 2, 1), (80, 0, 0),
         (89, 0, 0), (93, 0, 1), (121, 0, 0), (125, 0, 1), (129, 0, 0), (137, 0, 1)]
LOOP_CITY_RANGES = [(33, 41), (57, 65), (81, 97), (113, 121)]
# LOOP MURDER: (first bar, last bar + 1, filter Hz at start, filter Hz at end)
LOOP_MURDER_SWEEPS = [(49, 57, 700, 700), (65, 77, 500, 2500), (77, 81, 2500, 18000),
                      (89, 97, 18000, 18000), (121, 129, 18000, 18000)]
BIN = lambda name, octave: {"C": 0, "D": 2, "E": 4, "F#": 6, "G": 7, "A": 9, "B": 11}[name] \
    + 12 * (octave - 1) + 60                        # BinBassTone is C1 at 60: E2 -> 76
BREAK_BASS = [  # bar, note, octave, pattern [(beat, dur, vel)]: i - iv - VI - VII, V pedal
    *[(b, "E", 2, [(0, 1.5, 104), (2.5, 1.0, 92)]) for b in range(65, 69)],
    *[(b, "A", 1, [(0, 1.5, 104), (2.5, 1.0, 92)]) for b in (69, 70)],
    *[(b, "E", 2, [(0, 1.5, 104), (2.5, 1.0, 92)]) for b in (71, 72)],
    *[(b, "A", 1, [(0, 1.5, 106), (2.5, 1.0, 94)]) for b in (73, 74)],
    (75, "C", 2, [(0, 1.5, 106), (2.5, 1.0, 96)]), (76, "D", 2, [(0, 1.5, 108), (2.5, 1.0, 98)]),
    *[(b, "B", 1, [(k * .5, .4, 70 + 3 * (4 * (b - 77) + k // 2)) for k in range(8)])
      for b in range(77, 80)],
    (80, "B", 1, [(k * .5, .4, 112) for k in range(4)]),   # out 2 beats before the drop
]


_raw_hz = stem_remix.filter_raw   # Auto Filter Frequency as a raw envelope value


def v3_prepare():
    meta = {}
    for name, (src, bar, bars) in LOOPS_V3.items():
        stem = STEMS4 / SOURCES[src]["stem"].parent.name / "other.wav"
        x, sr = sf.read(stem, dtype="float32")
        six = source_sixteenths(src, bar, bars)
        a = six[0]
        take = _edge(x[int(a * sr): int(six[-1] * sr)].copy(), sr, .002, .004)
        take *= .5 / max(float(np.abs(take).max()), 1e-6)
        path = OUT / f"{name} loop - src {bar}-{bar + bars - 1}.wav"
        sf.write(path, take, sr, subtype="PCM_24")
        mk = [[k / 4 + (SWING_S if k % 2 else 0.0), t - a] for k, t in enumerate(six)]
        meta[name] = dict(path=str(path), beats=bars * 4, markers=mk)
    x, sr = sf.read(SOURCES["CITY"]["stem"], dtype="float32")
    mono = _hp(np.repeat(x.mean(axis=1, keepdims=True), 2, axis=1), 90, sr).astype(np.float32)
    audition = []
    for k, (t, d) in enumerate(zip(BABES, BABE_DUR)):
        take = _edge(mono[int((t - .12) * sr): int((t + d + .15) * sr)].copy(), sr, .004, .06)
        take *= .5 / max(float(np.abs(take).max()), 1e-6)
        path = OUT / f"Babe chop {k + 1} - src {int(t // 60)}m{t % 60:04.1f}s.wav"
        sf.write(path, take, sr, subtype="PCM_24")
        meta[f"babe{k}"] = dict(path=str(path))
        audition += [take, np.zeros((int(.6 * sr), 2), np.float32)]
    sf.write(OUT / "Babe chops - audition (1 to 5).wav", np.concatenate(audition), sr,
             subtype="PCM_24")
    (OUT / "v3.json").write_text(json.dumps(meta, indent=1))
    print("v3 prepared", list(meta))


def _place_loop(track, m, bar, envelopes=None):
    at = beat(bar)
    C("create_audio_clip", track=track, path=m["path"], bar=bar, warp=False,
      name=Path(m["path"]).stem, envelopes=envelopes)
    dur = sf.info(m["path"]).duration - .001
    C("set_warp_markers", track=track, clip={"at": at},
      markers=[[b, min(t, dur)] for b, t in m["markers"]])
    r = C("set_clip", track=track, clip={"at": at}, warping=True, warp_mode="complex_pro",
          looping=False, start_marker=0, end_marker=m["beats"])
    if r.get("length", m["beats"]) > m["beats"] + .02:   # markers do not resize a clip
        C("trim_clip", track=track, clip={"at": at}, end_beat=at + m["beats"])


def v3_live():
    meta = json.loads((OUT / "v3.json").read_text())
    # the rejected keys are archived, not deleted
    C("set_track", track="KEYS - house stab", name="ARCHIVE - KEYS house stab (rejected)",
      mute=True)
    C("set_param", track="BASS", device=0, param="Detune", value=14)   # sample is -14 ct
    for t in ("LOOP MURDER - orig keys", "LOOP CITY - orig synth"):
        C("set_param", track=t, device="EQ Eight", param="1 Frequency A", display="150 Hz")
    C("set_param", track="LOOP MURDER - orig keys", device="Auto Filter", param="Frequency",
      display="18.0 kHz")
    C("set_param", track="LOOP MURDER - orig keys", device="Auto Filter", param="Resonance",
      display="25.0 %")
    C("set_track", track="LOOP MURDER - orig keys", volume_db=-5)
    C("set_track", track="LOOP CITY - orig synth", volume_db=-3, pan=0.1)   # ~-11 dB vs drums
    for t in ("LOOP MURDER - orig keys", "LOOP CITY - orig synth"):
        C("set_send", track=t, send=0, db=-20)
    for a, b in LOOP_CITY_RANGES:
        for bar in range(a, b, 2):
            _place_loop("LOOP CITY - orig synth", meta["City synth"], bar)
    for a, b, f0, f1 in LOOP_MURDER_SWEEPS:
        n = (b - a) // 2
        for k, bar in enumerate(range(a, b, 2)):
            lo = f0 * (f1 / f0) ** (k / n)
            hi = f0 * (f1 / f0) ** ((k + 1) / n)
            env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                    "points": [[0, _raw_hz(lo)], [8, _raw_hz(hi)]]}]
            _place_loop("LOOP MURDER - orig keys", meta["Murder keys"], bar, env)
    # break bass: i - iv - VI - VII, then the V pulsing into the drop. Its own track: on
    # the groove bass's fader it sat 8-12 dB over the kickless break's drums
    C("delete_clips_in_range", track="BASS", start_bar=65, end_bar=81)
    C("create_track", kind="midi", name="BASS - break")
    C("load_device", track="BASS - break", path=KIT + "C_BinBassTone_01_SP.wav")
    C("set_param", track="BASS - break", device=0, param="Volume", value=0)
    C("set_param", track="BASS - break", device=0, param="Detune", value=14)
    C("set_track", track="BASS - break", volume_db=-27)
    C("set_track_output", track="BASS - break", dest="LOW END")
    for bar, name, octv, hits in BREAK_BASS:
        notes = [[BIN(name, octv), t, d, v] for t, d, v in hits]
        C("create_midi_clip", track="BASS - break", bar=bar, length=4, notes=notes,
          name=f"break bass {name}")
    # babe chops: unwarped, the voice's own speed, into the delay
    C("set_track", track="VOX BABE", volume_db=-8)
    C("set_send", track="VOX BABE", send=0, db=-16)
    C("set_send", track="VOX BABE", send=1, db=-14)
    for bar, off, k in CHOPS:
        C("create_audio_clip", track="VOX BABE", path=meta[f"babe{k}"]["path"],
          beat=beat(bar) + off, warp=False, name=f"babe {k + 1}")
    # vocals back into the mix
    for t, send in (("VOX CITY", -19), ("VOX MURDER", -17)):
        C("set_track", track=t, volume_db=-4)     # ~11 dB under the drums
        C("set_send", track=t, send=0, db=send)
    for t in ("VOX CITY", "VOX MURDER"):
        C("delete_clips_in_range", track=t, start_bar=1, end_bar=146)
    vocal_clips()


def v3_low_end():
    """The kit's LOW END bus: kick + bass + sub through one HP 34 Hz, a slow 2:1 glue and
    a little soft-sine saturation, so they move as one instrument."""
    C("create_track", kind="audio", name="LOW END")
    C("set_track_input", track="LOW END", source="No Input")
    C("set_track", track="LOW END", monitoring="in")
    for t in ("KICK", "BASS", "SUB"):
        C("set_track_output", track=t, dest="LOW END")
    # a list parameter takes `item`: display="High Pass 48dB" matched "Low Pass 48dB"
    C("set_param", track="LOW END", device="EQ Eight", param="1 Filter Type A",
      item="High Pass 48dB")
    C("set_param", track="LOW END", device="EQ Eight", param="1 Frequency A", display="34.0 Hz")
    C("load_device", track="LOW END", query="Glue Compressor", roots=["audio_effects"])
    C("load_device", track="LOW END", query="Saturator", roots=["audio_effects"])
    for param, disp in (("Attack", "10"), ("Ratio", "2"), ("Release", ".2"),
                        ("Range", "2.5 dB"), ("Threshold", "-20.0 dB")):
        C("set_param", track="LOW END", device="Glue Compressor", param=param, display=disp)
    C("set_param", track="LOW END", device="Saturator", param="Type", item="Soft Sine")
    C("set_param", track="LOW END", device="Saturator", param="Drive", display="2.0 dB")
    C("set_param", track="LOW END", device="Saturator", param="Dry/Wet", display="30 %")



# ---------------------------------------------------------------- v4 mix (2026-10-20)
# "loved the guitar riff; the vocal there needs more warp and timing; fit everything in
# the mix, volumes, priorities". Priorities: kick/bass > vocal > Murder guitar riff >
# City synth > hats/perc > babe chops. Each EQ move makes room for the next priority.
RIFF = "LOOP MURDER - orig keys"


def _eq(track, band, kind, hz, db=None, q=None):
    C("set_param", track=track, device="EQ Eight", param=f"{band} Filter On A", value=1)
    C("set_param", track=track, device="EQ Eight", param=f"{band} Filter Type A", item=kind)
    C("set_param", track=track, device="EQ Eight", param=f"{band} Frequency A", display=hz)
    if db is not None:
        C("set_param", track=track, device="EQ Eight", param=f"{band} Gain A", display=db)
    if q is not None:
        C("set_param", track=track, device="EQ Eight", param=f"{band} Q A", display=q)


def mix_v4():
    C("set_track", track=RIFF, name="LOOP MURDER - guitar riff")
    riff = "LOOP MURDER - guitar riff"
    for t in ("VOX CITY", "VOX MURDER"):
        _eq(t, 1, "High Pass 12dB", "120 Hz")
        _eq(t, 2, "Bell", "350 Hz", "-2.5 dB", "1.00")      # the guitar's body lives here
        _eq(t, 7, "High Shelf", "6.00 kHz", "2.0 dB")        # demucs stems of 90s masters are dark
        C("load_device", track=t, query="Compressor", roots=["audio_effects"])
        for param, disp in (("Threshold", "-20.0 dB"), ("Ratio", "3.00 : 1"),
                            ("Attack", "10.0 ms"), ("Release", "80.0 ms")):
            C("set_param", track=t, device="Compressor", param=param, display=disp)
    _eq(riff, 3, "Bell", "2.50 kHz", "-2.0 dB", "1.20")       # the vocal's presence
    _eq("LOOP CITY - orig synth", 3, "Bell", "2.50 kHz", "-1.5 dB", "1.20")
    for t, d in (("HAT 16ths", 2.0), ("HAT OFF - persona", 1.5)):
        cur = [x for x in client.call("get_song")["tracks"] if x["name"] == t][0]["vol_db"]
        C("set_track", track=t, volume_db=round(cur + d, 1))
    # the riff the producer loved: more of it, and open where it plays in grooves
    meta = json.loads((OUT / "v3.json").read_text())
    C("delete_clips_in_range", track=riff, start_bar=49, end_bar=57)
    for a, b, f0, f1 in [(49, 57, 1500, 4000), (105, 113, 18000, 18000)]:
        for k, bar in enumerate(range(a, b, 2)):
            n = (b - a) // 2
            lo, hi = f0 * (f1 / f0) ** (k / n), f0 * (f1 / f0) ** ((k + 1) / n)
            env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                    "points": [[0, _raw_hz(lo)], [8, _raw_hz(hi)]]}]
            _place_loop(riff, meta["Murder keys"], bar, env)


# ---------------------------------------------------------------- v5 energy (2026-10-20)
# "sometimes very buzzy; the scratch chops could sit better; when the City loop leaves
# the energy falls too much; use the Murder loop more; more dynamics, house arrangement
# and energy control". The buzz was the City loop: 3-10 kHz in the 'other' stem went from
# 7 % (v2) to 17 % of its energy with it open; the limiter was idle (0.03 % of samples
# near the ceiling). The City loop now runs 9-136 under a low-pass that IS the energy
# map (open = 6 kHz, never 18 kHz), out only for the main break; the Murder riff joins
# it in the peaks (drop, final hook). The chop files start 0.12 s before the word, so they
# landed a 16th late: they now start 0.25 beat early, on phrase gaps.
CITY = "LOOP CITY - orig synth"
CITY_MAP = [(9, 17, 400, 900), (17, 31, 1000, 1000), (31, 33, 1000, 2500),
            (33, 41, 6000, 6000), (41, 49, 1200, 1200), (49, 57, 1200, 3000),
            (57, 63, 6000, 6000), (63, 65, 6000, 1500), (81, 97, 6000, 6000),
            (97, 105, 1200, 1200), (105, 113, 1500, 3000), (113, 121, 6000, 6000),
            (121, 129, 2500, 1200), (129, 137, 900, 350)]
RIFF_ADD = [(81, 89), (113, 121)]                 # the riff joins the City loop at the peaks
CHOPS_V5 = [(9, 0, 0), (25, 0, 1), (29, 0, 0), (49, 0, 1), (53, 0, 0), (72, 2, 1),
            (77, 0, 0), (78, 0, 1), (79, 0, 0), (79, 2, 1), (80, 0, 0), (89, 0, 0),
            (93, 0, 1), (105, 0, 0), (109, 0, 1), (121, 0, 0), (125, 0, 1), (129, 0, 0),
            (133, 0, 1)]
CHOP_LEAD = 0.25            # beats of file before the word (0.12 s at 125 BPM)
KICK_HOLES = [32, 56, 112]  # the kick's last beat out before hooks: a prepared entry


def _swept(track, m, a, b, f0, f1, device="Auto Filter"):
    n = max(1, (b - a) // 2)
    for k, bar in enumerate(range(a, b, 2)):
        lo, hi = f0 * (f1 / f0) ** (k / n), f0 * (f1 / f0) ** ((k + 1) / n)
        env = [{"param": "Frequency", "device": device, "unit": "raw",
                "points": [[0, _raw_hz(lo)], [8, _raw_hz(hi)]]}]
        _place_loop(track, m, bar, env)


def v5_energy():
    meta = json.loads((OUT / "v3.json").read_text())
    names = [d["name"] for d in client.call("get_track", {"track": CITY})["devices"]]
    if "Auto Filter" not in names:
        C("load_device", track=CITY, query="Auto Filter", roots=["audio_effects"])
    _eq(CITY, 7, "High Shelf", "3.50 kHz", "-2.0 dB")
    C("delete_clips_in_range", track=CITY, start_bar=1, end_bar=146)
    for a, b, f0, f1 in CITY_MAP:
        _swept(CITY, meta["City synth"], a, b, f0, f1)
    riff = "LOOP MURDER - guitar riff"
    for a, b in RIFF_ADD:
        C("delete_clips_in_range", track=riff, start_bar=a, end_bar=b)
        _swept(riff, meta["Murder keys"], a, b, 18000, 18000)
    C("delete_clips_in_range", track="VOX BABE", start_bar=1, end_bar=146)
    for bar, off, k in CHOPS_V5:
        C("create_audio_clip", track="VOX BABE", path=meta[f"babe{k}"]["path"],
          beat=beat(bar) + off - CHOP_LEAD, warp=False, name=f"babe {k + 1}")
    for clip in client.call("get_track", {"track": "KICK"})["clips"]:
        notes = client.call("get_notes", {"track": "KICK", "clip": clip["i"]})
        holes = [beat(b) + 3 - clip["start"] for b in KICK_HOLES]
        keep = [n for n in notes if all(abs(n[1] - h) > 1e-3 for h in holes)]
        if len(keep) < len(notes):
            C("add_notes", track="KICK", clip=clip["i"], notes=keep, replace=True)
    for t in ("VOX CITY", "VOX MURDER"):
        C("set_param", track=t, device="EQ Eight", param="7 Gain A", display="1.0 dB")
    # v5 measured grooves -9.6 LUFS against hooks -9.5 and drop -9.3: flat. Contrast by
    # subtraction: the snare layer lifts only the hooks/drop, the 909 tom only the second
    # half of grooves B and C (the groove evolves every 8 bars).
    for track, ranges in (("SNARE", [(33, 41), (57, 65), (81, 97), (113, 121)]),
                          ("TOM 909", [(49, 57), (105, 113)])):
        C("delete_clips_in_range", track=track, start_bar=1, end_bar=146)
        part = DRUMS[track][1][0]
        for a, b in ranges:
            C("create_midi_clip", track=track, bar=a, length=(b - a) * 4,
              notes=_drum_notes(part, b - a), name=f"{track.lower()} {a}-{b - 1} (lift)")


# ---------------------------------------------------------------- v6 roles (2026-10-20)
# "volumes muddy, no lead and no atmosphere; City synth further back, giving rhythm with
# call and response; closed hats a bit loud; harmony and coherence; the song has that bass
# riff; scratches all the time lose their charm; mind phasing". Roles now: lead = the rap,
# and the Murder guitar riff where nobody raps; rhythm = City 2 City's own bass riff (the
# ear's transcription: E E G | A A B on 16ths 0 3 6, a D D# E B turn every 4th bar) and
# the City synth answering only in the 2nd bar of each pair, high-passed, lower, wetter;
# atmosphere = the riff into a 6 s reverb through a send only (no dry copy: no comb
# filtering against the riff); chops and calls only at structural moments.
CITY_BASS = [  # (beat in 4 bars, note, octave, dur); octave up from the record's E1
    *[(o + t, n, 2, .35) for o in (0, 8) for t, n in ((0, "E"), (.75, "E"), (1.5, "G"))],
    *[(o + t, n, 2, .35) for o in (4, 12) for t, n in ((0, "A"), (.75, "A"), (1.5, "B"))],
    (14.5, "D", 2, .25), (14.75, "D#", 2, .25), (15.0, "E", 2, .4), (15.5, "B", 1, .4),
]
NOTE_PC = {"C": 0, "D": 2, "D#": 3, "E": 4, "F#": 6, "G": 7, "A": 9, "B": 11}
# "the break has no tension, it's dry; use the scratch as FX, not part of the music":
# the chops become an FX track (thrown into delay and atmosphere) at transitions only,
# plus a reversed "babe" swelling into the drop; the break's tension comes from the
# drop's own City synth previewed filtered and opening, the V in the bass, and the
# Murder voice and riff sent into the atmosphere.
FX = "FX - babe scratch"
CHOPS_V6 = [(56, 2, 1), (72, 2, 1), (76, 2, 0), (112, 2, 1), (128, 2, 0)]
REVERSE_INTO = [81]            # a reversed babe ends exactly on these downbeats
TENSION_CITY = (77, 81, 400, 3000)
CALLS_V6 = [16, 32, 112, 128]
CITY_RESPONSE = [(9, 17, 500, 900), (17, 33, 900, 1400), (33, 41, 2500, 2500),
                 (41, 57, 900, 1800), (57, 65, 2500, 1500), (81, 97, 2500, 2500),
                 (97, 113, 900, 1800), (113, 121, 2500, 2500), (121, 137, 1500, 400)]
ATMOS_RANGES = [(33, 41), (57, 81), (81, 97), (113, 129)]


def _section_file(name, m, bars, gate=None):
    """The 2-bar loop tiled over `bars` bars at source time, bars where gate(bar) is False
    silenced with 5 ms fades; returns (path, markers) for one clip per section."""
    return stem_remix.section_file(dict(m, beats=m.get("beats", 8)), bars, OUT / f"{name}.wav", gate)


def _place_section(track, path, mk, bar, beats, f0=None, f1=None):
    at = beat(bar)
    env = None
    if f0:
        env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                "points": [[0, _raw_hz(f0)], [beats, _raw_hz(f1)]]}]
    C("create_audio_clip", track=track, path=path, bar=bar, warp=False,
      name=Path(path).stem, envelopes=env)
    dur = sf.info(path).duration - .001
    C("set_warp_markers", track=track, clip={"at": at}, markers=[[b, min(t, dur)] for b, t in mk])
    r = C("set_clip", track=track, clip={"at": at}, warping=True, warp_mode="complex_pro",
          looping=False, start_marker=0, end_marker=beats)
    if r.get("length", beats) > beats + .02:
        C("trim_clip", track=track, clip={"at": at}, end_beat=at + beats)


def v6_roles():
    meta = json.loads((OUT / "v3.json").read_text())
    # rhythm: the City synth answers in the 2nd bar of each pair, back in the room
    C("delete_clips_in_range", track=CITY, start_bar=1, end_bar=146)
    for a, b, f0, f1 in CITY_RESPONSE:
        path, mk = _section_file(f"City synth response {a}-{b - 1}", meta["City synth"], b - a,
                                 gate=lambda k: k % 2 == 1)
        _place_section(CITY, path, mk, a, (b - a) * 4, f0, f1)
    _eq(CITY, 1, "High Pass 12dB", "400 Hz")
    C("set_track", track=CITY, volume_db=-7, pan=0.2)
    C("set_send", track=CITY, send=0, db=-13)
    # lead: the riff stays dry and centred; its mud below the body goes
    riff = "LOOP MURDER - guitar riff"
    _eq(riff, 2, "Bell", "220 Hz", "-2.0 dB", "1.00")
    C("set_track", track=riff, pan=0)
    # atmosphere: the riff through a send only into a long, dark, mono-bass reverb
    C("set_param", track="return:C-Atmos", device="Hybrid Reverb", param="Decay", display="6.00 s")
    C("set_param", track="return:C-Atmos", device="Hybrid Reverb", param="Dry/Wet", display="100 %")
    C("set_param", track="return:C-Atmos", device="Hybrid Reverb", param="EQ Lo Freq", display="300 Hz")
    C("set_param", track="return:C-Atmos", device="Hybrid Reverb", param="EQ Hi Gain", display="-6.0 dB")
    C("set_param", track="return:C-Atmos", device="Hybrid Reverb", param="Bass Mono", value=1)
    C("set_track", track="return:C-Atmos", volume_db=-10)
    C("create_track", kind="audio", name="ATMOS - riff wash")
    C("set_track_output", track="ATMOS - riff wash", dest="Sends Only")
    C("set_send", track="ATMOS - riff wash", send=2, db=0)
    for a, b in ATMOS_RANGES:
        path, mk = _section_file(f"Riff wash {a}-{b - 1}", meta["Murder keys"], b - a)
        _place_section("ATMOS - riff wash", path, mk, a, (b - a) * 4)
    C("set_send", track="VOX BABE", send=2, db=-8)
    # the bass: City 2 City's own riff, E2 octave, the sub on its roots
    for t in ("BASS", "SUB"):
        C("delete_clips_in_range", track=t, start_bar=17, end_bar=65)
        C("delete_clips_in_range", track=t, start_bar=81, end_bar=129)
    for a, b in BASS_RANGES:
        notes, sub = [], []
        for k in range((b - a) // 4):
            for t, n, o, d in CITY_BASS:
                notes.append([NOTE_PC[n] + 12 * (o - 1) + 60, k * 16 + t, d, 108 if t % 4 == 0 else 98])
                if t % 4 in (0, .75) and o == 2 and n in ("E", "A"):
                    sub.append([NOTE_PC[n] + 24, k * 16 + t, .3, 110])      # E1 / A1
        notes, sub = _feel(notes, "bass"), _feel(sub, "bass")
        if b == 65:
            notes = [x for x in notes if x[1] < (b - a) * 4 - 1]
            sub = [x for x in sub if x[1] < (b - a) * 4 - 1]
        C("create_midi_clip", track="BASS", bar=a, length=(b - a) * 4, notes=notes,
          name=f"City 2 City bass riff {a}")
        C("create_midi_clip", track="SUB", bar=a, length=(b - a) * 4, notes=sub,
          name=f"sub roots {a}")
    # the scratch is FX: own name, further back, thrown into delay and atmosphere
    C("set_track", track="VOX BABE", name=FX, volume_db=-12)
    _eq(FX, 1, "High Pass 12dB", "300 Hz")
    for send, db in ((0, -12), (1, -8), (2, -6)):
        C("set_send", track=FX, send=send, db=db)
    C("delete_clips_in_range", track=FX, start_bar=1, end_bar=146)
    for bar, off, k in CHOPS_V6:
        C("create_audio_clip", track=FX, path=meta[f"babe{k}"]["path"],
          beat=beat(bar) + off - CHOP_LEAD, warp=False, name=f"babe throw {k + 1}")
    x, sr = sf.read(meta["babe0"]["path"], dtype="float32")
    rev = OUT / "Babe chop 1 - reversed.wav"
    sf.write(rev, _edge(x[::-1].copy(), sr, .08, .004), sr, subtype="PCM_24")
    rev_beats = len(x) / sr * client.call("get_song")["tempo"] / 60
    for bar in REVERSE_INTO:
        C("create_audio_clip", track=FX, path=str(rev), beat=beat(bar) - rev_beats,
          warp=False, name="babe reversed into the drop")
    # ear candy, from the riff itself, only at turns: a reversed half-bar swelling into
    # hooks, and a 32nd stutter of its first hit in the beat before groove B and the break
    tempo = client.call("get_song")["tempo"]
    rx, rsr = sf.read(meta["Murder keys"]["path"], dtype="float32")
    half = rx[len(rx) // 4: len(rx) // 2][::-1].copy()          # beats 3-4 of bar 1
    swell = OUT / "Riff reversed swell.wav"
    sf.write(swell, _edge(half * np.linspace(.2, 1, len(half))[:, None], rsr, .05, .004),
             rsr, subtype="PCM_24")
    for bar in (33, 113):
        C("create_audio_clip", track=FX, path=str(swell), warp=False, name="riff swell",
          beat=beat(bar) - len(half) / rsr * tempo / 60)
    n32 = int(rsr * 60 / tempo / 8)
    hit = _edge(rx[:n32].copy(), rsr, .002, .01)
    stut = np.concatenate([hit * (.55 + .45 * k / 7) for k in range(8)])
    stutter = OUT / "Riff stutter 1 beat.wav"
    sf.write(stutter, stut, rsr, subtype="PCM_24")
    for bar in (41, 65):
        C("create_audio_clip", track=FX, path=str(stutter), warp=False, name="riff stutter",
          beat=beat(bar) - 1)
    # tension: the drop's City synth previewed, every bar, filter opening into the drop
    a, b, f0, f1 = TENSION_CITY
    path, mk = _section_file("City synth tension", meta["City synth"], b - a)
    _place_section(CITY, path, mk, a, (b - a) * 4 - 2, f0, f1)   # out 2 beats early
    # the break breathes: the Murder voice into the atmosphere
    C("set_send", track="VOX MURDER", send=2, db=-12)
    # City calls only at four turns (they read as scratches when repeated)
    calls = [c for c in client.call("get_track", {"track": "VOX CITY"})["clips"]
             if c["name"].startswith("City call")]
    for c in calls:
        if round(c["start"] / 4 + 1.125) not in CALLS_V6:
            C("set_clip", track="VOX CITY", clip={"at": c["start"]}, muted=True)
    # closed hats back
    C("set_track", track="HAT 16ths", volume_db=-12.0)


# ---------------------------------------------------------------- v7 (2026-10-20)
# "loved this bass groove, use its holes for the other riffs; you shouldn't have shortened
# the City loops, they give movement; the scratches are still repetitive". The City loop
# runs whole again; it and the Murder riff duck under the bass (sidechain from BASS) and
# bloom in its holes (beats 2-4 of every bar). Each scratch is its own variation, once.
def _scratch_variants(meta):
    tempo = client.call("get_song")["tempo"]
    s16 = 60 / tempo / 4
    out = {}
    x, sr = sf.read(meta["babe1"]["path"], dtype="float32")
    lead = int(.12 * sr)
    att = _edge(x[lead: lead + int(.09 * sr)].copy(), sr, .002, .01)
    gap = np.zeros((int(s16 * sr) - len(att), 2), np.float32)
    out["stutter"] = np.concatenate([att, gap, att, gap, x[lead:]])           # ba-ba-babe
    sos = signal.butter(4, [700, 3000], "bandpass", fs=sr, output="sos")
    tel = signal.sosfilt(sos, x[lead:], axis=0).astype(np.float32)
    out["telephone"] = tel * (.5 / max(float(np.abs(tel).max()), 1e-6))
    y, sr0 = sf.read(meta["babe0"]["path"], dtype="float32")
    y = y[lead:]
    rate = np.linspace(1.0, .35, len(y))                                     # tape stop
    pos = np.cumsum(rate)
    pos = pos[pos < len(y) - 1]
    out["tapestop"] = np.stack([np.interp(pos, np.arange(len(y)), y[:, c]) for c in (0, 1)],
                               axis=1).astype(np.float32)
    z, _ = sf.read(meta["babe2"]["path"], dtype="float32")
    out["plain3"] = z[lead:]
    paths = {}
    for k, v in out.items():
        path = OUT / f"Babe scratch - {k}.wav"
        sf.write(path, _edge(v, sr, .002, .03), sr, subtype="PCM_24")
        paths[k] = str(path)
    return paths


SCRATCHES_V7 = [(56, 2, "stutter"), (72, 2, "telephone"), (76, 2, "plain1"),
                (104, 2, "plain3"), (128, 2, "tapestop")]


def v7_holes():
    meta = json.loads((OUT / "v3.json").read_text())
    C("delete_clips_in_range", track=CITY, start_bar=1, end_bar=146)
    for a, b, f0, f1 in CITY_RESPONSE:
        path, mk = _section_file(f"City synth {a}-{b - 1}", meta["City synth"], b - a)
        _place_section(CITY, path, mk, a, (b - a) * 4, f0, f1)
    a, b, f0, f1 = TENSION_CITY
    path, mk = _section_file("City synth tension", meta["City synth"], b - a)
    _place_section(CITY, path, mk, a, (b - a) * 4 - 2, f0, f1)
    for t in (CITY, "LOOP MURDER - guitar riff"):
        names = [d["name"] for d in client.call("get_track", {"track": t})["devices"]]
        if "Compressor" not in names:
            C("load_device", track=t, query="Compressor", roots=["audio_effects"])
        C("set_device_input", track=t, device="Compressor", source="BASS", channel="Post Mixer")
        C("set_param", track=t, device="Compressor", param="S/C EQ On", value=0)
        for param, disp in (("Threshold", "-32.0 dB"), ("Ratio", "2.50 : 1"),
                            ("Attack", "1.00 ms"), ("Release", "150 ms")):
            C("set_param", track=t, device="Compressor", param=param, display=disp)
    paths = _scratch_variants(meta)
    paths["plain1"] = None
    C("delete_clips_in_range", track=FX, start_bar=55, end_bar=58)
    C("delete_clips_in_range", track=FX, start_bar=71, end_bar=78)
    C("delete_clips_in_range", track=FX, start_bar=103, end_bar=106)
    C("delete_clips_in_range", track=FX, start_bar=127, end_bar=130)
    for bar, off, kind in SCRATCHES_V7:
        if kind == "plain1":
            C("create_audio_clip", track=FX, path=meta["babe0"]["path"], warp=False,
              beat=beat(bar) + off - CHOP_LEAD, name="babe")
        else:
            C("create_audio_clip", track=FX, path=paths[kind], warp=False,
              beat=beat(bar) + off, name=f"babe {kind}")


# ---------------------------------------------------------------- v8 (2026-10-20)
# "too many scratches in a row, they can be a detail at a bar change; take only Murder's
# rap without the scratch and use the scratch separately as FX, it really clashes".
# Murder's repeated hook (src 41-48 = the intro) is the DJ-cut part: the break and drop b
# now carry Murder's rap verses (16th-based, over its own guitar riff); its scratch is a
# half-bar FX at two bar changes; the babe variations keep three spots, none in a row.
MURDER_VOX_V8 = [(65, "Murder verse 1"), (89, "Murder verse 2")]
FX_KEEP_V8 = ["babe stutter", "babe reversed into the drop", "babe tapestop",
              "riff swell", "riff stutter"]
MURDER_SCRATCH_AT = [(48, 2), (96, 2)]        # bar, beat: into the riff's groove sections


def v8_murder():
    meta = json.loads((OUT / "phrases.json").read_text())
    C("delete_clips_in_range", track="VOX MURDER", start_bar=1, end_bar=146)
    for bar, name in MURDER_VOX_V8:
        m = meta[name]
        at, beats = beat(bar) - PREROLL, m["beats"] + PREROLL
        C("create_audio_clip", track="VOX MURDER", path=m["path"], beat=at, warp=False,
          name=f"{name} (src bar {m['source_bar']})")
        dur = sf.info(m["path"]).duration - .001
        C("set_warp_markers", track="VOX MURDER", clip={"at": at},
          markers=[[b, min(t, dur)] for b, t in m["markers"]])
        r = C("set_clip", track="VOX MURDER", clip={"at": at}, warping=True,
              warp_mode="complex_pro", looping=False, start_marker=0, end_marker=beats)
        if r.get("length", beats) > beats + .02:
            C("trim_clip", track="VOX MURDER", clip={"at": at}, end_beat=at + beats)
    for c in client.call("get_track", {"track": FX})["clips"]:
        if c["name"] not in FX_KEEP_V8:
            C("delete_clip", track=FX, clip={"at": c["start"]})
    # Murder's scratch: beats 3-4 of its source bar 41, at the source speed (unwarped)
    x, sr = sf.read(SOURCES["MURDER"]["stem"], dtype="float32")
    six = source_sixteenths("MURDER", 41, 1)
    cut = _edge(x[int(six[8] * sr): int(six[16] * sr)].copy(), sr, .004, .03)
    cut *= .5 / max(float(np.abs(cut).max()), 1e-6)
    path = OUT / "Murder scratch - half bar.wav"
    sf.write(path, cut, sr, subtype="PCM_24")
    for bar, b in MURDER_SCRATCH_AT:
        at = beat(bar) + b
        C("create_audio_clip", track=FX, path=str(path), warp=True, beats=2,
          warp_mode="complex_pro", beat=at, name="Murder scratch")
        C("trim_clip", track=FX, clip={"at": at}, end_beat=at + 2)


# "the riffs and the sampled parts are louder than drums and bass: the kick always
# loudest, everything else guided by the kick's level". Targets are each element's
# soloed integrated LUFS over the drop (limiter off) relative to the soloed kick.
LEVELS_VS_KICK = {   # measured v8 (solo, limiter off) -> these; sparse parts read low in LUFS
    "BASS": -3.0, "CLAP": -9.0, "SNARE": -14.8, "HAT 16ths": -17.3,     # hats: he found
    "HAT OFF - persona": -15.8, "CONGAS": -17.0, "SHAKER LOOP": -24.0,    # them loud: kept
    "PERC LOOP": -19.0, "LOOP CITY - orig synth": -17.9, "LOOP MURDER - guitar riff": -12.0,
    "VOX MURDER": -12.0, "FX - babe scratch": -14.0,
}
FOLLOWERS = {"VOX MURDER": ["VOX CITY"], "BASS": ["BASS - break"]}   # same move


def v8_reverbs():
    """Both returns added ~-14 LU against the kick, 75-78 % of it 250 Hz-2 kHz: the strange
    wash in the background. Each now sits ~-20 LU, high-passed above the low mids."""
    C("set_send", track=CITY, send=0, db=-20)
    # a return without a user name is renamed after its chain ("A-Reverb | EQ Eight"):
    # address returns by index
    if "EQ Eight" not in client.call("get_song")["returns"][0]["devices"]:
        C("load_device", track="return:0", query="EQ Eight", roots=["audio_effects"])
    _eq("return:0", 1, "High Pass 48dB", "350 Hz")
    _eq("return:0", 2, "Bell", "600 Hz", "-3.0 dB", "0.80")
    C("set_track", track="return:0", volume_db=-4)
    C("set_param", track="return:2", device="Hybrid Reverb", param="EQ Lo Freq",
      display="500 Hz")
    C("set_param", track="return:2", device="Hybrid Reverb", param="Decay",
      display="4.00 s")
    C("set_track", track="return:2", volume_db=-16)


def v8_levels(measured_json):
    m = json.loads(Path(measured_json).read_text())
    kick = m["KICK"][0]
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    for track, target in LEVELS_VS_KICK.items():
        if track not in m or m[track][0] == float("-inf"):
            continue
        delta = round(target - (m[track][0] - kick), 1)
        for t in [track] + FOLLOWERS.get(track, []):
            C("set_track", track=t, volume_db=round(faders[t] + delta, 1))
        print(f"{track:28s} {m[track][0] - kick:+5.1f} -> {target:+5.1f}  fader {delta:+.1f} dB")


# "the bass lacks sub, this is a club track": the sub plays City 2 City's whole riff at the
# record's own octave (E1 E1 G1 | A1 A1 B1, the D D# E B turn), legato within each
# figure and silent in the holes (beats 2.25-4) that the riffs answer in.
SUB_LEN = {0: .7, .75: .7, 1.5: .75}


def v8_sub():
    for a, b in BASS_RANGES:
        C("delete_clips_in_range", track="SUB", start_bar=a, end_bar=b)
        sub = []
        for k in range((b - a) // 4):
            for t, n, o, d in CITY_BASS:
                base = NOTE_PC[n] + 12 * (o - 1) + 12             # one octave under the bass
                if base < 28:                     # keep E1..D#2: the LOW END bus cuts 34 Hz
                    base += 12
                dur = SUB_LEN.get(round(t % 4, 2), .25)
                sub.append([base, k * 16 + t, dur, 112])
        sub = _feel(sub, "bass")
        if b == 65:
            sub = [x for x in sub if x[1] < (b - a) * 4 - 1]
        C("create_midi_clip", track="SUB", bar=a, length=(b - a) * 4, notes=sub,
          name=f"sub - City riff at E1 {a}")
    C("set_track", track="SUB", volume_db=-5.4)      # soloed: -6 LU under the kick


# ---------------------------------------------------------------- v9 (2026-10-20)
# "the bass has no sub either, it should carry the bounce; tension and release for the
# breaks and drop are missing; didn't like the bass roll; look at 90s house references".
# Two classic edits in his Sexy Vibes folder (Marian "House Music Anthem", Mood Child
# "Believe In Women" Sorel edit) measured: a -3.6/-3.7 LU dip just before every drop,
# builds rising +0.23 LU and +0.6 dB of highs per bar, short 8-32 bar breaks between full
# sections (drop jump 2.4-7.4 LU). So: the bass plays at the record's octave (E1, the sub
# is its own fundamental; the separate sine sub is archived: two E1 sources phase), the
# B-pulse "bass roll" is gone, every build teases the bass riff high-passed (no sub, so
# the drop's sub IS the release), lifts with the reserved open hat and the opening
# filters, and empties the last 2 beats before each drop. Mini-breaks at 29-32 and
# 105-112 repeat tension and release, edit style.
MINI_BREAKS = [(29, 33), (105, 113)]       # kick and bass out
BUILDS = [(29, 33), (73, 81), (109, 113)]  # bass teaser + imite lift
DIPS = [81, 113]                           # the last 2 beats before these are empty
DIP_TRACKS = ["CLAP", "SNARE", "HAT 16ths", "HAT OFF - persona", "HAT OFF - shaker shot",
              "HAT OFF - imite", "CONGAS", "TOM 909", "PERC LOOP", "SHAKER LOOP",
              "LOOP MURDER - guitar riff", CITY, "VOX CITY", "VOX MURDER", "BASS - break"]
TEASER = "BASS - teaser (HP)"


def _filter_notes(track, drop):
    """Rewrite each MIDI clip of `track` without the notes where drop(abs_beat) is true."""
    for c in client.call("get_track", {"track": track})["clips"]:
        if c["type"] != "midi":
            continue
        notes = client.call("get_notes", {"track": track, "clip": {"at": c["start"]}})
        keep = [n for n in notes if not drop(c["start"] + n[1])]
        if len(keep) < len(notes):
            C("add_notes", track=track, clip={"at": c["start"]}, notes=keep, replace=True)


def _in(ranges):
    return lambda t: any(beat(a) - 1e-3 <= t < beat(b) - 1e-3 for a, b in ranges)


def v9_tension():
    # the bass an octave down, at the record's register; the sine sub archived
    for c in client.call("get_track", {"track": "BASS"})["clips"]:
        notes = client.call("get_notes", {"track": "BASS", "clip": {"at": c["start"]}})
        C("add_notes", track="BASS", clip={"at": c["start"]},
          notes=[[n[0] - 12] + n[1:] for n in notes], replace=True)
    C("set_track", track="SUB", name="ARCHIVE - SUB sine (phased with the E1 bass)", mute=True)
    # mini-breaks: kick and bass out
    _filter_notes("KICK", _in(MINI_BREAKS))
    _filter_notes("BASS", _in(MINI_BREAKS))
    # no bass roll: the build's B pulses go
    C("delete_clips_in_range", track="BASS - break", start_bar=77, end_bar=81)
    # the teaser: City's bass riff an octave up, high-passed, velocity rising
    C("create_track", kind="midi", name=TEASER)
    C("load_device", track=TEASER, path=KIT + "C_BinBassTone_01_SP.wav")
    C("set_param", track=TEASER, device=0, param="Volume", value=0)
    C("set_param", track=TEASER, device=0, param="Detune", value=14)
    C("load_device", track=TEASER, query="EQ Eight", roots=["audio_effects"])
    _eq(TEASER, 1, "High Pass 48dB", "250 Hz")
    C("set_track", track=TEASER, volume_db=-12)
    for a, b in BUILDS:
        n_bars = b - a
        notes = []
        for k in range(int(np.ceil(n_bars / 4))):
            for t, n, o, d in CITY_BASS:
                at = k * 16 + t
                if at < n_bars * 4 - 2:                       # out 2 beats before the drop
                    vel = int(70 + 45 * at / (n_bars * 4))
                    notes.append([NOTE_PC[n] + 12 * (o - 1) + 60, at, d, vel])
        C("create_midi_clip", track=TEASER, bar=a, length=n_bars * 4,
          notes=_feel(notes, "bass"), name=f"bass teaser {a}-{b - 1}")
    # the reserved open hat lifts every build
    imite = kits.pattern("let_the_rhythm", 4, ["hat_off_imite"])["hat_off_imite"]
    for a, b in BUILDS:
        lift = [[60] + n[1:] for n in _feel(imite, "hat_off_imite")
                if n[1] < min(b - a, 4) * 4 - 2]
        start = max(a, b - 4)
        C("delete_clips_in_range", track="HAT OFF - imite", start_bar=start, end_bar=b)
        C("create_midi_clip", track="HAT OFF - imite", bar=start, length=(b - start) * 4,
          notes=lift, name=f"lift {start}-{b - 1}")
    # bass soloed -4.9 LU vs the kick at E1: +1.9 to -3. "The clap now sits outside the
    # kit with too much reverb": after its +3.7 dB its drumverb send was the loudest tail;
    # clap 2 dB back, clap and snare nearly dry.
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    for t, d in (("BASS", 1.9), ("BASS - break", 1.9), ("CLAP", -2.0)):
        C("set_track", track=t, volume_db=round(faders[t] + d, 1))
    for t in ("CLAP", "SNARE"):
        C("set_send", track=t, send=0, db=-32)
    # the breath: the last 2 beats before each drop empty (atmosphere and FX stay)
    holes = [(beat(d) - 2, beat(d)) for d in DIPS]
    hole = lambda t: any(a - 1e-3 <= t < b - 1e-3 for a, b in holes)
    for t in DIP_TRACKS:
        info = client.call("get_track", {"track": t})
        if info["kind"] == "midi":
            _filter_notes(t, hole)
        else:
            for c in info["clips"]:
                for a, b in holes:
                    if c["start"] < a < c["end"]:
                        C("trim_clip", track=t, clip={"at": c["start"]}, end_beat=a)


# v9 measured flat builds (73-80 at -16.5..-15.1 LUFS per bar; refs rise ~0.2 LU/bar):
# the build's own parts now also rise in level under their opening filters.
BUILD_RAMP_DB = 7.0     # each build part starts this far under its fader, ends +1 over


def _vol_env(fader, beats, k, n):
    lo = fader - BUILD_RAMP_DB + (BUILD_RAMP_DB + 1) * k / n
    hi = fader - BUILD_RAMP_DB + (BUILD_RAMP_DB + 1) * (k + 1) / n
    return {"param": "volume", "unit": "db", "points": [[0, round(lo, 2)], [beats, round(hi, 2)]]}


def v9_builds():
    meta = json.loads((OUT / "v3.json").read_text())
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    riff = "LOOP MURDER - guitar riff"
    # riff 73-80: break sweep tail (to 2.5 kHz) then open to 18 kHz, rising
    plan = [(73, 1462, 2000), (75, 2000, 2500), (77, 2500, 6700), (79, 6700, 18000)]
    C("delete_clips_in_range", track=riff, start_bar=73, end_bar=81)
    for k, (bar, f0, f1) in enumerate(plan):
        env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                "points": [[0, _raw_hz(f0)], [8, _raw_hz(f1)]]},
               _vol_env(faders[riff], 8, k, len(plan))]
        _place_loop(riff, meta["Murder keys"], bar, env)
        if bar == 79:
            C("trim_clip", track=riff, clip={"at": beat(79)}, end_beat=beat(81) - 2)
    C("delete_clips_in_range", track=riff, start_bar=109, end_bar=113)
    for k, bar in enumerate((109, 111)):
        env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                "points": [[0, _raw_hz(18000)], [8, _raw_hz(18000)]]},
               _vol_env(faders[riff], 8, k, 2)]
        _place_loop(riff, meta["Murder keys"], bar, env)
        if bar == 111:
            C("trim_clip", track=riff, clip={"at": beat(111)}, end_beat=beat(113) - 2)
    # the City preview in the tension rises too
    C("delete_clips_in_range", track=CITY, start_bar=77, end_bar=81)
    a, b, f0, f1 = TENSION_CITY
    path, mk = _section_file("City synth tension", meta["City synth"], b - a)
    at, beats = beat(a), (b - a) * 4 - 2
    env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
            "points": [[0, _raw_hz(f0)], [beats, _raw_hz(f1)]]},
           {"param": "volume", "unit": "db",
            "points": [[0, faders[CITY] - 5], [beats, faders[CITY] + 1]]}]
    C("create_audio_clip", track=CITY, path=path, bar=a, warp=False, name="City synth tension",
      envelopes=env)
    dur = sf.info(path).duration - .001
    C("set_warp_markers", track=CITY, clip={"at": at}, markers=[[x, min(t, dur)] for x, t in mk])
    C("set_clip", track=CITY, clip={"at": at}, warping=True, warp_mode="complex_pro",
      looping=False, start_marker=0, end_marker=beats)
    C("trim_clip", track=CITY, clip={"at": at}, end_beat=at + beats)
    # the bass teaser swells from far away
    for c in client.call("get_track", {"track": TEASER})["clips"]:
        notes = client.call("get_notes", {"track": TEASER, "clip": {"at": c["start"]}})
        L = c["length"]
        C("delete_clip", track=TEASER, clip={"at": c["start"]})
        C("create_midi_clip", track=TEASER, beat=c["start"], length=L, notes=notes,
          name=c["name"], envelopes=[{"param": "volume", "unit": "db",
                                      "points": [[0, faders[TEASER] - 8],
                                                 [L - 2, faders[TEASER] + 2]]}])


# ---------------------------------------------------------------- v10 clap (2026-10-20)
# "the clap sticks out of the mix, something is strange: too many clap variations, or
# too much reverb; the scratch is still too loud". The clap sample carries a ~300 ms room
# (-20 dB at 150 ms, -29 dB at 300 ms) and played 35 hits per 8 bars (pickups, an '& of
# 1', a 32nd ramp); the hook snare layer rings ~150 ms on top. Now: 2 and 4, one pickup
# every 4th bar, 5 ms late; both Simplers in Classic mode with short notes so the
# amplitude release cuts the tail at ~200 ms.
CLAP_LATE_V10 = 0.005 * 125 / 60


def _backbeat(bars, dips=()):
    notes = []
    for b in range(bars):
        for t in (1.0, 3.0):
            notes.append([60, b * 4 + t + CLAP_LATE_V10, .35, 100])
        if b % 4 == 3:
            notes.append([60, b * 4 + 3.75 + CLAP_LATE_V10, .2, 78])
    return notes


def v10_low_end():
    """Low band peaked 60-150 ms after each kick (the bass came back at 70 ms onto the
    kick's body): the kick now owns ~150 ms. Polarity test: +-0.15 dB, kept normal."""
    for t in ("BASS", "BASS - break"):
        names = [d["name"] for d in client.call("get_track", {"track": t})["devices"]]
        if "Compressor" not in names:
            C("load_device", track=t, query="Compressor", roots=["audio_effects"])
            C("set_device_input", track=t, device="Compressor", source="KICK",
              channel="Post Mixer")
            C("set_param", track=t, device="Compressor", param="S/C EQ On", value=0)
        for param, disp in (("Threshold", "-30.0 dB"), ("Ratio", "8.00 : 1"),
                            ("Attack", "0.10 ms"), ("Release", "140 ms")):
            C("set_param", track=t, device="Compressor", param=param, display=disp)
    C("set_param", track="LOW END", device="Glue Compressor", param="Range", display="1.5 dB")


def v10_clap():
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    for t in ("CLAP", "SNARE"):
        C("set_device_prop", track=t, device=0, prop="playback_mode", value=0)   # Classic
        C("set_param", track=t, device=0, param="Ve Release", display="60.0 ms")
        ranges = [(9, END)] if t == "CLAP" else [(33, 41), (57, 65), (81, 97), (113, 121)]
        C("delete_clips_in_range", track=t, start_bar=1, end_bar=146)
        for a, b in ranges:
            notes = [n for n in _backbeat(b - a)
                     if not any(beat(d) - 2 - 1e-3 <= beat(a) + n[1] < beat(d) for d in DIPS)]
            C("create_midi_clip", track=t, bar=a, length=(b - a) * 4, notes=notes,
              name=f"{t.lower()} 2+4 {a}")
    C("set_track", track="CLAP", volume_db=round(faders["CLAP"] - 1.5, 1))
    C("set_track", track=FX, volume_db=round(faders[FX] - 6, 1))


# ---------------------------------------------------------------- v11 character
# "more characteristic ear candy, personality: gangster, rap from the States, a bit UKG;
# tell the story better, use the vocal differently". From the track's own material:
# a radio-filtered Murder line opens the story (9-12); a tape stop of the City synth
# drops into the break; a UKG 2-step riff of pitched "ba" chops (E minor: 0 +3 +5 +8)
# rides the mini-break and the last groove; a DJ rewind fills the breath before the
# final hook.
UKG = "CHOPS - UKG babe"
UKG_RIFF = [(0, 0), (3, 3), (6, 5), (10, 0), (13, 8),            # (16th step, semitones)
            (16 + 2, 5), (16 + 6, 3), (16 + 9, 0), (16 + 12, 8)]
UKG_RANGES = [(105, 113), (121, 129)]


def _resample(x, ratio):
    """Play x `ratio` times faster (pitch and speed, like a turntable)."""
    pos = np.arange(0, len(x) - 1, ratio)
    return np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(x.shape[1])],
                    axis=1).astype(np.float32)


TRANS = "FX - transitions"


def v11_split():
    """The scratches stay low on FX; swells, stutters, tape stop and rewind are transition
    candy on their own track at the old FX level. The UKG riff leaves the last breath."""
    C("create_track", kind="audio", name=TRANS)
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    C("set_track", track=TRANS, volume_db=round(faders[FX] + 6, 1))
    for send, db in ((1, -10), (2, -10)):
        C("set_send", track=TRANS, send=send, db=db)
    for c in client.call("get_track", {"track": FX})["clips"]:
        if c["name"].startswith(("riff", "City tape", "DJ rewind")):
            C("create_audio_clip", track=TRANS, path=c["file"], beat=c["start"], warp=False,
              name=c["name"])
            C("delete_clip", track=FX, clip={"at": c["start"]})
    C("trim_clip", track=UKG, clip={"at": beat(111)}, end_beat=beat(113) - 2)


def v11_character():
    meta = json.loads((OUT / "v3.json").read_text())
    ph = json.loads((OUT / "phrases.json").read_text())
    tempo = client.call("get_song")["tempo"]
    s16 = 60 / tempo / 4
    # radio: Murder's first rap bars band-passed, under the intro
    x, sr = sf.read(ph["Murder verse 1"]["path"], dtype="float32")
    sos = signal.butter(4, [450, 2800], "bandpass", fs=sr, output="sos")
    radio = signal.sosfilt(sos, x, axis=0).astype(np.float32)
    radio = np.tanh(radio * 3) * .3                                  # a little grit
    rpath = OUT / "Murder verse 1 - radio.wav"
    sf.write(rpath, radio, sr, subtype="PCM_24")
    at, beats = beat(9) - PREROLL, 16 + PREROLL
    C("create_audio_clip", track="VOX MURDER", path=str(rpath), beat=at, warp=False,
      name="Murder on the radio (intro)")
    dur = sf.info(str(rpath)).duration - .001
    C("set_warp_markers", track="VOX MURDER", clip={"at": at},
      markers=[[b, min(t, dur)] for b, t in ph["Murder verse 1"]["markers"]])
    C("set_clip", track="VOX MURDER", clip={"at": at}, warping=True, warp_mode="complex_pro",
      looping=False, start_marker=0, end_marker=beats, gain_db=-6)
    C("trim_clip", track="VOX MURDER", clip={"at": at}, end_beat=at + beats)
    # tape stop of the City synth into the break (replaces the stutter there)
    cx, csr = sf.read(meta["City synth"]["path"], dtype="float32")
    half = cx[: int(2 * 60 / 92.017 * csr)]
    pos = np.cumsum(np.linspace(1.0, .15, len(half)))
    pos = pos[pos < len(half) - 1]
    stop = np.stack([np.interp(pos, np.arange(len(half)), half[:, c]) for c in (0, 1)], axis=1)
    stop = _edge(stop.astype(np.float32), csr, .002, .05)[: int(2 * 60 / tempo * csr)]
    spath = OUT / "City synth tape stop.wav"
    sf.write(spath, stop, csr, subtype="PCM_24")
    for c in client.call("get_track", {"track": FX})["clips"]:
        if c["name"] == "riff stutter" and abs(c["start"] - (beat(65) - 1)) < .01:
            C("delete_clip", track=FX, clip={"at": c["start"]})
    C("create_audio_clip", track=FX, path=str(spath), beat=beat(65) - 2, warp=False,
      name="City tape stop into the break")
    # DJ rewind before the final hook: the drop's riff spun back, speeding up
    rx, rsr = sf.read(meta["Murder keys"]["path"], dtype="float32")
    back = rx[::-1].copy()
    pos = np.cumsum(np.linspace(1.0, 4.0, len(back)))
    pos = pos[pos < len(back) - 1][: int(2 * 60 / tempo * rsr)]
    rew = np.stack([np.interp(pos, np.arange(len(back)), back[:, c]) for c in (0, 1)], axis=1)
    rew = _edge(rew.astype(np.float32) * np.linspace(.6, 1, len(rew))[:, None], rsr, .01, .02)
    wpath = OUT / "DJ rewind.wav"
    sf.write(wpath, rew, rsr, subtype="PCM_24")
    for c in client.call("get_track", {"track": FX})["clips"]:
        if c["name"] == "riff swell" and c["start"] > beat(100):
            C("delete_clip", track=FX, clip={"at": c["start"]})
    C("create_audio_clip", track=FX, path=str(wpath), beat=beat(113) - 2, warp=False,
      name="DJ rewind into the final hook")
    # UKG chop riff from the "ba" of babe
    bx, bsr = sf.read(meta["babe1"]["path"], dtype="float32")
    ba = _edge(bx[int(.12 * bsr): int(.12 * bsr) + int(s16 * .9 * bsr)].copy(), bsr, .002, .02)
    two = np.zeros((int(8 * 60 / tempo * bsr), 2), np.float32)
    for step, semi in UKG_RIFF:
        hit = _resample(ba, 2 ** (semi / 12))
        i = int(step * s16 * bsr + (SWING_S * 60 / tempo * bsr if step % 2 else 0))
        two[i: i + len(hit)] += hit[: len(two) - i]
    two *= .5 / max(float(np.abs(two).max()), 1e-6)
    upath = OUT / "UKG babe chop riff (2 bars).wav"
    sf.write(upath, two, bsr, subtype="PCM_24")
    C("create_track", kind="audio", name=UKG)
    C("set_track", track=UKG, volume_db=-16, pan=-0.15)
    C("set_send", track=UKG, send=1, db=-16)
    _eq(UKG, 1, "High Pass 12dB", "300 Hz")
    for a, b in UKG_RANGES:
        for bar in range(a, b, 2):
            C("create_audio_clip", track=UKG, path=str(upath), bar=bar, warp=True, beats=8,
              warp_mode="beats", name="UKG babe chops")


# ---------------------------------------------------------------- v12 DJ friendly
# "in the drop the scratches still sound loud, stealing the whole track; it has to be DJ
# friendly". The drop is instrumental (Murder's 2nd verse carried DJ cuts; the Murder
# scratch at 96 goes too); intro 1-16 and outro 129-144 are drums only for the mix in and
# out; the radio line moves to 17-24, entering with the bass.
def v12_dj():
    for c in client.call("get_track", {"track": "VOX MURDER"})["clips"]:
        if c["name"].startswith(("Murder verse 2", "Murder on the radio")):
            C("delete_clip", track="VOX MURDER", clip={"at": c["start"]})
    for c in client.call("get_track", {"track": FX})["clips"]:
        if c["name"] == "Murder scratch" and c["start"] > beat(90):
            C("delete_clip", track=FX, clip={"at": c["start"]})
    ph = json.loads((OUT / "phrases.json").read_text())
    rpath = str(OUT / "Murder verse 1 - radio.wav")
    at, beats = beat(17) - PREROLL, 32 + PREROLL
    C("create_audio_clip", track="VOX MURDER", path=rpath, beat=at, warp=False,
      name="Murder on the radio (with the bass)")
    dur = sf.info(rpath).duration - .001
    C("set_warp_markers", track="VOX MURDER", clip={"at": at},
      markers=[[b, min(t, dur)] for b, t in ph["Murder verse 1"]["markers"]])
    C("set_clip", track="VOX MURDER", clip={"at": at}, warping=True, warp_mode="complex_pro",
      looping=False, start_marker=0, end_marker=beats, gain_db=-6)
    C("trim_clip", track="VOX MURDER", clip={"at": at}, end_beat=at + beats)
    for c in client.call("get_track", {"track": CITY})["clips"]:
        if c["start"] < beat(17):
            C("delete_clip", track=CITY, clip={"at": c["start"]})
        elif c["start"] < beat(129) < c["end"]:
            C("trim_clip", track=CITY, clip={"at": c["start"]}, end_beat=beat(129))


# ---------------------------------------------------------------- v13 organize
# "the entry at 17 is too abrupt, too much comes in together: present the instruments
# little by little; the low end isn't strong, the bass has to hit and draw the groove;
# too many elements playing, they need organizing". Layers now enter one by one (17 bass,
# 21 radio, 25 congas, 29 the City synth rising in the mini-break, 33 the hook); the
# shaker loop (doubling the shaker shot) and the 909 rim go, the tom keeps only groove C;
# the bass plays longer notes with the bounce on its off-beat hits, a soft saturation for
# harmonics a club system shows, and a sidechain that lets the kick hit then hands over.
def v13_organize():
    # layering into the track
    for c in client.call("get_track", {"track": CITY})["clips"]:
        if c["start"] < beat(29):
            C("delete_clip", track=CITY, clip={"at": c["start"]})
    meta = json.loads((OUT / "v3.json").read_text())
    path, mk = _section_file("City synth enters 29-32", meta["City synth"], 4)
    _place_section(CITY, path, mk, 29, 16, 500, 2500)
    for c in client.call("get_track", {"track": "VOX MURDER"})["clips"]:
        if c["name"].startswith("Murder on the radio"):
            C("delete_clip", track="VOX MURDER", clip={"at": c["start"]})
    ph = json.loads((OUT / "phrases.json").read_text())
    rpath = str(OUT / "Murder verse 1 - radio.wav")
    at, beats = beat(21) - PREROLL, 32 + PREROLL
    C("create_audio_clip", track="VOX MURDER", path=rpath, beat=at, warp=False,
      name="Murder on the radio (bar 21)")
    dur = sf.info(rpath).duration - .001
    C("set_warp_markers", track="VOX MURDER", clip={"at": at},
      markers=[[b, min(t, dur)] for b, t in ph["Murder verse 1"]["markers"]])
    C("set_clip", track="VOX MURDER", clip={"at": at}, warping=True, warp_mode="complex_pro",
      looping=False, start_marker=0, end_marker=beats, gain_db=-6)
    C("trim_clip", track="VOX MURDER", clip={"at": at}, end_beat=min(at + beats, beat(29)))
    _filter_notes("CONGAS", lambda t: beat(17) <= t < beat(25))
    # fewer parts at once
    C("set_track", track="SHAKER LOOP", name="ARCHIVE - SHAKER LOOP (doubled the shaker shot)",
      mute=True)
    C("set_track", track="RIM 909", name="ARCHIVE - RIM 909 (too many parts)", mute=True)
    _filter_notes("TOM 909", lambda t: t < beat(97))
    # the bass hits and draws the groove
    for c in client.call("get_track", {"track": "BASS"})["clips"]:
        notes = client.call("get_notes", {"track": "BASS", "clip": {"at": c["start"]}})
        out = []
        for p_, t, d, v in notes:
            step = round((t % 4) * 4, 1)
            if d >= .3:                                      # the riff's figure, not the turn
                d = .55
            v = 118 if step in (3.0, 3.1, 6.0) else (100 if step == 0 else v)
            out.append([p_, t, d, v])
        C("add_notes", track="BASS", clip={"at": c["start"]}, notes=out, replace=True)
    C("set_param", track="BASS", device=0, param="Vol < Vel", display="60 %")
    names = [d["name"] for d in client.call("get_track", {"track": "BASS"})["devices"]]
    if "Saturator" not in names:
        C("load_device", track="BASS", query="Saturator", roots=["audio_effects"])
    C("set_param", track="BASS", device="Saturator", param="Type", item="Soft Sine")
    C("set_param", track="BASS", device="Saturator", param="Drive", display="5.0 dB")
    C("set_param", track="BASS", device="Saturator", param="Dry/Wet", display="45 %")
    for param, disp in (("Ratio", "6.00 : 1"), ("Release", "110 ms")):
        C("set_param", track="BASS", device="Compressor", param=param, display=disp)


# ---------------------------------------------------------------- v14 low-end polish
# "the low end is still a bit muddy, it deserves polish: presence, headroom". The drop's
# 1/3-octave curve (normalised 200 Hz-5 kHz) against Sexy Vibes' middle half: 32 Hz +6,
# 40-50 Hz +2.9, 125-200 Hz +2.3..+3.0, 630 Hz +4.1 over, 1.6 kHz -2.6 under. Each is
# fixed on the part that makes it; the bass root (E1, 41 Hz) is never high-passed.
def v14_polish():
    _eq("LOW END", 1, "High Pass 48dB", "36.0 Hz")              # 32 Hz rumble, E1 kept
    for t in ("BASS", "BASS - break"):
        names = [d["name"] for d in client.call("get_track", {"track": t})["devices"]]
        if "EQ Eight" not in names:
            C("load_device", track=t, query="EQ Eight", roots=["audio_effects"])
        _eq(t, 2, "Bell", "50.0 Hz", "-2.5 dB", "1.50")         # the kick owns 50 Hz
        _eq(t, 3, "Bell", "180 Hz", "-2.0 dB", "1.00")          # saturated harmonics mud
    for t, hz in (("CONGAS", "140 Hz"), ("TOM 909", "120 Hz")):
        names = [d["name"] for d in client.call("get_track", {"track": t})["devices"]]
        if "EQ Eight" not in names:
            C("load_device", track=t, query="EQ Eight", roots=["audio_effects"])
        _eq(t, 1, "High Pass 12dB", hz)
    riff = "LOOP MURDER - guitar riff"
    _eq(riff, 4, "Bell", "630 Hz", "-2.0 dB", "1.20")
    _eq(riff, 5, "Bell", "1.60 kHz", "1.5 dB", "0.90")          # presence for the lead
    _eq(CITY, 4, "Bell", "630 Hz", "-1.5 dB", "1.20")
    # v14 render: 32 Hz +6.1 -> +2.2, 40 Hz +2.9 -> +0.4; 200 Hz still +2.9 (kick, bass
    # and snare bodies together): one gentle cut on the LOW END bus
    _eq("LOW END", 2, "Bell", "200 Hz", "-2.0 dB", "1.20")


# ---------------------------------------------------------------- v15 the story
# "use the vocals more cleverly and tell the story better". The story is the title: two
# rappers from two cities meeting. Murder (Texas) first on the radio, far; B-Legit's hook
# disclosed in stages (half, then whole with a delay throw); Murder up close in the break;
# the drop instrumental; the final hook trades two bars each (City, Murder, City, Murder);
# the hook's tail closes on the radio. Rap is cut to 4-bar statements with the riffs
# answering, so a vocal is never wallpaper.
STORY = [  # (track, bar, phrase, treatment)
    ("VOX MURDER", 21, "Murder verse 1", "radio"),
    ("VOX CITY", 33, "City hook B half", "dry"),
    ("VOX CITY", 41, "City verse 2 half", "dry"),
    ("VOX CITY", 57, "City hook B", "throw"),
    ("VOX MURDER", 65, "Murder verse 1", "dry"),
    ("VOX CITY", 97, "City verse 3 half", "dry"),
    ("VOX CITY", 113, "City trade 1", "dry"), ("VOX MURDER", 115, "Murder trade 1", "dry"),
    ("VOX CITY", 117, "City trade 2", "dry"), ("VOX MURDER", 119, "Murder trade 2", "throw"),
    ("VOX CITY", 125, "City hook B tail", "radio"),
]


def _radio(path):
    x, sr = sf.read(path, dtype="float32")
    sos = signal.butter(4, [450, 2800], "bandpass", fs=sr, output="sos")
    y = (np.tanh(signal.sosfilt(sos, x, axis=0) * 3) * .3).astype(np.float32)
    out = str(Path(path).with_name(Path(path).stem + " - radio.wav"))
    sf.write(out, y, sr, subtype="PCM_24")
    return out


def _place_vocal(track, bar, m, treatment):
    path = _radio(m["path"]) if treatment == "radio" else m["path"]
    at, beats = beat(bar) - PREROLL, m["beats"] + PREROLL
    env = None
    if treatment == "throw":            # the phrase's last beat into the delay
        env = [{"param": "send:1", "unit": "db",
                "points": [[0, -70], [beats - 1.05, -70], [beats - 1, -4], [beats, -4]]}]
    C("create_audio_clip", track=track, path=path, beat=at, warp=False, envelopes=env,
      name=f"{Path(m['path']).stem} [{treatment}]")
    dur = sf.info(path).duration - .001
    C("set_warp_markers", track=track, clip={"at": at},
      markers=[[b, min(t, dur)] for b, t in m["markers"]])
    C("set_clip", track=track, clip={"at": at}, warping=True, warp_mode="complex_pro",
      looping=False, start_marker=0, end_marker=beats,
      gain_db=-6 if treatment == "radio" else 0)
    r = client.call("get_track", {"track": track})["clips"]
    mine = [c for c in r if abs(c["start"] - at) < .01]
    if mine and mine[0]["end"] > at + beats + .02:
        C("trim_clip", track=track, clip={"at": at}, end_beat=at + beats)


def v15_story():
    meta = json.loads((OUT / "phrases.json").read_text())
    for t in ("VOX CITY", "VOX MURDER"):
        C("delete_clips_in_range", track=t, start_bar=1, end_bar=146)
    for track, bar, name, treatment in STORY:
        _place_vocal(track, bar, meta[name], treatment)
    C("set_track", track="VOX CITY", mute=False)
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    C("set_track", track="VOX CITY", volume_db=faders["VOX MURDER"])
    C("set_send", track="VOX CITY", send=1, db=-70)     # throws only, from the clips


# ---------------------------------------------------------------- v16 theme + the 5 %
# "the earlier vocal dynamic was better; the lead vocal, the theme 'City to City', has
# to appear more, it's the teaser; better build-ups and ear candy; more movement, not
# busier; control energy, attention and release; effects and automation: the 5 % that
# makes it round". Vocals go back to v14's sparse dynamic plus the hook B on both hooks;
# the City call (the hook's first bar, the title line he liked first) is the teaser at
# the turns; hats get a filter automation, the last clap before each section a reverb
# throw, the percussion a slow auto-pan, and the three releases a sub boom.
THEME = [(16, "radio"), (32, "dry"), (36, "dry"), (40, "throw"), (76, "radio"),
         (79, "throw"), (96, "throw")]      # none at 112: the final hook opens with it
HOOKS_V16 = [(57, "City hook B"), (113, "City hook B")]
HAT_FILTER = [  # (bar, Hz) breakpoints for the closed hats' low-pass
    (1, 18000), (29, 3000), (33, 18000), (41, 10000), (57, 18000), (65, 6000), (73, 2500),
    (81, 18000), (97, 9000), (105, 9000), (109, 3000), (113, 18000), (129, 18000),
    (137, 8000), (145, 6000)]
CLAP_THROWS = [32, 56, 64, 96, 112, 128]
BOOMS = [33, 81, 113]


def v16_theme():
    meta = json.loads((OUT / "phrases.json").read_text())
    C("delete_clips_in_range", track="VOX CITY", start_bar=1, end_bar=146)
    for bar, name in HOOKS_V16:
        _place_vocal("VOX CITY", bar, meta[name], "throw")
    for bar, treatment in THEME:
        _place_vocal("VOX CITY", bar, meta["City call"], treatment)
    for c in client.call("get_track", {"track": "VOX MURDER"})["clips"]:
        if "trade" in c["name"]:
            C("delete_clip", track="VOX MURDER", clip={"at": c["start"]})


def v16_movement():
    # closed hats: one clip, its Auto Filter drawn over the whole song
    clip = client.call("get_track", {"track": "HAT 16ths"})["clips"][0]
    notes = client.call("get_notes", {"track": "HAT 16ths", "clip": {"at": clip["start"]}})
    pts = []
    for (b0, f0), (b1, f1) in zip(HAT_FILTER, HAT_FILTER[1:]):
        pts.append([beat(b0) - clip["start"], _raw_hz(f0)])
        pts.append([beat(b1) - clip["start"] - .01, _raw_hz(f1 if f1 > f0 or b1 - b0 <= 8
                                                               else f0)])
    C("delete_clip", track="HAT 16ths", clip={"at": clip["start"]})
    C("create_midi_clip", track="HAT 16ths", beat=clip["start"], length=clip["length"],
      notes=notes, name="hat 16ths (filter drawn)",
      envelopes=[{"param": "Frequency", "device": "Auto Filter", "unit": "raw", "points": pts}])
    # the last clap before each section thrown into the room
    clip = client.call("get_track", {"track": "CLAP"})["clips"][0]
    notes = client.call("get_notes", {"track": "CLAP", "clip": {"at": clip["start"]}})
    sp = [[0, -32]]
    for b in CLAP_THROWS:
        hit = beat(b) - clip["start"] + 3                     # the clap on 4
        if b == 80:
            hit -= 2
        sp += [[hit - .05, -32], [hit, -12], [hit + .9, -12], [hit + .95, -32]]
    C("delete_clip", track="CLAP", clip={"at": clip["start"]})
    C("create_midi_clip", track="CLAP", beat=clip["start"], length=clip["length"], notes=notes,
      name="clap 2+4 (throws)", envelopes=[{"param": "send:0", "unit": "db", "points": sp}])
    # the percussion breathes side to side, slowly (above the low end: it is high-passed)
    C("set_param", track="PERC LOOP", device="Auto Pan", param="Time Mode", item="Synced")
    C("set_param", track="PERC LOOP", device="Auto Pan", param="Rate", value=4)   # "2" bars
    C("set_param", track="PERC LOOP", device="Auto Pan", param="Amount", display="25 %")
    # sub boom on each release: a 62 -> 38 Hz sine sweep under the kick
    sr = 44100
    t = np.arange(int(1.1 * sr)) / sr
    f = 38 + 24 * np.exp(-t / .18)
    y = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.minimum(1, t / .005) * np.exp(-t / .45)
    boom = np.stack([y, y], axis=1).astype(np.float32) * .5
    bpath = OUT / "Sub boom 62-38 Hz.wav"
    sf.write(bpath, boom, sr, subtype="PCM_24")
    if not any(x["name"] == "FX - sub boom" for x in client.call("get_song")["tracks"]):
        C("create_track", kind="audio", name="FX - sub boom")
        C("set_track_output", track="FX - sub boom", dest="LOW END")
        C("set_track", track="FX - sub boom", volume_db=-8)   # peak ~7 dB under the kick
    for b in BOOMS:
        C("create_audio_clip", track="FX - sub boom", path=str(bpath), bar=b, warp=False,
          name="sub boom (release)")


# ---------------------------------------------------------------- v17 drums alive
# "the dynamics can still move; hat variations, they sound very straight; since the clap
# went down the rest of the drums lacks a bit". The hats had lost the kit's accent map
# (it came from the pool groove's velocity, neutralised to avoid double swing): on-beat
# 16ths ~11 dB under the off-beat 8ths. The 16ths now carry that map in their velocities
# (Simpler Vol<Vel 100 %), swing a little more (~57 %), drop one 16th every 2nd bar for a
# pocket, and flutter in 32nds at the end of every 8-bar phrase; the off-beat hat
# alternates strong/soft; congas fill the last two beats of each 8-bar phrase.
HAT_ACCENT_DB = [-10.8, -2.4, -0.5, -2.0, -11.3, -3.4, -0.4, -2.6,
                 -11.9, -3.4, -0.8, -2.4, -10.5, -2.8, -0.8, -1.6]   # kit's measured map
HAT_SWING_EXTRA = 0.005 * 125 / 60


def v17_drums():
    rng = np.random.default_rng(17)
    dips = [(beat(d) - 2, beat(d)) for d in DIPS]
    in_dip = lambda t: any(a - 1e-3 <= t < b for a, b in dips)
    # closed 16ths: rebuild the notes inside the existing (filter-drawn) clip
    clip = client.call("get_track", {"track": "HAT 16ths"})["clips"][0]
    old = client.call("get_notes", {"track": "HAT 16ths", "clip": {"at": clip["start"]}})
    bars = int(round(clip["length"] / 4))
    present = {round(round((n[1] - (SWING_S if round(n[1] * 4) % 2 else 0)) * 4)) for n in old}
    notes = []
    for b in range(bars):
        absbar = int(clip["start"] / 4) + b + 1
        for st in range(16):
            k = b * 16 + st
            if k not in present:
                continue
            if b % 2 == 1 and st == 7:                       # a pocket every 2nd bar
                continue
            t = k / 4 + ((SWING_S + HAT_SWING_EXTRA) if st % 2 else 0)
            if absbar % 8 == 0 and st >= 14:                 # 32nd flutter into the phrase
                for q in range(2):
                    tt = (b * 16 + st) / 4 + q * .125
                    if not in_dip(clip["start"] + tt):
                        notes.append([60, tt, .1, int(70 + 10 * q + 6 * (st - 14))])
                continue
            if in_dip(clip["start"] + t):
                continue
            v = int(np.clip(127 * 10 ** (HAT_ACCENT_DB[st] / 20) + rng.integers(-4, 5), 20, 127))
            notes.append([60, round(t, 4), .1, v])
    C("add_notes", track="HAT 16ths", clip={"at": clip["start"]}, notes=notes, replace=True)
    C("set_param", track="HAT 16ths", device=0, param="Vol < Vel", display="100 %")
    # off-beat hat: strong / soft alternation
    for c in client.call("get_track", {"track": "HAT OFF - persona"})["clips"]:
        ns = client.call("get_notes", {"track": "HAT OFF - persona", "clip": {"at": c["start"]}})
        out = [[p_, t, d, 108 if int(round((t - .5) * 2)) % 2 == 0 else 84] for p_, t, d, v in ns]
        C("add_notes", track="HAT OFF - persona", clip={"at": c["start"]}, notes=out,
          replace=True)
    C("set_param", track="HAT OFF - persona", device=0, param="Vol < Vel", display="60 %")
    # conga fills: the last two beats of each 8-bar phrase
    pads = [38, 40, 43, 45, 43, 40, 38, 45]
    for c in client.call("get_track", {"track": "CONGAS"})["clips"]:
        ns = client.call("get_notes", {"track": "CONGAS", "clip": {"at": c["start"]}})
        a = int(c["start"] / 4) + 1
        for bar in range(a, a + int(round(c["length"] / 4))):
            if bar % 8 or any(abs(beat(bar + 1) - d) < 1e-3 for d in [beat(x) for x in DIPS]):
                continue
            t0 = beat(bar) - c["start"] + 2
            ns = [n for n in ns if not (t0 - 1e-3 <= n[1] < t0 + 2)]
            ns += [[pads[i], round(t0 + i * .25 + (SWING_S if i % 2 else 0), 4), .2,
                    62 + 4 * i] for i in range(8)]
        C("add_notes", track="CONGAS", clip={"at": c["start"]}, notes=sorted(ns, key=lambda n: n[1]),
          replace=True)
    # the drums' body back
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    for t, d in (("CLAP", 1.5), ("HAT OFF - persona", 1.0), ("CONGAS", 1.5), ("PERC LOOP", 1.0)):
        C("set_track", track=t, volume_db=round(faders[t] + d, 1))


# ---------------------------------------------------------------- v18 mix: glue + space
# "the drum mix is still bad: fit everything, glue it, adjust volumes; treat the voices
# too, automate, use reverbs and delays: take it to the next level". The kit's DRUMS bus
# (Glue 2:1, 10 ms, range 4 dB, high shelf -2.5 dB at 9 kHz) glues every drum but the
# kick; one short room (D-Room) replaces the generic reverb on all of them; the voices get
# their own plate (E-Plate) and a filtered dotted delay for throws; in the break Murder's
# voice opens from the radio's band to full over two bars.
DRUM_BUS = "DRUMS"
DRUM_PARTS = {  # track: room send dB
    "CLAP": -16, "SNARE": -18, "HAT 16ths": -21, "HAT OFF - persona": -20,
    "HAT OFF - shaker shot": -21, "HAT OFF - imite": -21, "CONGAS": -18, "TOM 909": -19,
    "RIDE 909": -24, "CRASH 909": -22, "PERC LOOP": -20,
}
ROOM, PLATE = 3, 4      # return indices (D-Room, E-Plate)


def v18_mix():
    # returns
    for param, disp in (("Decay Time", "0.80 s"), ("Predelay", "5.00 ms"),
                        ("Input Freq", "2.50 kHz"), ("Input Width", "6.00 "),
                        ("Room Size", "40.00 "), ("Dry/Wet", "100 %")):
        C("set_param", track=f"return:{ROOM}", device="Reverb", param=param, display=disp)
    C("set_param", track=f"return:{ROOM}", device="Reverb", param="In Lo Cut On", value=1)
    for param, disp in (("Decay Time", "1.40 s"), ("Predelay", "25.0 ms"),
                        ("Input Freq", "2.00 kHz"), ("Input Width", "5.00 "),
                        ("Room Size", "70.00 "), ("Dry/Wet", "100 %")):
        C("set_param", track=f"return:{PLATE}", device="Reverb", param=param, display=disp)
    C("set_param", track=f"return:{PLATE}", device="Reverb", param="In Lo Cut On", value=1)
    C("set_track", track=f"return:{ROOM}", volume_db=-8)
    C("set_track", track=f"return:{PLATE}", volume_db=-8)
    C("set_param", track="return:1", device="Delay", param="R 16th", value=4)       # 1/4
    C("set_param", track="return:1", device="Delay", param="L 16th", value=3)       # 3/16
    C("set_param", track="return:1", device="Delay", param="Feedback", display="35 %")
    C("set_param", track="return:1", device="Delay", param="Filter On", value=1)
    C("set_param", track="return:1", device="Delay", param="Filter Freq", display="1.50 kHz")
    C("set_param", track="return:1", device="Delay", param="Filter Width", display="6.00 ")
    # the drum bus
    if not any(t["name"] == DRUM_BUS for t in client.call("get_song")["tracks"]):
        C("create_track", kind="audio", name=DRUM_BUS)
        C("set_track_input", track=DRUM_BUS, source="No Input")
        C("set_track", track=DRUM_BUS, monitoring="in")
        C("load_device", track=DRUM_BUS, query="Glue Compressor", roots=["audio_effects"])
    for param, disp in (("Attack", "10"), ("Ratio", "2"), ("Threshold", "-18.0 dB"),
                        ("Range", "4.00 dB"), ("Output", "1.00 dB")):
        C("set_param", track=DRUM_BUS, device="Glue Compressor", param=param, display=disp)
    _eq(DRUM_BUS, 7, "High Shelf", "9.00 kHz", "-2.5 dB")
    for t, room in DRUM_PARTS.items():
        C("set_track_output", track=t, dest=DRUM_BUS)
        C("set_send", track=t, send=0, db=-70)
        C("set_send", track=t, send=ROOM, db=room)
    # voices: own plate, no generic reverb, a little density
    for t in ("VOX CITY", "VOX MURDER"):
        C("set_send", track=t, send=0, db=-70)
        C("set_send", track=t, send=PLATE, db=-14)
        names = [d["name"] for d in client.call("get_track", {"track": t})["devices"]]
        if "Saturator" not in names:
            C("load_device", track=t, query="Saturator", roots=["audio_effects"])
        C("set_param", track=t, device="Saturator", param="Drive", display="3.0 dB")
        C("set_param", track=t, device="Saturator", param="Dry/Wet", display="30 %")
    for t in (FX, UKG):
        C("set_send", track=t, send=0, db=-70)
        C("set_send", track=t, send=PLATE, db=-16)
    # the break: Murder's voice opens from the radio band to full
    names = [d["name"] for d in client.call("get_track", {"track": "VOX MURDER"})["devices"]]
    if "Auto Filter" not in names:
        C("load_device", track="VOX MURDER", query="Auto Filter", roots=["audio_effects"])
    C("set_param", track="VOX MURDER", device="Auto Filter", param="Frequency", display="18.0 kHz")
    meta = json.loads((OUT / "phrases.json").read_text())
    m = meta["Murder verse 1"]
    for c in client.call("get_track", {"track": "VOX MURDER"})["clips"]:
        if abs(c["start"] - (beat(65) - PREROLL)) < .01:
            C("delete_clip", track="VOX MURDER", clip={"at": c["start"]})
    at, beats = beat(65) - PREROLL, m["beats"] + PREROLL
    env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
            "points": [[0, _raw_hz(1200)], [8.5, _raw_hz(18000)], [beats, _raw_hz(18000)]]}]
    C("create_audio_clip", track="VOX MURDER", path=m["path"], beat=at, warp=False,
      envelopes=env, name="Murder verse 1 - radio opens to the room")
    dur = sf.info(m["path"]).duration - .001
    C("set_warp_markers", track="VOX MURDER", clip={"at": at},
      markers=[[b, min(t, dur)] for b, t in m["markers"]])
    C("set_clip", track="VOX MURDER", clip={"at": at}, warping=True, warp_mode="complex_pro",
      looping=False, start_marker=0, end_marker=beats)


# ================================================================ v19: the club mix form
# "it lacks a club track's structure: two drops, the intro, the outro, a first drop and a
# second drop stronger, with more energy, tension, release, effects, crash, growth,
# build-up... always a club mix to dance to, not pop". The whole arrangement is rebuilt
# from one section map (192 bars at 125 BPM, ~6:08), every part placed by the sections it
# belongs to. Mix settings (buses, returns, EQs, levels) stay as v18 left them.
END19 = 193
SECTIONS19 = [  # (first bar, name for the locator)
    (1, "INTRO A - drums (DJ)"), (17, "INTRO B - bass, Murder on the radio"),
    (33, "GROOVE - City synth, the theme calls"), (49, "BREAK 1 - hook B, no kick"),
    (57, "BUILD 1 - everything rises, breath"), (65, "DROP 1 - hook B, release"),
    (97, "BREAK 2 - Murder from the radio to the room"), (113, "BUILD 2 - bigger, the V"),
    (129, "DROP 2 - everything, strongest"), (161, "OUTRO A - closing"),
    (177, "OUTRO B - drums (DJ)")]
DIPS19 = [65, 129]                   # 2 empty beats before the drops
KICK_HOLES19 = [32, 48, 80, 88, 96, 144, 152]
P19 = {  # MIDI drum parts: ranges [a, b)
    "KICK": [(1, 49), (65, 97), (129, END19)],
    "CLAP": [(9, 49), (57, 97), (113, END19)],
    "SNARE": [(73, 97), (129, 161)],
    "HAT OFF - persona": [(9, 49), (57, 97), (113, END19)],
    "HAT OFF - shaker shot": [(9, 49), (57, 97), (105, END19)],
    "HAT OFF - imite": [(61, 65), (81, 97), (121, 161)],
    "CONGAS": [(25, 49), (65, 97), (105, 113), (129, 177)],
    "TOM 909": [(41, 49), (89, 97), (145, 161)],
    "RIDE 909": [(81, 97), (129, 161)],
}
HATS19 = [(1, 97), (105, END19)]
HAT_FILTER19 = [(1, 6000), (9, 18000), (49, 6000), (57, 2500), (65, 18000), (105, 4000),
                (113, 2500), (129, 18000), (177, 18000), (189, 5000), (193, 4000)]
CLAP_THROWS19 = [32, 48, 64, 96, 128, 160, 176]
CRASH19 = [17, 33, 65, 81, 129, 145, 161, 177]
PERC19 = [(1, 49), (57, 97), (113, END19)]
BASS19 = [(17, 49), (65, 97), (129, 177)]
BREAK_BASS19 = (  # (bar, note, octave) one long note a bar: i iv i iv | i iv VI VII ... V
    [(b, "E" if (b - 49) % 4 < 2 else "A", 1) for b in range(49, 57)] +
    [(b, n, 1) for b, n in zip(range(97, 113), "EEAAEEAACCDDEEAA")] +
    [(b, "B", 1) for b in range(121, 129)])
TEASER19 = [(57, 65), (113, 129)]
BOOMS19 = [33, 65, 129]
CITY19 = [  # (a, b, Hz from, Hz to, volume ramp?)
    (29, 33, 500, 2500, False), (33, 49, 1200, 1800, False), (49, 57, 900, 900, False),
    (57, 65, 900, 6000, True), (65, 97, 6000, 6000, False), (113, 121, 500, 2500, True),
    (121, 129, 2500, 6000, True), (129, 161, 6000, 6000, False), (161, 177, 2500, 400, False)]
RIFF19 = [
    (41, 49, 1500, 4000, False), (49, 57, 800, 800, False), (57, 65, 1500, 18000, True),
    (73, 97, 18000, 18000, False), (97, 105, 600, 2500, False), (105, 113, 2500, 5000, False),
    (113, 121, 18000, 18000, True), (121, 129, 18000, 18000, True),
    (129, 161, 18000, 18000, False), (161, 169, 18000, 3000, False)]
ATMOS19 = [(49, 65), (97, 129), (129, 161), (161, 177)]
UKG19 = [(89, 97), (145, 161), (169, 177)]
VOCALS19 = [  # (track, bar, phrase, treatment)
    ("VOX MURDER", 21, "Murder verse 1", "radio"),
    ("VOX CITY", 32, "City call", "dry"), ("VOX CITY", 36, "City call", "dry"),
    ("VOX CITY", 40, "City call", "throw"), ("VOX CITY", 49, "City hook B", "plate"),
    ("VOX CITY", 60, "City call", "radio"), ("VOX CITY", 63, "City call", "throw"),
    ("VOX CITY", 65, "City hook B", "throw"), ("VOX CITY", 80, "City call", "throw"),
    ("VOX CITY", 88, "City call", "dry"), ("VOX CITY", 96, "City call", "throw"),
    ("VOX MURDER", 97, "Murder verse 1", "opens"), ("VOX CITY", 105, "City hook A", "plate"),
    ("VOX CITY", 124, "City call", "dry"), ("VOX CITY", 126, "City call", "dry"),
    ("VOX CITY", 129, "City hook B", "throw"), ("VOX CITY", 144, "City call", "throw"),
    ("VOX CITY", 152, "City call", "throw"), ("VOX CITY", 169, "City hook B tail", "radio"),
]
ACCEL19 = [(127, 0), (127, 2)]       # half-bar theme calls accelerating into the breath
TRANS19 = [("Riff reversed swell.wav", 33, "end"), ("Riff stutter 1 beat.wav", 41, "end"),
           ("Riff stutter 1 beat.wav", 49, "end"), ("City synth tape stop.wav", 97, "end"),
           ("DJ rewind.wav", 129, "end")]
SCRATCH19 = [("Murder scratch - half bar.wav", 48, 2, True), ("Babe scratch - stutter.wav", 112, 2, False),
             ("Murder scratch - half bar.wav", 152, 2, True), ("Babe scratch - tapestop.wav", 176, 2, False)]


def _hat_notes19(a, b, rng):
    notes = []
    for bar in range(a, b):
        base = (bar - a) * 4
        for st in range(16):
            if (bar - a) % 2 == 1 and st == 7:
                continue
            t = base + st / 4 + ((SWING_S + HAT_SWING_EXTRA) if st % 2 else 0)
            if bar % 8 == 0 and st >= 14:
                for q in range(2):
                    notes.append([60, base + st / 4 + q * .125, .1, int(70 + 10 * q + 6 * (st - 14))])
                continue
            v = int(np.clip(127 * 10 ** (HAT_ACCENT_DB[st] / 20) + rng.integers(-4, 5), 20, 127))
            notes.append([60, round(t, 4), .1, v])
    return notes


def _filter_env(points_bars, a, b):
    """A raw Auto Filter envelope for a clip [a, b) from (bar, Hz) breakpoints."""
    pts = []
    for (b0, f0), (b1, f1) in zip(points_bars, points_bars[1:]):
        lo, hi = max(a, b0), min(b, b1)
        if lo >= hi:
            continue
        frac = lambda x: (x - b0) / (b1 - b0)
        g = lambda x: f0 * (f1 / f0) ** frac(x)
        pts += [[beat(lo) - beat(a), _raw_hz(g(lo))], [beat(hi) - beat(a) - .01, _raw_hz(g(hi))]]
    return [{"param": "Frequency", "device": "Auto Filter", "unit": "raw", "points": pts}]


def _place_section19(track, path, mk, a, beats, envs):
    at = beat(a)
    C("create_audio_clip", track=track, path=path, beat=at, warp=False,
      name=Path(path).stem, envelopes=envs or None)
    dur = sf.info(path).duration - .001
    C("set_warp_markers", track=track, clip={"at": at}, markers=[[x, min(t, dur)] for x, t in mk])
    C("set_clip", track=track, clip={"at": at}, warping=True, warp_mode="complex_pro",
      looping=False, start_marker=0, end_marker=beats)
    mine = [c for c in client.call("get_track", {"track": track})["clips"]
            if abs(c["start"] - at) < .01]
    if mine and mine[0]["end"] > at + beats + .02:
        C("trim_clip", track=track, clip={"at": at}, end_beat=at + beats)


def _loop_sections19(track, m, plan, faders, filt=True):
    for a, b, f0, f1, ramp in plan:
        path, mk = _section_file(f"{Path(m['path']).stem[:10]} {a}-{b - 1}", m, b - a)
        beats = (b - a) * 4 - (2 if b in DIPS19 else 0)
        envs = []
        if filt:
            envs.append({"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                         "points": [[0, _raw_hz(f0)], [beats, _raw_hz(f1)]]})
        if ramp:
            envs.append({"param": "volume", "unit": "db",
                         "points": [[0, faders[track] - 6], [beats, faders[track] + 1]]})
        _place_section19(track, path, mk, a, beats, envs)


def arrange_v19():
    rng = np.random.default_rng(19)
    meta = json.loads((OUT / "v3.json").read_text())
    ph = json.loads((OUT / "phrases.json").read_text())
    tracks = {t["name"]: t for t in client.call("get_song")["tracks"]}
    faders = {n: t["vol_db"] for n, t in tracks.items()}
    content = [n for n, t in tracks.items() if not n.startswith("ARCHIVE")
               and n not in ("LOW END", DRUM_BUS)]
    for n in content:
        C("delete_clips_in_range", track=n, start_bar=1, end_bar=END19 + 8)
    dip_beats = [(beat(d) - 2, beat(d)) for d in DIPS19]
    in_dip = lambda t: any(x - 1e-3 <= t < y for x, y in dip_beats)
    # ---- drums
    for track, ranges in P19.items():
        part = {"KICK": "kick", "HAT OFF - persona": "hat_off_persona",
                "HAT OFF - shaker shot": "hat_off_shaker_shot", "HAT OFF - imite": "hat_off_imite",
                "CONGAS": "congas", "TOM 909": "tom_909", "RIDE 909": "ride"}.get(track)
        for a, b in ranges:
            if track in ("CLAP", "SNARE"):
                notes = _backbeat(b - a)
            else:
                notes = _drum_notes(part, b - a)
            if track == "HAT OFF - persona":
                notes = [[p_, t, d, 108 if int(round((t - .5) * 2)) % 2 == 0 else 84]
                         for p_, t, d, v in notes]
            if track == "KICK":
                holes = [beat(h) + 3 - beat(a) for h in KICK_HOLES19 if a <= h < b]
                notes = [n for n in notes if all(abs(n[1] - h) > 1e-3 for h in holes)]
            if track == "CONGAS":
                pads = [38, 40, 43, 45, 43, 40, 38, 45]
                for bar in range(a, b):
                    if bar % 8 == 0 and bar + 1 not in DIPS19:
                        t0 = beat(bar) - beat(a) + 2
                        notes = [n for n in notes if not (t0 - 1e-3 <= n[1] < t0 + 2)]
                        notes += [[pads[i], round(t0 + i * .25 + (SWING_S if i % 2 else 0), 4),
                                   .2, 62 + 4 * i] for i in range(8)]
            notes = [n for n in notes if not in_dip(beat(a) + n[1])]
            envs = None
            if track == "CLAP":
                sp = [[0, -32]]
                for tb in CLAP_THROWS19:
                    if a <= tb < b:
                        hit = beat(tb) - beat(a) + (1 if tb + 1 in DIPS19 else 3)
                        sp += [[hit - .05, -32], [hit, -12], [hit + .9, -12], [hit + .95, -32]]
                envs = [{"param": "send:3", "unit": "db", "points": sp}]
            C("create_midi_clip", track=track, bar=a, length=(b - a) * 4,
              notes=sorted(notes, key=lambda n: n[1]), name=f"{track.lower()} {a}-{b - 1}",
              envelopes=envs)
    for a, b in HATS19:
        notes = [n for n in _hat_notes19(a, b, rng) if not in_dip(beat(a) + n[1])]
        C("create_midi_clip", track="HAT 16ths", bar=a, length=(b - a) * 4, notes=notes,
          name=f"hats {a}-{b - 1}", envelopes=_filter_env(HAT_FILTER19, a, b))
    crash = kits.pattern("let_the_rhythm", 1, ["crash"])["crash"][0]
    for bar in CRASH19:
        C("create_midi_clip", track="CRASH 909", bar=bar, length=4,
          notes=[[crash[0], 0, 1, crash[3]]], name="section crash")
    perc = str(LOOP_DIR / LOOPS["PERC LOOP"][0])
    for a, b in PERC19:
        C("create_audio_clip", track="PERC LOOP", path=perc, bar=a, warp=True, beats=16,
          warp_mode="beats", name=f"perc loop {a}")
        fill_loop("PERC LOOP", a, b - (.5 if b in DIPS19 else 0), 16)
    # ---- bass
    for a, b in BASS19:
        notes = []
        for k in range((b - a) // 4):
            for t, n, o, d in CITY_BASS:
                step = round((t % 4) * 4)
                pitch = NOTE_PC[n] + 12 * (o - 2) + 60
                pitch += 12 if pitch < 64 else 0          # nothing under E1: LOW END cuts 36 Hz
                notes.append([pitch, k * 16 + t,
                              .55 if d >= .3 else d, 118 if step in (3, 6) else 100])
        holes = [beat(h) + 3 - beat(a) for h in KICK_HOLES19 if a <= h < b]
        notes = [x for x in _feel(notes, "bass") if all(not (h - 1e-3 <= x[1] < h + 1) for h in holes)]
        C("create_midi_clip", track="BASS", bar=a, length=(b - a) * 4, notes=notes,
          name=f"City 2 City bass {a}")
    for bar, n, o in BREAK_BASS19:
        dur = 3.5 if bar + 1 not in DIPS19 else 1.9
        C("create_midi_clip", track="BASS - break", bar=bar, length=4,
          notes=[[(lambda p_: p_ + 12 if p_ < 64 else p_)(NOTE_PC[n] + 12 * (o - 1) + 60), 0, dur, 96 + (bar - 121) * 3 if bar >= 121 else 96]],
          name=f"break bass {n}")
    for a, b in TEASER19:
        n_bars = b - a
        notes = []
        for k in range(n_bars // 4):
            for t, n, o, d in CITY_BASS:
                at = k * 16 + t
                if at < n_bars * 4 - 2:
                    notes.append([NOTE_PC[n] + 12 * (o - 1) + 60, at, d, int(70 + 45 * at / (n_bars * 4))])
        C("create_midi_clip", track=TEASER, bar=a, length=n_bars * 4, notes=_feel(notes, "bass"),
          name=f"bass teaser {a}", envelopes=[{"param": "volume", "unit": "db", "points":
                                               [[0, faders[TEASER] - 8], [n_bars * 4 - 2, faders[TEASER] + 2]]}])
    boom = str(OUT / "Sub boom 62-38 Hz.wav")
    for bar in BOOMS19:
        C("create_audio_clip", track="FX - sub boom", path=boom, bar=bar, warp=False, name="sub boom")
    # ---- loops, atmosphere, chops
    _loop_sections19(CITY, meta["City synth"], CITY19, faders)
    _loop_sections19("LOOP MURDER - guitar riff", meta["Murder keys"], RIFF19, faders)
    _loop_sections19("ATMOS - riff wash", meta["Murder keys"],
                     [(a, b, 0, 0, False) for a, b in ATMOS19], faders, filt=False)
    ukg = str(OUT / "UKG babe chop riff (2 bars).wav")
    for a, b in UKG19:
        for bar in range(a, b, 2):
            C("create_audio_clip", track=UKG, path=ukg, bar=bar, warp=True, beats=8,
              warp_mode="beats", name="UKG babe chops")
    # ---- vocals
    for track, bar, name, treatment in VOCALS19:
        m = ph[name]
        if treatment == "opens":
            at, beats = beat(bar) - PREROLL, m["beats"] + PREROLL
            env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                    "points": [[0, _raw_hz(1200)], [8.5, _raw_hz(18000)], [beats, _raw_hz(18000)]]}]
            _place_section19(track, m["path"], m["markers"], bar - PREROLL / 4, beats, env)
        elif treatment == "plate":
            _place_vocal(track, bar, m, "dry")
        else:
            _place_vocal(track, bar, m, treatment)
    call = ph["City call"]
    for bar, off in ACCEL19:
        at = beat(bar) + off - .25
        C("create_audio_clip", track="VOX CITY", path=call["path"], beat=at, warp=False,
          name="theme accelerating")
        dur = sf.info(call["path"]).duration - .001
        C("set_warp_markers", track="VOX CITY", clip={"at": at},
          markers=[[x, min(t, dur)] for x, t in call["markers"]])
        C("set_clip", track="VOX CITY", clip={"at": at}, warping=True, warp_mode="complex_pro",
          looping=False, start_marker=PREROLL - .25, end_marker=PREROLL + 2)
        C("trim_clip", track="VOX CITY", clip={"at": at}, end_beat=min(at + 2.25, beat(129) - 2))
    # ---- FX
    tempo = client.call("get_song")["tempo"]
    for f, bar, how in TRANS19:
        path = str(OUT / f)
        L = sf.info(path).duration * tempo / 60
        C("create_audio_clip", track=TRANS, path=path, beat=beat(bar) - L, warp=False,
          name=Path(f).stem)
    rev = str(OUT / "Babe chop 1 - reversed.wav")
    L = sf.info(rev).duration * tempo / 60
    C("create_audio_clip", track=FX, path=rev, beat=beat(65) - L, warp=False, name="babe reversed")
    for f, bar, b_, warp in SCRATCH19:
        at = beat(bar) + b_
        if warp:
            C("create_audio_clip", track=FX, path=str(OUT / f), beat=at, warp=True, beats=2,
              warp_mode="complex_pro", name=Path(f).stem)
            C("trim_clip", track=FX, clip={"at": at}, end_beat=at + 2)
        else:
            C("create_audio_clip", track=FX, path=str(OUT / f), beat=at, warp=False, name=Path(f).stem)
    # locators last: Live refuses a cue beyond the song's current length
    C("clear_cues")
    for bar, name in SECTIONS19:
        C("set_cue", bar=bar, name=name)


# ---------------------------------------------------------------- v19 organisation
# "clean the channels, group, work the buses, it's very disorganised; organise with
# colours by frequency". Live's API neither groups nor reorders tracks: rejected
# archives are deleted (this script recreates any of them), the originals become muted
# REF tracks, VOX / MUSIC / FX buses are inserted next to their parts, and every track
# takes the colour of its band and role.
REJECTED = ["ARCHIVE - RIM 909 (too many parts)", "ARCHIVE - SHAKER LOOP (doubled the shaker shot)",
            "ARCHIVE - SUB sine (phased with the E1 bass)", "ARCHIVE - KEYS house stab (rejected)"]
BUSES = {  # bus: (members, insert after)
    "VOX BUS": (["VOX CITY", "VOX MURDER"], "VOX MURDER"),
    "MUSIC BUS": (["LOOP CITY - orig synth", "LOOP MURDER - guitar riff", UKG], UKG),
    "FX BUS": ([FX, TRANS], TRANS),
}
COLOURS = {  # Live palette index: red low end, orange drum body, yellow hats/cymbals,
    # brown percussion, green harmony, cyan atmosphere, violet voice, pink FX, grey refs
    14: ["KICK", "BASS", "BASS - break", "BASS - teaser (HP)", "FX - sub boom"],
    15: ["CLAP", "SNARE"],
    17: ["HAT 16ths", "HAT OFF - persona", "HAT OFF - shaker shot", "HAT OFF - imite",
         "RIDE 909", "CRASH 909"],
    16: ["CONGAS", "TOM 909", "PERC LOOP"],
    19: ["LOOP CITY - orig synth", "LOOP MURDER - guitar riff", UKG],
    21: ["ATMOS - riff wash"],
    24: ["VOX CITY", "VOX MURDER"],
    26: [FX, TRANS],
    1: ["LOW END"], 2: [DRUM_BUS], 4: ["MUSIC BUS"], 11: ["VOX BUS"], 12: ["FX BUS"],
    27: ["REF - City 2 City (original)", "REF - Murder (original)"],
}


def organise_v19():
    names = [t["name"] for t in client.call("get_song")["tracks"]]
    for n in REJECTED:
        if n in names:
            C("delete_track", track=n)
    for t in client.call("get_song")["tracks"]:
        if t["name"].startswith("ARCHIVE original") and "City 2 City" in t["name"]:
            C("set_track", track=t["i"], name="REF - City 2 City (original)", mute=True)
        elif t["name"].startswith("ARCHIVE original") and "Murder" in t["name"]:
            C("set_track", track=t["i"], name="REF - Murder (original)", mute=True)
    for bus, (members, after) in BUSES.items():
        tracks = client.call("get_song")["tracks"]
        if not any(t["name"] == bus for t in tracks):
            idx = [t["i"] for t in tracks if t["name"] == after][0] + 1
            C("create_track", kind="audio", name=bus, index=idx)
            C("set_track_input", track=bus, source="No Input")
            C("set_track", track=bus, monitoring="in")
        for m in members:
            C("set_track_output", track=m, dest=bus)
    # bus processing: a voice that sits as one, music that breathes with the kick
    C("load_device", track="VOX BUS", query="Compressor", roots=["audio_effects"])
    for param, disp in (("Threshold", "-18.0 dB"), ("Ratio", "2.00 : 1"),
                        ("Attack", "10.0 ms"), ("Release", "100 ms")):
        C("set_param", track="VOX BUS", device="Compressor", param=param, display=disp)
    _eq("VOX BUS", 1, "High Pass 12dB", "100 Hz")
    C("load_device", track="MUSIC BUS", query="Compressor", roots=["audio_effects"])
    C("set_device_input", track="MUSIC BUS", device="Compressor", source="KICK", channel="Post Mixer")
    C("set_param", track="MUSIC BUS", device="Compressor", param="S/C EQ On", value=0)
    for param, disp in (("Threshold", "-28.0 dB"), ("Ratio", "2.50 : 1"),
                        ("Attack", "5.00 ms"), ("Release", "120 ms")):
        C("set_param", track="MUSIC BUS", device="Compressor", param=param, display=disp)
    _eq("MUSIC BUS", 1, "High Pass 12dB", "120 Hz")
    _eq("FX BUS", 1, "High Pass 12dB", "200 Hz")
    for colour, tracks in COLOURS.items():
        for t in tracks:
            C("set_track", track=t, color_index=colour)


# ---------------------------------------------------------------- v20 finish
# "falling into the breaks is abrupt (v19 measured -6.3 LU into break 1, -8.7 LU into
# break 2 in one bar); the hat groove a bit loud; the drums need glue; the voices sound
# like different samples (Murder's mp3 measured 4-6 dB darker above 2 kHz, 5.6 dB thinner
# at 120-250 Hz, +2.3 dB at 1-2 kHz, 2 LU quieter than City); more energy and tension in
# break 2 with repetitions, delays and reverb; polish the bass, clean every EQ".
HAT_FILTER20 = [(1, 6000), (8.9, 6000), (9, 18000), (49, 18000), (51, 5000), (56.9, 5000),
                (57, 2500), (64.5, 18000), (97, 18000), (99, 3000), (104.9, 3000),
                (105, 4000), (112.9, 4000), (113, 2500), (128.5, 18000), (185, 18000),
                (193, 4000)]
CLEAN_HP = {"CLAP": "150 Hz", "SNARE": "120 Hz", "HAT 16ths": "300 Hz",
            "HAT OFF - persona": "250 Hz", "HAT OFF - shaker shot": "300 Hz",
            "HAT OFF - imite": "300 Hz", "CRASH 909": "300 Hz", "RIDE 909": "350 Hz",
            "PERC LOOP": "200 Hz"}
BUILD2_CALLS = ([(b, 0, 4) for b in (113, 115, 117, 119)] + [(b, 0, 4) for b in (121, 122, 123, 124)]
                + [(b, o, 2) for b in (125, 126) for o in (0, 2)]
                + [(b, o, 1) for b in (127, 128) for o in (0, 1, 2, 3)
                   if beat(b) + o < beat(129) - 2])          # every 2 bars ... every beat


def _wash(meta):
    """The drop poured into the break: one bar of the riff through a 3 s reverb, its
    low-pass falling 8 kHz -> 600 Hz over the tail."""
    x, sr = sf.read(meta["Murder keys"]["path"], dtype="float32")
    seg = x[: len(x) // 2]
    rng = np.random.default_rng(20)
    n = int(3.5 * sr)
    ir = rng.standard_normal((n, 2)).astype(np.float32) * np.exp(-np.arange(n) / (.9 * sr))[:, None]
    wet = np.stack([signal.fftconvolve(seg[:, c], ir[:, c])[: len(seg) + n] for c in (0, 1)], axis=1)
    out = np.zeros_like(wet)
    hop = int(.05 * sr)
    for i in range(0, len(wet), hop):
        fc = 8000 * (600 / 8000) ** min(1, i / len(wet))
        sos = signal.butter(2, fc, "lowpass", fs=sr, output="sos")
        out[i:i + hop] = signal.sosfilt(sos, wet[i:i + hop], axis=0)
    out = _edge(out * np.linspace(1, 0, len(out))[:, None] ** 1.5, sr, .01, .2)
    out *= .45 / max(float(np.abs(out).max()), 1e-6)
    path = OUT / "Drop wash into the break.wav"
    sf.write(path, out.astype(np.float32), sr, subtype="PCM_24")
    return str(path)


def v20_finish():
    meta = json.loads((OUT / "v3.json").read_text())
    ph = json.loads((OUT / "phrases.json").read_text())
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    # 1. falling into the breaks: a soft crash and the drop's wash ringing in
    wash = _wash(meta)
    crash = kits.pattern("let_the_rhythm", 1, ["crash"])["crash"][0]
    for bar in (49, 97):
        C("create_midi_clip", track="CRASH 909", bar=bar, length=4,
          notes=[[crash[0], 0, 1, 88]], name="soft crash into the break")
        C("create_audio_clip", track=TRANS, path=wash, bar=bar, warp=False,
          name="drop wash into the break", gain_db=8)   # v20 check: -6.7 LU at +0 dB
    # 2. hats: corrected filter map (held between breakpoints), back in break 2, -2 dB
    rng = np.random.default_rng(20)
    C("delete_clips_in_range", track="HAT 16ths", start_bar=1, end_bar=END19 + 1)
    dips = [(beat(d) - 2, beat(d)) for d in DIPS19]
    notes = [n for n in _hat_notes19(1, END19, rng)
             if not any(a - 1e-3 <= n[1] < b for a, b in dips)]
    C("create_midi_clip", track="HAT 16ths", bar=1, length=(END19 - 1) * 4, notes=notes,
      name="hats (filter drawn)", envelopes=_filter_env(HAT_FILTER20, 1, END19))
    C("set_track", track="HAT 16ths", volume_db=round(faders["HAT 16ths"] - 2, 1))
    # 3. glue: the bus works a little harder, the shared room a little louder
    C("set_param", track=DRUM_BUS, device="Glue Compressor", param="Threshold", display="-22.0 dB")
    C("set_track", track=f"return:{ROOM}", volume_db=-5)
    # 4. one record: Murder matched to City
    _eq("VOX MURDER", 7, "High Shelf", "3.50 kHz", "4.5 dB")
    _eq("VOX MURDER", 4, "Bell", "200 Hz", "2.0 dB", "0.80")
    _eq("VOX MURDER", 5, "Bell", "1.40 kHz", "-1.5 dB", "1.00")
    C("set_track", track="VOX MURDER", volume_db=round(faders["VOX MURDER"] + 2, 1))
    # 5. break 2 tension: the theme repeats faster and faster into delay and plate
    for c in client.call("get_track", {"track": "VOX CITY"})["clips"]:
        if beat(113) - 1 <= c["start"] < beat(129) - 1:
            C("delete_clip", track="VOX CITY", clip={"at": c["start"]})
    call = ph["City call"]
    dur = sf.info(call["path"]).duration - .001
    total = beat(129) - 2 - beat(113)
    for bar, off, length in BUILD2_CALLS:
        at = beat(bar) + off - .25
        k = (beat(bar) + off - beat(113)) / total
        env = [{"param": "send:1", "unit": "db", "points": [[0, -24 + 18 * k], [length, -24 + 18 * k]]},
               {"param": f"send:{PLATE}", "unit": "db", "points": [[0, -18 + 10 * k], [length, -18 + 10 * k]]}]
        C("create_audio_clip", track="VOX CITY", path=call["path"], beat=at, warp=False,
          envelopes=env, name=f"theme x{int(4 / length)}")
        C("set_warp_markers", track="VOX CITY", clip={"at": at},
          markers=[[x, min(t, dur)] for x, t in call["markers"]])
        C("set_clip", track="VOX CITY", clip={"at": at}, warping=True, warp_mode="complex_pro",
          looping=False, start_marker=PREROLL - .25, end_marker=PREROLL + length)
        mine = [c for c in client.call("get_track", {"track": "VOX CITY"})["clips"]
                if abs(c["start"] - at) < .01]
        if mine and mine[0]["end"] > at + length + .25 + .02:
            C("trim_clip", track="VOX CITY", clip={"at": at}, end_beat=at + length + .25)
    # 6. bass polish and clean EQs everywhere above the low end
    C("set_param", track="BASS", device="Saturator", param="Dry/Wet", display="35 %")
    _eq("BASS", 8, "Low Pass 12dB", "3.00 kHz")
    _eq("BASS", 4, "Bell", "110 Hz", "1.5 dB", "1.20")
    for t, hz in CLEAN_HP.items():
        names = [d["name"] for d in client.call("get_track", {"track": t})["devices"]]
        if "EQ Eight" not in names:
            C("load_device", track=t, query="EQ Eight", roots=["audio_effects"])
        _eq(t, 1, "High Pass 12dB", hz)


# ---------------------------------------------------------------- v21 one pocket
# "the drums feel disconnected, the hats lost, the continuous hats too loud". Measured
# micro-timing: hat 16ths' off-16ths +15.7 ms, congas/tom/bass +10.8 ms, shaker shot
# -10.4 ms (the kit's -5.2 ms applied twice), clap/snare +5 ms. Every 16th part now
# swings the same 10.8 ms, the shaker leans the kit's 5 ms early; the two continuous hats
# come down.
def v21_pocket():
    beat_ms = 60000 / client.call("get_song")["tempo"]
    swung = SWING_S + HAT_SWING_EXTRA

    def hat_fix(t):
        k = round((t - swung) * 4)
        if k % 2 == 1 and abs(t - (k / 4 + swung)) < 1e-3:   # an off-16th at the old swing
            return round(t - HAT_SWING_EXTRA, 4)
        return t
    shaker_fix = lambda t: round(t + 5.2 / beat_ms, 4)
    for track, fix in (("HAT 16ths", hat_fix), ("HAT OFF - shaker shot", shaker_fix)):
        for c in client.call("get_track", {"track": track})["clips"]:
            ns = client.call("get_notes", {"track": track, "clip": {"at": c["start"]}})
            C("add_notes", track=track, clip={"at": c["start"]},
              notes=[[p_, fix(t), d, v] for p_, t, d, v in ns], replace=True)
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    C("set_track", track="HAT 16ths", volume_db=round(faders["HAT 16ths"] - 3, 1))
    C("set_track", track="HAT OFF - persona", volume_db=round(faders["HAT OFF - persona"] - 2, 1))

# "the looped vocal you picked is badly warped, off time, ugly". The build's repetition
# sliced the warped City call on the grid, cutting syllables in half. The chop now starts
# at the real attack of hook B's first syllable ("baby", near the downbeat of source bar
# 40), unwarped (the voice's own speed), and its attack sits on the grid; the last bar's
# beat repeats rise a semitone each.
def _onset_chops(src_bar=40):
    s = SOURCES["CITY"]
    detected = json.loads(BEATS_FILE.read_text())["CITY"]["beats"]
    return stem_remix.onset_chops(s["stem"], OUT, s["bpm"], s["downbeat"], src_bar, detected,
                                  label="Hook B chop")


def v21_build_vocal(src_bar=40):
    chops, lead = _onset_chops(src_bar)
    for c in client.call("get_track", {"track": "VOX CITY"})["clips"]:
        if beat(113) - 1 <= c["start"] < beat(129) - 1:
            C("delete_clip", track="VOX CITY", clip={"at": c["start"]})
    total = beat(129) - 2 - beat(113)
    hits = ([(b, 0, "long", 0) for b in (113, 115, 117, 119, 121, 122, 123, 124)]
            + [(b, o, "long", 0) for b in (125, 126) for o in (0, 2)]
            + [(b, o, "short", i) for i, (b, o) in enumerate((b, o) for b in (127, 128)
                                                             for o in range(4))
               if beat(b) + o < beat(129) - 2])
    for bar, off, kind, rise in hits:
        at = beat(bar) + off - .004 * 125 / 60
        k = (beat(bar) + off - beat(113)) / total
        env = [{"param": "send:1", "unit": "db", "points": [[0, -24 + 18 * k], [2, -24 + 18 * k]]},
               {"param": f"send:{PLATE}", "unit": "db", "points": [[0, -18 + 10 * k], [2, -18 + 10 * k]]}]
        C("create_audio_clip", track="VOX CITY", path=chops[kind], beat=at, warp=False,
          envelopes=env, name=f"hook B chop {kind}" + (f" +{rise}" if rise else ""))
        if rise:
            C("set_clip", track="VOX CITY", clip={"at": at}, pitch=rise)
    print("onset lead vs grid (s):", round(lead, 3))


# ear candy: a reversed 909 crash pulling into each drop's second half, and a 909 tom
# run (hi hi mid mid low low low low, 16ths, swung) in the two beats before each breath
LIVE2 = Path("/Users/lukasgalhardo/Desktop/Projects 26:27/LIVE 2 Project/Samples/Imported")
REV_CRASH_INTO = [81, 145]
TOM_RUN_AT = [(64, 0), (128, 0)]        # bar, beat


def v21_candy():
    tempo = client.call("get_song")["tempo"]
    s16 = 60 / tempo / 4
    cx, sr = sf.read(LIVE2 / "Crash 909.aif", dtype="float32")
    cx = cx if cx.ndim == 2 else np.repeat(cx[:, None], 2, axis=1)
    rev = _edge(cx[: int(1.6 * sr)][::-1].copy(), sr, .25, .005)
    rev *= .45 / max(float(np.abs(rev).max()), 1e-6)
    rpath = OUT / "909 crash reversed.wav"
    sf.write(rpath, rev, sr, subtype="PCM_24")
    L = len(rev) / sr * tempo / 60
    for bar in REV_CRASH_INTO:
        C("create_audio_clip", track=TRANS, path=str(rpath), beat=beat(bar) - L, warp=False,
          name="reversed crash")
    toms = {k: sf.read(LIVE2 / f, dtype="float32")[0] for k, f in
            (("hi", "Tom 909 Hi.aif"), ("mid", "Tom 909 Mid 2.wav"), ("low", "Tom 909 Low.aif"))}
    toms = {k: (v if v.ndim == 2 else np.repeat(v[:, None], 2, axis=1)) for k, v in toms.items()}
    run = np.zeros((int(8 * s16 * sr) + int(.4 * sr), 2), np.float32)
    for i, (k, g) in enumerate(zip(["hi", "hi", "mid", "mid", "low", "low", "low", "low"],
                                   [.55, .6, .65, .7, .75, .8, .9, 1.0])):
        a = int((i * s16 + (SWING_S * 60 / tempo if i % 2 else 0)) * sr)
        hit = toms[k][: int(.35 * sr)] * g
        run[a: a + len(hit)] += hit[: len(run) - a]
    run = _edge(run, sr, .001, .05)
    run *= .5 / max(float(np.abs(run).max()), 1e-6)
    tpath = OUT / "909 tom run.wav"
    sf.write(tpath, run[: int(8 * s16 * sr)], sr, subtype="PCM_24")
    for bar, b in TOM_RUN_AT:
        C("create_audio_clip", track=TRANS, path=str(tpath), beat=beat(bar) + b, warp=False,
          name="909 tom run")


# "use fills too, they matter": phrase-end fills in rotation, never on top of a turn that
# already has a transition (stutter, scratch, tape stop, rewind): a 909 tom run on beats
# 3-4 at the bigger turns inside drops, a two-clap pickup (3.5, 3.75) at the smaller ones;
# the conga fills already close every 8-bar phrase where congas play.
TOM_FILLS = [88, 136, 160]
CLAP_PICKUPS = [40, 56, 80, 120, 144, 168, 184]


def v21_fills():
    tpath = str(OUT / "909 tom run.wav")
    for bar in TOM_FILLS:
        C("create_audio_clip", track=TRANS, path=tpath, beat=beat(bar) + 2, warp=False,
          name="909 tom run (fill)")
    for c in client.call("get_track", {"track": "CLAP"})["clips"]:
        ns = client.call("get_notes", {"track": "CLAP", "clip": {"at": c["start"]}})
        add = []
        for bar in CLAP_PICKUPS:
            t0 = beat(bar) - c["start"]
            if 0 <= t0 < c["length"]:
                add += [[60, round(t0 + 2.5 + CLAP_LATE_V10, 4), .2, 70],
                        [60, round(t0 + 2.75 + CLAP_LATE_V10, 4), .2, 86]]
        if add:
            C("add_notes", track="CLAP", clip={"at": c["start"]},
              notes=sorted(ns + add, key=lambda n: n[1]), replace=True)


# the solo spectra of drop 2 (limiter off) against the kick: riff -22.4 and City -23.3 LU
# (the kick-keyed MUSIC BUS compressor at -28 dB took ~12 dB), the hats as loud as the clap
# (-12.5 / -12.1 / -12.1), the kick the loudest element at 250-630 Hz (its box masking bass
# and voice), the congas on top at 315 Hz; ride and tom silent since v1 (forced to pitch
# 60, an empty pad of the 909 rack).
def v21_mix():
    for t, pitch in (("RIDE 909", 51), ("TOM 909", 44)):
        for c in client.call("get_track", {"track": t})["clips"]:
            ns = client.call("get_notes", {"track": t, "clip": {"at": c["start"]}})
            C("add_notes", track=t, clip={"at": c["start"]},
              notes=[[pitch] + n[1:] for n in ns], replace=True)
    C("set_param", track="MUSIC BUS", device="Compressor", param="Threshold", display="-16.0 dB")
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    for t, d in (("HAT 16ths", -3.5), ("HAT OFF - persona", -3.0), ("CLAP", 3.0),
                 ("CONGAS", -2.0), ("VOX BUS", -2.0)):
        C("set_track", track=t, volume_db=round(faders[t] + d, 1))
    names = [d["name"] for d in client.call("get_track", {"track": "KICK"})["devices"]]
    if "EQ Eight" not in names:
        C("load_device", track="KICK", query="EQ Eight", roots=["audio_effects"])
    _eq("KICK", 3, "Bell", "400 Hz", "-3.0 dB", "1.20")
    _eq("CONGAS", 2, "Bell", "315 Hz", "-2.0 dB", "1.20")
    # re-measured soloed after the bus fix (riff -17.1, City -18.4, atmos -22.2, ride -23.8,
    # tom -16.3 LU vs the kick) and set to riff -12, City -16, atmos -20, ride -20, tom -18
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    for t, d in (("LOOP MURDER - guitar riff", 5.1), ("LOOP CITY - orig synth", 2.4),
                 ("ATMOS - riff wash", 2.2), ("RIDE 909", 3.8), ("TOM 909", -1.7)):
        C("set_track", track=t, volume_db=round(faders[t] + d, 1))
    C("re_enable_automation")     # a fader move overrides the clips' volume ramps


# ---------------------------------------------------------------- v22 mix + master
# "quick mix and master to test in the car; an FX in break 2 after the vocal starts sounds
# strange; a summer beach-club track, bounce, presence; the voices analysed together, not
# competing in level or weight, in the same atmosphere". The wash at 97 sat under Murder's
# first words: gone. Murder no longer feeds the long atmosphere (City never did): both
# voices live in the plate only. Soloed, they were level within 0.5 LU but Murder kept
# +3.8 dB at 250-600 Hz and -2.8 / -3.5 dB at 1.5-4 / 4-10 kHz: EQ'd to City. Master:
# EQ (sub clean under 28 Hz, presence and air +1 dB), Glue 2:1 slow, then the True Peak
# limiter at -1 dBTP, driven to ~-9 LUFS.
def v22_voices():
    for c in client.call("get_track", {"track": TRANS})["clips"]:
        if c["name"] == "drop wash into the break" and abs(c["start"] - beat(97)) < .01:
            C("delete_clip", track=TRANS, clip={"at": c["start"]})
    C("set_send", track="VOX MURDER", send=2, db=-70)
    _eq("VOX MURDER", 2, "Bell", "400 Hz", "-5.0 dB", "0.90")
    _eq("VOX MURDER", 4, "Bell", "160 Hz", "3.0 dB", "0.80")
    _eq("VOX MURDER", 5, "Bell", "1.00 kHz", "-2.0 dB", "1.00")
    _eq("VOX MURDER", 7, "High Shelf", "3.00 kHz", "6.0 dB")
    _eq("VOX CITY", 7, "High Shelf", "6.00 kHz", "0.0 dB")


def v22_master(limiter_gain_db=12.0):   # calibrated: drop 2 -8.7 LUFS, crest 8.3 dB
    names = client.call("get_song")["master"]["devices"]     # get_track refuses the master
    if "EQ Eight" not in names:
        C("load_device", track="master", query="EQ Eight", roots=["audio_effects"])
        C("move_device", track="master", device="EQ Eight", position=0)
    if "Glue Compressor" not in names:
        C("load_device", track="master", query="Glue Compressor", roots=["audio_effects"])
        C("move_device", track="master", device="Glue Compressor", position=1)
    _eq("master", 1, "High Pass 48dB", "28.0 Hz")
    _eq("master", 4, "Bell", "3.50 kHz", "1.0 dB", "0.70")
    _eq("master", 7, "High Shelf", "12.0 kHz", "1.0 dB")
    for param, disp in (("Attack", "30"), ("Ratio", "2"), ("Threshold", "-14.0 dB"),
                        ("Range", "3.00 dB")):
        C("set_param", track="master", device="Glue Compressor", param=param, display=disp)
    C("set_param", track="master", device="Limiter", param="Input Gain",
      display=f"{limiter_gain_db:.1f} dB")


# ---------------------------------------------------------------- v23 breakbeat
# "I wanted a breaking-beat drum in break 2, it's really calling for it". Sample Magic's
# reworked "smash" break (120 BPM, 2 bars, 10 hits a bar, swung ~+25 ms) warped onto the
# track's pocket the way the vocals are (a marker on every hit, moved 70 % onto its 16th +
# the kit's 10.8 ms swing), high-passed at 120 Hz so the low end stays the drop's release;
# it enters filtered with Murder's opening voice, runs whole under hook A, and rises
# through build 2 into the breath. On the DRUMS bus and the kit's room.
BREAK_LOOP = Path("/Users/lukasgalhardo/Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs/"
                  "Sample Magic Acoustic Drum Tools/reworked_breaks_&_beats/adt_120_drum_break_smash.wav")
BREAKBEAT = "BREAKBEAT"
BREAKBEAT_PLAN = [  # (a, b, Hz from, Hz to, volume ramp)
    (97, 105, 2000, 18000, False), (105, 113, 18000, 18000, False),
    (113, 121, 18000, 18000, True), (121, 129, 18000, 18000, True)]


def _break_markers(x, sr, bpm=120.0, q=.7):
    return stem_remix.break_loop(x, sr, bpm, SWING_S, q)[0]


def v23_breakbeat():
    x, sr = sf.read(BREAK_LOOP, dtype="float32")
    x = x if x.ndim == 2 else np.repeat(x[:, None], 2, axis=1)
    src = OUT / "Breakbeat smash (2 bars).wav"
    sf.write(src, x, sr, subtype="PCM_24")
    m = {"path": str(src), "markers": _break_markers(x, sr)}
    if not any(t["name"] == BREAKBEAT for t in client.call("get_song")["tracks"]):
        idx = [t["i"] for t in client.call("get_song")["tracks"] if t["name"] == "PERC LOOP"][0] + 1
        C("create_track", kind="audio", name=BREAKBEAT, index=idx)
        C("load_device", track=BREAKBEAT, query="Auto Filter", roots=["audio_effects"])
        C("set_track_output", track=BREAKBEAT, dest=DRUM_BUS)
        C("set_track", track=BREAKBEAT, color_index=16, volume_db=-14.8)   # soloed: -10 LU vs kick
        C("set_send", track=BREAKBEAT, send=ROOM, db=-18)
        _eq(BREAKBEAT, 1, "High Pass 48dB", "120 Hz")
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    C("delete_clips_in_range", track=BREAKBEAT, start_bar=1, end_bar=END19 + 1)
    for a, b, f0, f1, ramp in BREAKBEAT_PLAN:
        path, mk = _section_file(f"Breakbeat {a}-{b - 1}", m, b - a)
        beats = (b - a) * 4 - (2 if b in DIPS19 else 0)
        envs = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                 "points": [[0, _raw_hz(f0)], [min(8.5, beats), _raw_hz(f1)], [beats, _raw_hz(f1)]]}]
        if ramp:
            envs.append({"param": "volume", "unit": "db",
                         "points": [[0, faders[BREAKBEAT] - 5], [beats, faders[BREAKBEAT] + 1]]})
        _place_section19(BREAKBEAT, path, mk, a, beats, envs)


# ---------------------------------------------------------------- v24 the break pulls
# "more movement, more variations; make it pull the break into a strong build-up; and the
# drop lands weak". Break 2 changes every 2 bars (whole, a 2-beat hole, the last beat
# reversed, a snare stutter, another break - "tight" - for contrast); build 2 chops it
# faster and faster (the loop's 1st beat on every beat, its snare beat in 8ths, then 16ths)
# under the opening filter; drop 2 keeps the break under the kick (high-passed 300 Hz)
# for 16 bars, its boom and crash 3 dB up, riff and City +1.5 dB.
ALT_BREAK = BREAK_LOOP.with_name("adt_120_drum_break_tight.wav")
BREAK2_CYCLE = ["full", "full", "hole", "rev", "full", "alt", "full", "stut"]   # 97-112
BUILD2_CYCLE = ["full", "alt", "full", "stut"]                                # 113-120


def _break_variants():
    x, sr = sf.read(BREAK_LOOP, dtype="float32")
    x = x if x.ndim == 2 else np.repeat(x[:, None], 2, axis=1)
    b = int(.5 * sr)                                   # one beat at the loop's 120 BPM
    s16 = b // 4
    v = {"full": x.copy()}
    h = x.copy()
    h[6 * b: 8 * b] *= 0                               # bar 2 beats 3-4 out
    h[6 * b - 64: 6 * b] *= np.linspace(1, 0, 64)[:, None]
    v["hole"] = h
    r = x.copy()
    r[7 * b: 8 * b] = x[7 * b: 8 * b][::-1]
    v["rev"] = r
    st = x.copy()
    snare = x[b: b + s16].copy()
    for i in range(4):
        st[7 * b + i * s16: 7 * b + (i + 1) * s16] = snare * (.6 + .13 * i)
    v["stut"] = st
    y, sr2 = sf.read(ALT_BREAK, dtype="float32")
    y = y if y.ndim == 2 else np.repeat(y[:, None], 2, axis=1)
    v["alt"] = y[: len(x)] if len(y) >= len(x) else np.pad(y, ((0, len(x) - len(y)), (0, 0)))
    return v, sr, b


def _chop_build(sr, b, tempo):
    """Bars 121-128 at the track's tempo: the 1st beat on every beat (121-124), the snare
    beat in 8ths (125-126), in 16ths (127-128), rising; out 2 beats before the drop."""
    x, _ = sf.read(BREAK_LOOP, dtype="float32")
    x = x if x.ndim == 2 else np.repeat(x[:, None], 2, axis=1)
    beat_s = 60 / tempo
    first, snare = x[:b], x[b: 2 * b]
    out = np.zeros((int(8 * 4 * beat_s * sr), 2), np.float32)
    def put(seg, t, g):
        i = int(t * sr)
        seg = _edge(seg[: len(out) - i].copy(), sr, .001, .008) * g
        out[i: i + len(seg)] += seg
    for k in range(16):                                  # 121-124: beat pulse
        put(first[: int(beat_s * sr)], k * beat_s, .7 + .1 * k / 16)
    for k in range(16):                                  # 125-126: snare 8ths
        put(snare[: int(beat_s / 2 * sr)], 16 * beat_s + k * beat_s / 2, .75 + .1 * k / 16)
    for k in range(32 - 8):                              # 127-128: 16ths, 2 beats short
        put(snare[: int(beat_s / 4 * sr)], 24 * beat_s + k * beat_s / 4, .8 + .2 * k / 24)
    out *= .5 / max(float(np.abs(out).max()), 1e-6)
    path = OUT / "Breakbeat build chops 121-128.wav"
    sf.write(path, out, sr, subtype="PCM_24")
    return str(path)


def v24_break():
    v, sr, b = _break_variants()
    mk = {}
    for k, x in v.items():
        path = OUT / f"Breakbeat smash - {k}.wav"
        sf.write(path, x, sr, subtype="PCM_24")
        mk[k] = {"path": str(path), "markers": _break_markers(x, sr)}
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    C("delete_clips_in_range", track=BREAKBEAT, start_bar=97, end_bar=END19 + 1)
    plan = [(97 + 2 * i, kind) for i, kind in enumerate(BREAK2_CYCLE)] + \
           [(113 + 2 * i, kind) for i, kind in enumerate(BUILD2_CYCLE)]
    for bar, kind in plan:
        k = (bar - 97) / 24
        envs = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                 "points": [[0, _raw_hz(2000 if bar == 97 else 6000 + 12000 * min(1, k * 1.5))],
                            [8, _raw_hz(18000 if bar > 97 else 9000)]]}]
        if bar >= 113:
            envs.append({"param": "volume", "unit": "db", "points":
                         [[0, faders[BREAKBEAT] - 3 + 2 * (bar - 113) / 8],
                          [8, faders[BREAKBEAT] - 1 + 2 * (bar - 113) / 8]]})
        _place_section19(BREAKBEAT, mk[kind]["path"], mk[kind]["markers"], bar, 8, envs)
    tempo = client.call("get_song")["tempo"]
    chops = _chop_build(sr, b, tempo)
    C("create_audio_clip", track=BREAKBEAT, path=chops, bar=121, warp=False,
      name="break chops accelerating", envelopes=[{"param": "volume", "unit": "db", "points":
          [[0, faders[BREAKBEAT] - 1], [30, faders[BREAKBEAT] + 3]]}])
    # drop 2: the break under the kick, high-passed, for 16 bars
    if "Auto Filter" in [d["name"] for d in client.call("get_track", {"track": BREAKBEAT})["devices"]]:
        pass
    for i, bar in enumerate(range(129, 145, 2)):
        kind = "full" if i % 4 != 3 else "stut"
        envs = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                 "points": [[0, _raw_hz(18000)], [8, _raw_hz(18000)]]},
                {"param": "volume", "unit": "db", "points": [[0, faders[BREAKBEAT] - 5], [8, faders[BREAKBEAT] - 5]]}]
        _place_section19(BREAKBEAT, mk[kind]["path"], mk[kind]["markers"], bar, 8, envs)
    # the release: boom and crash up 3 dB at 129, the drop's loops +1.5 dB
    for c in client.call("get_track", {"track": "FX - sub boom"})["clips"]:
        if abs(c["start"] - beat(129)) < .01:
            C("set_clip", track="FX - sub boom", clip={"at": c["start"]}, gain_db=3)
    crash = kits.pattern("let_the_rhythm", 1, ["crash"])["crash"][0]
    C("delete_clips_in_range", track="CRASH 909", start_bar=129, end_bar=130)
    C("create_midi_clip", track="CRASH 909", bar=129, length=4,
      notes=[[crash[0], 0, 1, 127], [crash[0], 0, 1, 127]], name="drop 2 crash (doubled)")
    for t in ("LOOP MURDER - guitar riff", CITY):
        for c in client.call("get_track", {"track": t})["clips"]:
            if beat(129) - .01 <= c["start"] < beat(161):
                C("set_clip", track=t, clip={"at": c["start"]}, gain_db=1.5)
    C("re_enable_automation")


# ---------------------------------------------------------------- v25 later voices, glue
# "in the break and the vocal loops use a part further on in the vocal; adjust these FX;
# glue the drums and the timbres even more". Break 2 now carries Murder's later lines
# (source bars 25-32), the build's loop a syllable two bars later in hook B (bar 42); the
# transition FX sit 2 dB back; one tape-like saturation colours the DRUMS and MUSIC buses,
# and the acoustic break is EQ'd towards the electronic kit (box and fizz down).
def v25_glue():
    ph = json.loads((OUT / "phrases.json").read_text())
    m = ph["Murder verse 4"]
    for c in client.call("get_track", {"track": "VOX MURDER"})["clips"]:
        if abs(c["start"] - (beat(97) - PREROLL)) < .01:
            C("delete_clip", track="VOX MURDER", clip={"at": c["start"]})
    beats = m["beats"] + PREROLL
    env = [{"param": "Frequency", "device": "Auto Filter", "unit": "raw",
            "points": [[0, _raw_hz(1200)], [8.5, _raw_hz(18000)], [beats, _raw_hz(18000)]]}]
    _place_section19("VOX MURDER", m["path"], m["markers"], 97 - PREROLL / 4, beats, env)
    v21_build_vocal(42)
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    C("set_track", track=TRANS, volume_db=round(faders[TRANS] - 2, 1))
    for bus, drive, wet in ((DRUM_BUS, "2.0 dB", "35 %"), ("MUSIC BUS", "1.5 dB", "25 %")):
        if "Saturator" not in [d["name"] for d in client.call("get_track", {"track": bus})["devices"]]:
            C("load_device", track=bus, query="Saturator", roots=["audio_effects"])
        C("set_param", track=bus, device="Saturator", param="Type", item="Soft Sine")
        C("set_param", track=bus, device="Saturator", param="Drive", display=drive)
        C("set_param", track=bus, device="Saturator", param="Dry/Wet", display=wet)
    _eq(BREAKBEAT, 3, "Bell", "400 Hz", "-2.0 dB", "1.00")
    _eq(BREAKBEAT, 7, "High Shelf", "8.00 kHz", "-2.0 dB")
    C("re_enable_automation")


# ---------------------------------------------------------------- v26 pre-drops
# "the break into the drop still isn't as impactful as I'd like; it could have a nice
# pre-drop, something characteristic of the track". The track's signature moment: the
# whole track stops and the title line stands alone, a cappella, dry and close; its last
# word throws into the delay, a reversed crash swells, and the drop lands. Drop 2: bar
# 127 = "baby I'm in your city" (hook B's 1st bar), 128 = its echo, 128.5 the DJ rewind.
# Drop 1: bar 64 = the City call (the theme), a reversed crash into 65.
PREDROPS = [  # (stop bar, drop bar, phrase, keep these FX)
    (64, 65, "City call", ()),
    (127, 129, "City trade 1", ("DJ rewind",)),
]
KEEP_THROUGH = {"ATMOS - riff wash", "LOW END", DRUM_BUS, "VOX BUS", "MUSIC BUS", "FX BUS"}


def _clear(stop, drop, keep_fx):
    a, b = beat(stop), beat(drop)
    for t in client.call("get_song")["tracks"]:
        n = t["name"]
        if n in KEEP_THROUGH or n.startswith("REF") or n == "FX - sub boom":
            continue
        info = client.call("get_track", {"track": t["i"]})
        if info["kind"] == "midi":
            _filter_notes(n, lambda x: a - 1e-3 <= x < b)
            continue
        for c in info["clips"]:
            if c["start"] < a < c["end"] - 1e-3:
                C("trim_clip", track=n, clip={"at": c["start"]}, end_beat=a)
            elif (a - 1e-3 <= c["start"] < b - PREROLL - 1e-3    # a clip starting in the
                  and not any(k in c["name"] for k in keep_fx)):  # drop's pre-roll stays
                C("delete_clip", track=n, clip={"at": c["start"]})


def v26_predrops():
    ph = json.loads((OUT / "phrases.json").read_text())
    tempo = client.call("get_song")["tempo"]
    rev = str(OUT / "909 crash reversed.wav")
    L = sf.info(rev).duration * tempo / 60
    for stop, drop, phrase, keep in PREDROPS:
        _clear(stop, drop, keep)
        m = ph[phrase]
        at, beats = beat(stop) - PREROLL, 4 + PREROLL               # one bar of it
        env = [{"param": "send:1", "unit": "db",
                "points": [[0, -70], [beats - 1.05, -70], [beats - 1, -2], [beats + 4, -2]]},
               {"param": f"send:{PLATE}", "unit": "db", "points": [[0, -16], [beats, -12]]}]
        C("create_audio_clip", track="VOX CITY", path=m["path"], beat=at, warp=False,
          envelopes=env, name=f"PRE-DROP a cappella: {phrase}")
        dur = sf.info(m["path"]).duration - .001
        C("set_warp_markers", track="VOX CITY", clip={"at": at},
          markers=[[x, min(t, dur)] for x, t in m["markers"]])
        C("set_clip", track="VOX CITY", clip={"at": at}, warping=True, warp_mode="complex_pro",
          looping=False, start_marker=0, end_marker=beats, gain_db=2)
        C("trim_clip", track="VOX CITY", clip={"at": at}, end_beat=at + beats)
        end = beat(drop) - (2 if drop == 129 else 0)                 # the rewind owns 128.5
        C("create_audio_clip", track=TRANS, path=rev, beat=end - L, warp=False,
          name="reversed crash (pre-drop)")
    C("re_enable_automation")


# ---------------------------------------------------------------- v27 gain staging
# "this bass is sending a clipped signal? it's saturating on top of what is clipped; these
# mistakes can't happen". Mine: v1 set the bass Simplers to 0 dB on a normalised sample,
# so with velocity 118 and the Saturator's +5 dB drive the chain ran over 0 dBFS before a
# -19 dB fader. Every source now peaks ~-6 dBFS into its effects: the three bass Simplers
# back to -12 dB (faders up to compensate), the Saturator driven 9 dB into a signal that
# arrives 12 dB lower, the break wash +4 dB not +8, Murder's EQ output -4 dB before its
# compressor (its shelf adds 6 dB).
def v27_gain():
    faders = {t["name"]: t["vol_db"] for t in client.call("get_song")["tracks"]}
    for t in ("BASS", "BASS - break", TEASER):
        C("set_param", track=t, device=0, param="Volume", value=-12)
        C("set_track", track=t, volume_db=round(min(6.0, faders[t] + 12), 1))
    C("set_param", track="BASS", device="Saturator", param="Drive", display="9.0 dB")
    for c in client.call("get_track", {"track": TRANS})["clips"]:
        if c["name"] == "drop wash into the break":
            C("set_clip", track=TRANS, clip={"at": c["start"]}, gain_db=4)
    C("set_param", track="VOX MURDER", device="EQ Eight", param="Output", display="-4.00 dB")
    C("set_track", track="VOX MURDER", volume_db=round(faders["VOX MURDER"] + 2, 1))
    C("re_enable_automation")


def mix():
    """Kick sidechain on bass and sub (S/C EQ off: its 80 Hz high-pass hid the kick's
    body), the pool groove neutralised (swing is in the notes), a safety limiter."""
    for t, release in (("BASS", "70.0 ms"), ("SUB", "90.0 ms")):
        C("load_device", track=t, query="Compressor", roots=["audio_effects"])
        C("set_device_input", track=t, device="Compressor", source="KICK", channel="Post Mixer")
        C("set_param", track=t, device="Compressor", param="S/C EQ On", value=0)
        C("set_param", track=t, device="Compressor", param="Threshold", display="-24")
        C("set_param", track=t, device="Compressor", param="Attack", display="0.50 ms")
        C("set_param", track=t, device="Compressor", param="Release", display=release)
    for g in client.call("grooves")["grooves"]:
        C("set_groove", name=g["name"], timing=0, random=0, velocity=0)
    C("load_device", track="master", query="Limiter", roots=["audio_effects"])
    C("set_param", track="master", device="Limiter", param="Mode", value=2)
    C("set_param", track="master", device="Limiter", param="Ceiling", display="-1.0 dB")
    C("set_param", track="master", device="Limiter", param="Input Gain", display="6.0 dB")


def cues():
    for bar, name in CUES:
        C("set_cue", bar=bar, name=name)


if __name__ == "__main__":
    stage = sys.argv[1]
    if stage == "v8_levels":
        v8_levels(sys.argv[2])
        sys.exit()
    if stage == "v8_reverbs":
        v8_reverbs()
        sys.exit()
    {"phrases": phrases, "tracks": tracks, "cues": cues, "mix": mix, "v3_prepare": v3_prepare,
     "v3_live": v3_live, "v3_low_end": v3_low_end, "mix_v4": mix_v4, "v5_energy": v5_energy, "v6_roles": v6_roles, "v7_holes": v7_holes, "v8_murder": v8_murder, "v8_sub": v8_sub, "v9_tension": v9_tension, "v9_builds": v9_builds, "v10_clap": v10_clap, "v11_character": v11_character, "v11_split": v11_split, "v12_dj": v12_dj, "v13_organize": v13_organize, "v14_polish": v14_polish, "v15_story": v15_story, "v16_theme": v16_theme,
     "v16_movement": v16_movement, "v17_drums": v17_drums, "v18_mix": v18_mix, "arrange_v19": arrange_v19, "organise_v19": organise_v19, "v20_finish": v20_finish, "v21_pocket": v21_pocket, "v21_build_vocal": v21_build_vocal, "v21_candy": v21_candy, "v21_fills": v21_fills, "v21_mix": v21_mix, "v22_voices": v22_voices, "v22_master": v22_master, "v23_breakbeat": v23_breakbeat, "v24_break": v24_break, "v25_glue": v25_glue, "v26_predrops": v26_predrops, "v27_gain": v27_gain,
     "clips": lambda: (drum_clips(), harmonic_clips(), vocal_clips())}[stage]()
    (OUT / f"live-changes-{stage}.json").write_text(json.dumps(LOG, indent=1, default=str))
