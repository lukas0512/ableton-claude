"""Murder: EP track 2, a 123 BPM dark house remix of UGK "Murder" (86.0 BPM, E minor,
A440), the sister of From The Streets: same family (stems from the record, the vocal
rules, club form) but its own groove: heavier, darker, straighter.

Material (offline analysis 2026-10-21, source bars from the first downbeat 0.8976 s):
- theme: the "Murder... Murder..." chant, src 3.5-8 (the intro)
- Pimp C verse src 7-40 (slow), Bun B verse src 45-80 (fast flow), "murder case" src 61.5
- bass riff (1 bar): E (1.5 beats) G (1.5) A|D (.5) D# (.5, leading tone back to E)
- 'other': low guitar riff B-D-A-A# (the bass a 5th up), src 9-25 alone; high keys
  melody (2 bars, D5 G#4 E4 .. C5 G4 | .. C5 C#5) with it at src 4-8, 26-29, 40-49

Stages: `python build_murder.py sketch` (two 8-bar groove sketches for the producer).
"""
import sys
from pathlib import Path

import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))
from ableton_claude import client, server  # noqa: E402

BPM = 123.0
ROOT = Path("/Users/lukasgalhardo/Desktop/TRACKS 2027/Murder")
KIT = "user_library/Samples/Claude/Murder Kit/"
LOOPS = ROOT / "loops"
LOG = []


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args))
    return r


def beat(bar):
    return (bar - 1) * 4.0


def swing(notes, pct):
    """Off-beat 16ths late by (pct - 50) % of an 8th."""
    late = (pct - 50) / 100 * 0.5
    return [[p, round(t + (late if round(t * 4) % 2 else 0), 4), d, v] for p, t, d, v in notes]


def steps(pattern, bars, pitch=60, dur=.2, vel=None, late=0.0):
    """pattern: {bar_in_cycle: [16th steps]} or a list for every bar; vel(step) -> velocity."""
    out = []
    for b in range(bars):
        st = pattern[b % len(pattern)] if isinstance(pattern, dict) else pattern
        for s in st:
            out.append([pitch, b * 4 + s / 4 + late, dur, vel(s) if vel else 100])
    return out


# ---------------------------------------------------------------- sketch
DRUMS = {  # track: (sample, fader dB, pan)
    "KICK": ("DGH_KICK_025.wav", -4, 0),
    "CLAP": ("MD2_CLAP_6.wav", -9, 0),
    "SNARE": ("DGH_SNARE_013.wav", -12, 0),
    "HAT": ("DCW_Closed_Hat_04.wav", -16, .1),
    "OPEN HAT": ("DSB_HH_COOL.wav", -18, -.15),
    "RIM": ("DGH_PERCUSSION_006.wav", -15, .3),
    "CONGA": ("NSL_BongoCongas_26.wav", -14, -.3),
}
E1, G1, A1, D1, DS1 = 28, 31, 33, 26, 27
A_BAR, B_BAR, BARS = 1, 11, 8


def hat_vel(s):
    return 100 if s % 4 == 2 else (66 if s % 2 else 48)


def sketch_a():
    """Hypnotic: 4x4, clap 2+4, 16th hats accented on the off-beat, rim syncopation,
    bass rolling in 16ths between the kicks on Murder's riff, 52 % swing."""
    sw = 52
    parts = {
        "KICK": steps([0, 4, 8, 12], BARS, dur=.25, vel=lambda s: 118),
        "CLAP": steps([4, 12], BARS, late=.016, vel=lambda s: 104),
        "HAT": steps(list(range(16)), BARS, dur=.1, vel=hat_vel),
        "RIM": steps({0: [3, 10], 1: [7, 11, 14]}, BARS, dur=.1, vel=lambda s: 88),
        "OPEN HAT": [n for n in steps([2, 6, 10, 14], BARS, dur=.3, vel=lambda s: 90)
                     if n[1] >= 16],                       # the second half lifts
    }
    bass = []
    for b in range(BARS):
        for s in range(16):
            if s % 4 == 0:
                continue                                   # the kick owns the beat
            p = E1 if s < 6 else G1 if s < 12 else (A1 if b % 2 == 0 else D1) if s < 14 else DS1
            bass.append([p, b * 4 + s / 4, .2, 112 if s % 4 == 2 else 92])
    parts["BASS A - rolling"] = bass
    return {k: swing(v, sw) for k, v in parts.items()}


