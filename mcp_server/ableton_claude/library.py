"""The user's sample library as a resource.

Every file is indexed once: what it is (kick, clap, hat, shaker, perc, drum or top loop,
bass, chord/stab, pad, lead, vocal, fx, midi), whether it is a loop, and the tempo and key
its pack wrote into the name, plus its length from the file header. Search ranks by role,
key compatibility, tempo and the pack's genre words; timbre (brightness, length) is
measured only for the candidates, so a 26,000-file library indexes in seconds and a pick
can still follow a genre's measured sound.
"""
import json
import os
import re
import time

import soundfile as sf

from . import knowledge

INDEX_PATH = os.path.normpath(os.path.join(knowledge.KNOWLEDGE_DIR, "..", "samples_index.json"))
AUDIO = (".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg")
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ROLE_WORDS = [  # checked in order: the first role whose word appears wins
    ("midi", []),
    ("fx", ["fx", "sfx", "riser", "uplifter", "downlifter", "impact", "sweep", "whoosh", "noise", "reverse", "atmos fx", "transition"]),
    ("vocal", ["vocal", "vox", "voice", "acapella", "adlib", "chant", "spoken", "phrase"]),
    ("top_loop", ["top loop", "toploop", "tops", "top_", "hat loop", "perc loop", "percussion loop", "shaker loop"]),
    ("drum_loop", ["drum loop", "drumloop", "drum_loop", "full loop", "beat loop", "drums loop", "groove loop"]),
    ("kick", ["kick", "kck", "bd_", "bassdrum", "bass drum"]),
    ("clap", ["clap", "clp"]),
    ("snare", ["snare", "snr", "rimshot"]),
    ("hat", ["hat", "hh_", "hihat", "hi-hat", "hi hat", "closed", "open h"]),
    ("ride", ["ride"]),
    ("crash", ["crash", "cymbal"]),
    ("shaker", ["shaker", "shk", "tamb", "maraca", "cabasa"]),
    ("perc", ["perc", "conga", "bongo", "rim", "clave", "cowbell", "tom", "wood", "block", "timbale", "djembe", "snap"]),
    ("bass", ["bass", "sub ", "sub_", "808", "reese"]),
    ("chord", ["chord", "stab", "keys", "piano", "rhodes", "organ", "epiano", "e-piano"]),
    ("pad", ["pad", "atmos", "ambient", "texture", "drone", "strings"]),
    ("lead", ["lead", "synth", "arp", "pluck", "melody", "hook", "riff", "sequence", "seq"]),
]
LOOP_WORDS = ("loop", "bpm", "groove", "full", "_lp", "sequence")
GENRE_WORDS = ("deep house", "tech house", "house", "techno", "minimal", "garage", "afro", "disco", "melodic")


def _key(name):
    """(tonic_pc, mode) from a sample name, e.g. 'Stab_Gm', 'Chord_F#min', 'Bass A minor 124'.
    A lone letter ('Loop A') is not a key."""
    toks = [t for t in re.split(r"[\s_\-.()\[\]]+", name) if t]
    for i, t in enumerate(toks):
        m = re.fullmatch(r"([A-G])(#|b|s)?((?i:minor|min|major|maj)|m|M)?", t)
        if not m:
            continue
        suffix = m.group(3)
        nxt = toks[i + 1].lower() if i + 1 < len(toks) else ""
        if suffix is None and nxt in ("minor", "major", "min", "maj"):
            suffix = nxt
        if suffix is None and not m.group(2):
            continue
        pc = (NOTE[m.group(1)] + {"#": 1, "s": 1, "b": -1}.get(m.group(2) or "", 0)) % 12
        if suffix and (suffix == "M" or suffix.lower() in ("maj", "major")):
            mode = "major"
        elif suffix and suffix.lower() in ("m", "min", "minor"):
            mode = "minor"
        else:
            mode = None
        return pc, mode
    return None, None


def _bpm(name):
    m = re.search(r"(\d{2,3})\s*bpm", name, re.I) or re.search(r"(?:^|[\s_\-])(\d{2,3})(?:[\s_\-]|$)", name)
    if m:
        v = int(m.group(1))
        if 70 <= v <= 180:
            return v
    return None


