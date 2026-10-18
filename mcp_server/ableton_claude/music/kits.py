"""Drum kits learned from finished tracks: each part's exact loop (velocities and
micro-timing kept), its step pattern, sample, chain, level, sends and where it plays.

Kits live as JSON in ableton_claude/kits/. Notes are [pitch, start_beat, duration_beats,
velocity], relative to the part's loop of `loop_beats`.
"""
import json
import os

KITS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "kits")


def names():
    if not os.path.isdir(KITS_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(KITS_DIR) if f.endswith(".json"))


def load(name):
    key = name.strip().lower().replace(" ", "_").replace("-", "_")
    path = os.path.join(KITS_DIR, key + ".json")
    if not os.path.isfile(path):
        raise ValueError("no kit %r; kits: %s" % (name, names()))
    with open(path) as fh:
        return json.load(fh)


def tile(notes, loop_beats, bars, pitch=None):
    """Repeat a part's loop over `bars` 4/4 bars, cutting what overhangs.
    pitch remaps every note (a Simpler plays at 60, a Drum Rack pad at its own note)."""
    total = bars * 4.0
    out = []
    if not notes or not loop_beats:
        return out
    k = 0
    while k * loop_beats < total - 1e-9:
        for p, s, d, v in notes:
            t = s + k * loop_beats
            if t < total - 1e-9:
                out.append([pitch if pitch is not None else p, round(t, 4),
                            round(min(d, total - t), 4), v])
        k += 1
    return sorted(out, key=lambda n: (n[1], n[0]))


def summary(kit):
    """The kit without its note lists: roles, steps, offsets, levels, chains, presence."""
    parts = {}
    for key, p in kit["parts"].items():
        parts[key] = {k: v for k, v in p.items() if k != "notes"}
    return {k: v for k, v in kit.items() if k != "parts"} | {"parts": parts}


def pattern(name, bars=8, parts=None, pitch_map=None):
    """{part: notes} tiled over `bars`. pitch_map: {part: pitch} to play on other pads."""
    kit = load(name)
    out = {}
    for key, p in kit["parts"].items():
        if parts and key not in parts:
            continue
        if not p.get("notes"):
            continue
        out[key] = tile(p["notes"], p["loop_beats"], bars, (pitch_map or {}).get(key))
    return out