def sketch_b():
    """Murder bounce: snare on 2, clap on 4, off-beat hats, 3-3-2 congas, the bass on
    the record's own riff rhythm, 55 % swing."""
    sw = 55
    parts = {
        "KICK": steps([0, 4, 8, 12], BARS, dur=.25, vel=lambda s: 118),
        "SNARE": steps([4], BARS, late=.012, vel=lambda s: 100),
        "CLAP": steps([12], BARS, late=.016, vel=lambda s: 108),
        "HAT": steps([2, 6, 10, 13, 14], BARS, dur=.1,
                     vel=lambda s: 100 if s % 4 == 2 else 58),
        "CONGA": steps({0: [0, 3, 6, 10, 13], 1: [0, 3, 6, 9, 11, 14]}, BARS, dur=.15,
                       vel=lambda s: 96 if s in (0, 6, 10) else 74),
        "RIM": steps({0: [], 1: [], 2: [], 3: [15]}, BARS, dur=.1, vel=lambda s: 84),
    }
    bass = []
    for b in range(BARS):
        turn = A1 if b % 2 == 0 else D1
        for p, t, d, v in ((E1, .5, .45, 112), (E1, 1.25, .2, 96), (G1, 1.5, .7, 108),
                           (G1, 2.5, .2, 94), (turn, 3.0, .45, 104), (DS1, 3.5, .45, 100)):
            bass.append([p, b * 4 + t, d, v])
    parts["BASS B - riff"] = bass
    return {k: swing(v, sw) for k, v in parts.items()}


def _place_loop(track, path, markers, beats, bar, copies):
    for k in range(copies):
        at = beat(bar) + k * beats
        C("create_audio_clip", track=track, path=str(path), beat=at, warp=False,
          name=Path(path).stem)
        dur = sf.info(str(path)).duration - .001
        C("set_warp_markers", track=track, clip={"at": at},
          markers=[[b, min(t, dur)] for b, t in markers])
        r = C("set_clip", track=track, clip={"at": at}, warping=True, warp_mode="complex_pro",
              looping=False, start_marker=0, end_marker=beats)
        if r.get("length", beats) > beats + .02:
            C("trim_clip", track=track, clip={"at": at}, end_beat=at + beats)


def sketch():
    song = client.call("get_song")
    built = any(t["name"] == "KICK" for t in song["tracks"])
    empty = [t["name"] for t in song["tracks"] if t["name"][:2] in ("1-", "2-", "3-", "4-")
             and not t.get("clips") and not t.get("devices")]
    C("set_tempo", bpm=BPM)
    if not built:
        _tracks()

    for bar, parts, label in ((A_BAR, sketch_a(), "SKETCH A - hipnotico, rolling 16ths, 52 %"),
                              (B_BAR, sketch_b(), "SKETCH B - Murder bounce, riff, 55 %")):
        for track, notes in parts.items():
            C("create_midi_clip", track=track, bar=bar, length=BARS * 4, notes=notes,
              name=label.split(" -")[0])
        C("set_cue", name=label, bar=bar)
    meta = __import__("json").loads((LOOPS / "stem-remix.json").read_text())
    loop = meta["Murder other"]
    for bar in (A_BAR, B_BAR):
        _place_loop("LOOP - Murder guitar riff", loop["path"], loop["markers"], loop["beats"],
                    bar, BARS // 2)
    for name in empty:                                     # the blank set's empty tracks
        C("delete_track", track=name)                      # (Live keeps at least one)
    C("set_cue", name="end of sketches", bar=B_BAR + BARS + 1)
    print("sketch done")


def _tracks():
    for name, (wav, fader, pan) in DRUMS.items():
        C("create_track", kind="midi", name=name)
        C("load_device", track=name, path=KIT + wav)
        C("set_device_prop", track=name, device=0, prop="playback_mode", value=1)
        C("set_track", track=name, volume_db=fader, pan=pan)
    for name, preset, fader in (("BASS A - rolling", "sounds/Bass/Muted Dark Bass.adv", -10),
                                ("BASS B - riff", "sounds/Bass/Basic FM House Bass.adg", -10)):
        C("create_track", kind="midi", name=name)
        C("load_device", track=name, path=preset)
        C("load_device", track=name, query="Compressor", roots=["audio_effects"])
        C("set_device_input", track=name, device="Compressor", source="KICK",
          channel="Post Mixer")
        C("set_param", track=name, device="Compressor", param="Threshold", db=-22)
        C("set_param", track=name, device="Compressor", param="Ratio", display=4)
        C("set_track", track=name, volume_db=fader)
    C("create_track", kind="audio", name="LOOP - Murder guitar riff")
    C("set_track", track="LOOP - Murder guitar riff", volume_db=-8, pan=-.1)


if __name__ == "__main__":
    {"sketch": sketch}[sys.argv[1]]()