def classify(path, dur_s=None):
    low = path.lower()
    name = os.path.splitext(os.path.basename(path))[0]
    fname = name.lower()
    role = None
    for r, words in ROLE_WORDS[1:]:                        # the file name decides first
        if any(w in fname for w in words):
            role = r
            break
    if role is None:
        for r, words in ROLE_WORDS[1:]:                    # then the folders
            if any(w in low for w in words):
                role = r
                break
    midi = low.endswith((".mid", ".midi"))
    one_shot_folder = any(w in low for w in ("one shot", "oneshot", "one-shot", "one_shot", "single hit", "hits"))
    named_loop = "loop" in fname or _bpm(name) is not None
    if midi:
        loop = True
    elif one_shot_folder and "loop" not in fname:
        loop = False
    elif dur_s is not None:
        loop = dur_s >= 1.8 and (named_loop or dur_s >= 3.5)
    else:
        loop = named_loop
    tonic, mode = _key(name)
    return {"role": "midi" if midi else (role or "other"), "midi_role": (role or "other") if midi else None,
            "loop": bool(loop), "bpm": _bpm(name), "key_pc": tonic, "mode": mode,
            "genre_words": [g for g in GENRE_WORDS if g in low]}


def build_index(roots, log=None):
    rows, t = [], time.time()
    for root in roots:
        for dp, _, files in os.walk(root):
            for f in files:
                if f.startswith("."):
                    continue
                low = f.lower()
                if not low.endswith(AUDIO + (".mid", ".midi")):
                    continue
                p = os.path.join(dp, f)
                dur, sr_ = None, None
                if low.endswith((".wav", ".aif", ".aiff", ".flac", ".ogg")):
                    try:
                        info = sf.info(p)
                        dur, sr_ = round(info.duration, 2), info.samplerate
                    except Exception:
                        pass
                rows.append({"path": p, "dur_s": dur, "sr": sr_, **classify(p, dur)})
    idx = {"roots": roots, "built": time.strftime("%Y-%m-%d %H:%M"), "n": len(rows), "items": rows}
    tmp = INDEX_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(idx, fh)
    os.replace(tmp, INDEX_PATH)
    if log:
        log("indexed %d files in %.1fs" % (len(rows), time.time() - t))
    return idx


def load_index():
    return json.load(open(INDEX_PATH)) if os.path.exists(INDEX_PATH) else None


def summary(idx):
    import collections
    c = collections.Counter((r["role"], r["loop"]) for r in idx["items"])
    return {"%s%s" % (role, " loops" if loop else ""): n for (role, loop), n in c.most_common()}


def _key_fit(row, key_pc, mode):
    if key_pc is None or row["key_pc"] is None:
        return 0.0
    if row["key_pc"] == key_pc and (row["mode"] in (None, mode)):
        return 1.0
    rel = (key_pc + 3) % 12 if mode == "minor" else (key_pc - 3) % 12     # relative major/minor
    if row["key_pc"] == rel and row["mode"] != mode:
        return 0.8
    if (row["key_pc"] - key_pc) % 12 in (5, 7):                           # a fifth away
        return 0.3
    return -1.0


def search(role=None, text=None, key_pc=None, mode=None, bpm=None, loop=None, genre=None, limit=20, idx=None):
    idx = idx or load_index()
    if not idx:
        raise RuntimeError("no sample index yet: run library.build_index(roots)")
    words = [w.lower() for w in (text or "").split() if w]
    out = []
    for r in idx["items"]:
        if role and r["role"] != role:
            continue
        if loop is not None and bool(r["loop"]) != bool(loop):
            continue
        low = r["path"].lower()
        if words and not all(w in low for w in words):
            continue
        s = 0.0
        kf = _key_fit(r, key_pc, mode)
        if key_pc is not None and r["role"] in ("bass", "chord", "pad", "lead", "vocal", "midi"):
            if kf < 0:
                continue                                                     # wrong key for tonal material
            s += 2.0 * kf
        if bpm and r.get("bpm"):
            ratio = min(abs(r["bpm"] - bpm), abs(r["bpm"] * 2 - bpm), abs(r["bpm"] / 2 - bpm))
            s += max(0.0, 1.0 - ratio / 6.0)
        if genre:
            s += 0.8 * sum(1 for g in genre.lower().split("|") if g in r["genre_words"])
        out.append((round(s, 3), r))
    out.sort(key=lambda t: -t[0])
    return [dict(r, score=s) for s, r in out[:limit]]
