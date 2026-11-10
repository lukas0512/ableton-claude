"""Groove rápido: a whole dance-floor groove in one step, for people who don't program.

`make` writes crisp drums (kick, clap+snare, hats, percussion) and a bassline locked to
the kick, all in one swing pocket, from a vibe (house, tech house, deep house, UK garage,
afro house) or from the feel of tracks the user trained or studied (a profile: tempo,
key, swing, the hats' per-16th timing and accents, the bass's rhythms and degrees).
It also learns: `rate` keeps the person's "gostei / não gostei" per groove, and `make`
steers its automatic choices (bass style, swing) toward what they liked. `apply` puts it in Live with stock sounds through a `call(cmd, args)` that journals each
change (an 8-bar loop, or a DJ-friendly track with intro and outro to mix), and `remove`
takes it out again. Planning is pure; only `apply`/`remove` talk to Live.

Notes are [pitch, start_beat, duration_beats, velocity]. Timing is baked into the MIDI:
no groove from the Groove Pool goes on top of it. A recipe is a starting point that must
be heard; it does not prove the result is good.
"""
import datetime
import hashlib
import json
import math
import os
import random

from . import knowledge, storage
from .music.groove import swing_offset

# Stock Live 12 Drum Racks, pads read from the presets' files (36 = C1).
KIT_909 = "drums/909 Core Kit.adg"
KIT_PERC = "drums/Percussion Core Kit.adg"
PADS_909 = {"kick": 36, "rim": 37, "snare": 38, "clap": 39, "closed_hat": 42,
            "low_tom": 44, "mid_tom": 45, "open_hat": 46, "crash": 48, "ride": 50}
PADS_PERC = {"clave": 37, "conga_low": 38, "cowbell": 39, "conga_hi": 40, "shaker": 41,
             "cabasa": 42, "bongo_low": 43, "bongo_high": 45, "tamb": 48}

# Which track plays which part. Separate tracks so each element gets its own level and
# EQ (the producer's sets work this way); the kick alone keys the bass's sidechain.
TRACKS = ("KICK", "CLAP", "HATS", "PERC", "BASS")
ROLE_TRACK = {"kick": "KICK", "clap": "CLAP", "snare": "CLAP",
              "closed_hat": "HATS", "open_hat": "HATS", "ride": "HATS"}

# x = hit, X = accent, g = ghost, . = rest; two 16-step bars, then an optional phrase end
# that replaces the last bar of every 8 (a turn, never a roll: rolls were rejected).
_VEL = {"X": 118, "x": 96, "g": 58}

VIBES = {
    "house": {
        "label": "House (dub / streets)", "bpm": 128, "swing": 57, "key": ("G", "minor"),
        "bass": "offbeat", "perc_kit": "909",
        "why": "Kick reto, clap sincopado com ghost, hats em 16 com o acento no contratempo "
               "e baixo no contratempo: o balanço do dub house.",
        "drums": {
            "kick": ["X...X...X...X...", "X...X...X...X..."],
            "clap": ["....X.......X..g", "..g.X.......X..."],
            "snare": ["....x.......x...", "....x.......x..."],
            "closed_hat": ["gxXxgxXxgxXxgxXx", "gxXxgxXxgxXxgxXg"],
            "open_hat": ["..g...g...g...g.", "..g...g...g...g."],
            "rim": ["...g..x....g..x.", "...g..x....g.x.."],
        },
        "end": {"clap": "..g.X.......X.gX", "open_hat": "..g...g...g...x."},
    },
    "tech_house": {
        "label": "Tech house", "bpm": 126, "swing": 55, "key": ("F", "minor"),
        "bass": "rolling", "perc_kit": "perc",
        "why": "Kick seco, hats rápidos com ghosts, conga e bongô sincopados e baixo rolante "
               "nos buracos do kick.",
        "drums": {
            "kick": ["X...X...X...X...", "X...X...X...X..."],
            "clap": ["....X.......X...", "....X.......X.g."],
            "closed_hat": ["x.g.xgx.x.g.xgxg", "x.g.xgx.x.g.xgxg"],
            "open_hat": ["..X...X...X...X.", "..X...X...X...X."],
            "conga_low": [".x.....x........", ".x.....X........"],
            "conga_hi": ["......x..x......", "......x..X......"],
            "bongo_low": ["...........x....", "...........X...."],
            "shaker": ["gxgxgxgxgxgxgxgx", "gxgxgxgxgxgxgxgx"],
        },
        "end": {"clap": "....X.....g.X.gX", "bongo_high": "X...x..........."},
    },
    "deep_house": {
        "label": "Deep house", "bpm": 122, "swing": 58, "key": ("A", "minor"),
        "bass": "deep", "perc_kit": "perc",
        "why": "Groove macio: kick redondo, clap no 2 e 4, shaker em 16 bem suingado, "
               "open hat no contratempo e baixo longo e cantado.",
        "drums": {
            "kick": ["x...x...x...x...", "x...x...x...x..."],
            "clap": ["....X.......X...", "....X.......X..."],
            "closed_hat": ["..x...x...x...x.", "..x...x...x.x.x."],
            "open_hat": ["..g...g...g...g.", "..g...g...g...g."],
            "shaker": ["gxgxgxgXgxgxgxgX", "gxgxgxgXgxgxgxgX"],
            "conga_low": ["...........x....", "...x.......x...."],
            "tamb": ["....x.......x...", "....x.......x..."],
        },
        "end": {"conga_hi": "......x..x..x.x."},
    },
    "ukg": {
        "label": "UK garage (2-step)", "bpm": 132, "swing": 63, "key": ("D", "minor"),
        "bass": "2step", "perc_kit": "909",
        "why": "Kick quebrado de 2-step, snare e clap juntos no 2 e 4, hats bem shuffle "
               "e baixo saltando de oitava.",
        "drums": {
            "kick": ["X.........X.....", "X.......X.X....."],
            "clap": ["....X.......X...", "....X.......X..."],
            "snare": ["....X.......X...", "....X.....g.X..."],
            "closed_hat": ["x.xxx.xgx.xxx.xg", "x.xxx.xgx.xxx.xx"],
            "open_hat": ["......g.......g.", "......g.......g."],
            "rim": ["..g....g..g....g", "..g....g..g..g.."],
        },
        "end": {"snare": "....X.....g.X.gX"},
    },
    "afro_house": {
        "label": "Afro house", "bpm": 122, "swing": 54, "key": ("C", "minor"),
        "bass": "sub", "perc_kit": "perc",
        "why": "Kick reto, congas e bongôs conversando, shaker em 16 e um sub que deixa "
               "espaço para a percussão.",
        "drums": {
            "kick": ["X...X...X...X...", "X...X...X...X..."],
            "clap": ["....x.......x...", "....x.......x..."],
            "closed_hat": ["..X...X...X...X.", "..X...X...X...X."],
            "shaker": ["xgxgxgxgxgxgxgxg", "xgxgxgxgxgxgxgxg"],
            "conga_low": ["X......x...x....", "X..x...x...x...."],
            "conga_hi": ["...x.x....x..x.x", "...x.x....x.xx.x"],
            "bongo_low": ["......x.......x.", "......x.....x..."],
            "clave": ["x..x...x..x.x...", "x..x...x..x.x..."],
        },
        "end": {"bongo_high": "........x.x.x.xx"},
    },
}

# Bass: per bar a rhythm (x = note, - = held, . = rest) and the degrees of its notes.
# A degree with + plays an octave up, with - an octave down.
BASSES = {
    "offbeat": {"label": "No contratempo (dub house)",
                "bars": [("..x-..x-..x-..x-", ["1", "1", "1+", "1"]),
                         ("..x-..x-..x-.xx-", ["1", "1", "b7-", "1", "1"])],
                "turn": ["1", "1", "5-", "b7-", "1"],
                "presets": ["sounds/Bass/Analog Bass.adg", "sounds/Bass/Basic Analog Bass.adg"]},
    "rolling": {"label": "Rolante (tech house)",
                "bars": [("..x-.xx...x-.x.x", ["1", "1", "1+", "1", "b7-", "1"]),
                         ("..x-.xx...x-.xx.", ["1", "1", "1+", "1", "5-", "b7-"])],
                "turn": ["1", "1", "1+", "b3", "4", "5"],
                "presets": ["sounds/Bass/Basic Saturated Bass.adg", "sounds/Bass/Analog Bass.adg"]},
    "bounce": {"label": "Bounce (5ª no 2 e 4)",
               "bars": [("..x-x-x-..x-x-xx", ["1", "5-", "1", "1", "5-", "1", "1+"]),
                        ("..x-x-x-..x-x-x.", ["1", "5-", "1", "1", "5-", "b7-"])],
               "turn": ["1", "5-", "1", "b3", "4", "5"],
               "presets": ["sounds/Bass/Analog Bass.adg", "sounds/Bass/Bounce Bass.adg"]},
    "deep": {"label": "Longo e cantado (deep)",
             "bars": [("..x---x-..x-.x--", ["1", "1", "b3", "1"]),
                      ("..x---x-..x-.x-.", ["1", "1", "4", "5-"])],
             "turn": ["1", "1", "b3", "b7-"],
             "presets": ["sounds/Bass/Basic Mello Bass.adg", "sounds/Bass/Analogue Bass.adv"]},
    "2step": {"label": "Saltado (UK garage)",
              "bars": [("x--..x-..x--.x..", ["1", "1+", "1", "b7-"]),
                       ("x--..x-.x-.x..x-", ["1", "1+", "b3", "1", "5-"])],
              "turn": ["1", "1+", "4", "b3", "1"],
              "presets": ["sounds/Bass/Basic Organ Bass.adg", "sounds/Bass/Basic Reese Bass.adg"]},
    "sub": {"label": "Sub com espaço (afro)",
            "bars": [("..x-----..x-..x-", ["1", "1", "b7-"]),
                     ("..x-----..x-.x-.", ["1", "1", "b3", "1"])],
            "turn": ["1", "1", "4", "5-"],
            "presets": ["sounds/Bass/Basic Sub Sine.adg", "sounds/Bass/Basic Sub Boom.adg"]},
}
BASS_FALLBACK = "instruments/Drift"

FEELS = {"reto": -4.0, "leve": -2.0, "padrao": 0.0, "forte": 3.0}
DEGREES = {"1": 0, "b2": 1, "2": 2, "b3": 3, "3": 4, "4": 5, "#4": 6, "b5": 6, "5": 7,
           "b6": 8, "6": 9, "b7": 10, "7": 11}
_ENHARMONIC = {"C": 0, "B#": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4,
               "F": 5, "E#": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9,
               "A#": 10, "Bb": 10, "B": 11, "Cb": 11}
NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

# Small timing roles (ms at the groove's tempo): the clap a hair late sits back, the
# shaker a hair early pushes (the producer's Let The Rhythm kit measured -5 ms).
ROLE_OFFSET_MS = {"clap": 4.0, "snare": 4.0, "shaker": -5.0, "cabasa": -5.0}
LENGTHS = {"open_hat": 0.22, "ride": 0.3, "crash": 1.0}

# Mixer starting points, the producer's kit faders rounded: the kick leads, the motor is
# felt more than heard, the bass present (he raised it above our level twice).
MIX = {"KICK": {"volume_db": -3.0}, "CLAP": {"volume_db": -6.0},
       "HATS": {"volume_db": -10.0, "pan": 0.0}, "PERC": {"volume_db": -11.0, "pan": 0.22},
       "BASS": {"volume_db": -5.0}}
# High-passes that keep the low end to kick and bass: the crisp part of crisp drums.
HIGH_PASS = {"CLAP": "180 Hz", "HATS": "350 Hz", "PERC": "200 Hz"}

# A DJ-friendly track: drums alone at both ends to mix in and out, the kick out of the
# break and build so the drop lands, and its last beat cut before them (a prepared exit).
DANCEFLOOR = [
    ("Intro", 8, ("KICK", "HATS")),
    ("Intro 2", 8, ("KICK", "HATS", "PERC", "CLAP")),
    ("Groove", 16, TRACKS),
    ("Groove 2", 16, TRACKS),
    ("Break", 16, ("HATS", "PERC", "BASS")),
    ("Build", 8, ("CLAP", "HATS", "PERC", "BASS")),
    ("Drop", 32, TRACKS),
    ("Outro", 8, ("KICK", "HATS", "PERC", "CLAP")),
    ("Outro 2", 8, ("KICK", "HATS")),
]
LAYOUTS = ("loop", "pista")


def vibes():
    """What the person can choose, with Portuguese labels for the app."""
    return {"vibes": [{"id": k, "label": v["label"], "bpm": v["bpm"], "swing": v["swing"],
                       "key": "%s %s" % v["key"], "bass": v["bass"]} for k, v in VIBES.items()],
            "basses": [{"id": k, "label": v["label"]} for k, v in BASSES.items()],
            "feels": list(FEELS), "layouts": list(LAYOUTS),
            "inspirations": [g["genre"] for g in knowledge.trained_genres()]}


def _pc(name):
    name = str(name).strip()
    name = name[:1].upper() + name[1:]
    if name not in _ENHARMONIC:
        raise ValueError("tom desconhecido: %r (use C, C#, D, Eb...)" % name)
    return _ENHARMONIC[name]


def _bass_root(tonic):
    """The tonic between E1 (28) and D#2 (39): low enough to weigh, high enough to be heard."""
    root = 24 + _pc(tonic)
    return root + 12 if root < 28 else root


def _degree(token, root, mode):
    shift = 12 if token.endswith("+") else -12 if token.endswith("-") else 0
    deg = token.rstrip("+-")
    semis = DEGREES[deg]
    if mode == "major" and deg in ("b3", "b6", "b7"):
        semis += 1          # the same shape in a major key
    return root + semis + shift


def _ms_to_beats(ms, bpm):
    return ms * bpm / 60000.0


def _phrase_end(bar, bars):
    """The last bar of every 8 (of every 4 in a 4-bar loop) turns the phrase."""
    phrase = min(8, bars)
    return bar % phrase == phrase - 1


def _steps_notes(bars_steps, pitch, bars, swing, bpm, offset_ms=0.0, length=0.1,
                 end=None, rng=None, vel_scale=1.0):
    """Tile per-bar 16-step strings over `bars`; `end` replaces the last bar of every 8."""
    notes = []
    for bar in range(bars):
        steps = bars_steps[bar % len(bars_steps)]
        if end and _phrase_end(bar, bars):
            steps = end
        for step, ch in enumerate(steps):
            if ch not in _VEL:
                continue
            start = bar * 4 + step * 0.25 + swing_offset(step, swing) + _ms_to_beats(offset_ms, bpm)
            vel = _VEL[ch] * vel_scale + (rng.randint(-5, 5) if rng and ch != "X" else 0)
            notes.append([pitch, round(max(0.0, start), 4), length, int(max(1, min(127, vel)))])
    return notes


def _template_hats(template, presence, pitch, bars, bpm, rng):
    """The references' hats: every 16th they mostly play, at their own timing and accents."""
    steps = {s["step"]: s for s in template.get("steps", []) if s.get("offset_ms") is not None}
    notes = []
    for bar in range(bars):
        for step in range(16):
            s = steps.get(step)
            if s is None or (presence and presence[step] < 0.55):
                continue
            accent = s.get("accent_db") or 0.0
            vel = 115 + 3.5 * accent + rng.randint(-4, 4)
            start = bar * 4 + step * 0.25 + _ms_to_beats(s["offset_ms"], bpm)
            notes.append([pitch, round(max(0.0, start), 4), 0.1, int(max(40, min(127, vel)))])
    return notes


def _bass_notes(recipe, root, mode, bars, swing):
    notes = []
    for bar in range(bars):
        rhythm, degrees = recipe["bars"][bar % len(recipe["bars"])]
        if _phrase_end(bar, bars):
            degrees = recipe.get("turn", degrees)
        onsets = [i for i, ch in enumerate(rhythm) if ch == "x"]
        for k, step in enumerate(onsets):
            held = 1
            while step + held < 16 and rhythm[step + held] == "-":
                held += 1
            start = bar * 4 + step * 0.25 + swing_offset(step, swing)
            # A gate that ends before the next 16th: the synth's release does the rest.
            dur = max(0.12, held * 0.25 - 0.04)
            pitch = _degree(degrees[k % len(degrees)], root, mode)
            vel = 112 if k == 0 else 100 if rhythm[step - 1:step] != "x" else 92
            notes.append([pitch, round(start, 4), round(dur, 4), vel])
    return notes


def _profile_bass(ear_bass, seed):
    """A bass recipe from the references' heard rhythms and their most used degrees."""
    rhythms = [r[0] for r in ear_bass.get("rhythms", []) if isinstance(r, (list, tuple))
               and isinstance(r[0], str) and len(r[0]) == 16 and "x" in r[0]]
    if not rhythms:
        return None
    rng = random.Random(seed)
    first = rhythms[seed % len(rhythms)]
    second = rhythms[(seed + 1) % len(rhythms)] if len(rhythms) > 1 else first
    weights = {d: w for d, w in (ear_bass.get("degrees") or {}).items() if d in DEGREES and w >= 0.04}
    others = [d for d in sorted(weights, key=weights.get, reverse=True) if d != "1"][:4] or ["5", "b7"]

    def degrees(rhythm):
        n = rhythm.count("x")
        out = ["1"]
        for i in range(1, n):
            # Mostly the root (the references' first degree), colour from their next ones.
            d = "1" if rng.random() < weights.get("1", .4) + .2 else rng.choice(others)
            out.append(d + ("-" if DEGREES[d] >= 7 else ""))
        return out

    turn = degrees(second)
    turn[-1] = "5-"
    return {"label": "Das referências", "bars": [(first, degrees(first)), (second, degrees(second))],
            "turn": turn, "presets": BASSES["offbeat"]["presets"]}


def inspiration(name):
    """Tempo, key, swing and the heard drums/bass of a trained genre or reference study."""
    prof = knowledge.load_profile(name)
    if not prof:
        raise ValueError("Não encontrei o perfil %r. Treine o gênero ou estude as referências primeiro." % name)
    out = {"name": prof.get("genre") or name, "n_tracks": prof.get("n_tracks")}
    bpm = (prof.get("bpm") or {}).get("median")
    if bpm:
        out["bpm"] = round(float(bpm), 1)
    ear = prof.get("ear") or {}
    swing = ear.get("hat_swing_pct") or (prof.get("swing_pct") or {}).get("median")
    if isinstance(swing, dict):
        swing = swing.get("median")
    if swing:
        out["swing"] = round(float(swing), 1)
    keys = prof.get("keys") or {}
    if keys:
        best = max(keys, key=keys.get).split()
        if len(best) == 2 and best[0][:1].upper() + best[0][1:] in _ENHARMONIC:
            out["key"] = (best[0], best[1].lower())
    drums = ear.get("drums") or {}
    hats = drums.get("hats") or {}
    if isinstance(hats.get("template"), dict) and hats["template"].get("steps"):
        presence = hats.get("step_presence")
        if isinstance(presence, str):
            presence = json.loads(presence)
        out["hats"] = {"template": hats["template"], "presence": presence}
    if (ear.get("four_on_floor_share") or 1) < 0.5:
        out["broken_kick"] = True
    kick = _learned_kick(drums.get("kick") or {}, out.get("broken_kick"))
    if kick:
        out["kick"] = kick
    clap_ms = _learned_clap_ms(drums.get("clap") or {}, ear.get("backbeat_share"))
    if clap_ms is not None:
        out["clap_ms"] = clap_ms
    if isinstance(ear.get("bass"), dict):
        out["bass"] = ear["bass"]
    brk = ((prof.get("structure") or {}).get("main_break_bars") or {}).get("median")
    if brk:
        out["break_bars"] = int(min(32, max(8, int(brk / 8.0 + .5) * 8)))
    return out


def _presence(part):
    pres = part.get("step_presence")
    if isinstance(pres, str):
        try:
            pres = json.loads(pres)
        except ValueError:
            return None
    if isinstance(pres, list) and len(pres) == 16 and all(isinstance(x, (int, float)) for x in pres):
        return pres
    return None


def _learned_kick(kick, broken):
    """The references' kick as a step string. Four-on-the-floor keeps its quarters and only
    gains the ghost kicks they play between them; a broken kick takes their whole pattern."""
    pres = _presence(kick)
    if not pres or pres[0] < 0.5:
        return None
    cells = []
    for step, p in enumerate(pres):
        if step == 0 or (step % 4 == 0 and not broken):
            cells.append("X")
        elif p >= 0.75:
            cells.append("X" if step % 4 == 0 else "x")
        elif p >= 0.5:
            cells.append("x")
        elif p >= 0.3 and step % 4:
            cells.append("g")
        else:
            cells.append(".")
    pattern = "".join(cells)
    return pattern if pattern.count("X") + pattern.count("x") >= 2 else None


def _learned_clap_ms(clap, backbeat_share):
    """How late the references' clap sits on 2 and 4 (ms), when they have a backbeat."""
    if (backbeat_share or 0) < 0.5:
        return None
    steps = (clap.get("template") or {}).get("steps") or []
    offs = [s["offset_ms"] for s in steps if isinstance(s, dict) and s.get("step") in (4, 12)
            and isinstance(s.get("offset_ms"), (int, float))]
    if not offs:
        return None
    return round(min(20.0, max(-8.0, sum(offs) / len(offs))), 1)


# ---- Learning from the person's opinion -------------------------------------------------

def taste_path():
    return os.path.join(storage.DATA_DIR, "Production", "groove_taste.json")


def load_taste(path=None):
    try:
        with open(path or taste_path(), encoding="utf-8") as f:
            taste = json.load(f)
        if isinstance(taste, dict) and isinstance(taste.get("votes"), list):
            return taste
    except (OSError, ValueError):
        pass
    return {"votes": []}


def learned(taste, vibe):
    """What the votes on this vibe say: likes, dislikes, a score per bass style and the
    swing (before the feel) of the grooves they liked."""
    votes = [v for v in (taste or {}).get("votes", []) if isinstance(v, dict) and v.get("vibe") == vibe]
    likes = [v for v in votes if v.get("liked")]
    scores = {}
    for v in votes:
        if v.get("bass") in BASSES:
            scores[v["bass"]] = scores.get(v["bass"], 0) + (1 if v.get("liked") else -1)
    swings = [float(v["base_swing"]) for v in likes if isinstance(v.get("base_swing"), (int, float))]
    return {"likes": len(likes), "dislikes": len(votes) - len(likes), "bass_scores": scores,
            "swing": round(sum(swings) / len(swings), 1) if swings else None, "n_swing": len(swings)}


def rate(groove, liked, path=None):
    """Keep one vote per groove (a new opinion replaces the old) and return what's learned."""
    path = path or taste_path()
    taste = load_taste(path)
    vote = {"id": groove["id"], "vibe": groove["vibe"], "bass": groove["bass"],
            "feel": groove["feel"], "swing": groove["swing"], "base_swing": groove.get("base_swing"),
            "bpm": groove["bpm"], "inspired_by": groove.get("inspired_by"), "seed": groove["seed"],
            "liked": bool(liked), "at": datetime.datetime.now().isoformat(timespec="seconds")}
    taste["votes"] = [v for v in taste["votes"] if v.get("id") != vote["id"]][-499:] + [vote]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(taste, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return learned(taste, groove["vibe"])


def make(vibe="house", tonic=None, mode=None, bpm=None, swing=None, feel="padrao",
         bass="auto", inspired_by=None, bars=8, seed=1, taste=None):
    """The whole groove, planned: settings, notes per track, a step grid to show, and why.
    `taste` (from load_taste) steers the automatic choices toward the grooves they liked."""
    if vibe not in VIBES:
        raise ValueError("Escolha uma vibe: %s" % ", ".join(VIBES))
    if bars not in (4, 8, 16):
        raise ValueError("O loop tem 4, 8 ou 16 compassos.")
    if feel not in FEELS:
        raise ValueError("Swing: %s" % ", ".join(FEELS))
    v = VIBES[vibe]
    ref = inspiration(inspired_by) if inspired_by else {}
    tonic = tonic or (ref.get("key") or v["key"])[0]
    mode = (mode or (ref.get("key") or v["key"])[1]).lower()
    if mode not in ("minor", "major"):
        raise ValueError("Modo: minor ou major.")
    bpm = float(bpm or ref.get("bpm") or v["bpm"])
    if not 90 <= bpm <= 150:
        raise ValueError("BPM entre 90 e 150.")
    mine = learned(taste, vibe) if taste else None
    taught = []
    if swing is not None or ref.get("swing"):
        base_swing = float(swing if swing is not None else ref["swing"])
    else:
        base_swing = float(v["swing"])
        if mine and mine["swing"] is not None:
            # Toward the swing of the grooves they liked, more the more they liked.
            n = mine["n_swing"]
            base_swing = round(base_swing + (mine["swing"] - base_swing) * n / (n + 1.0), 1)
            if abs(base_swing - v["swing"]) >= 0.5:
                taught.append("swing %.0f %%" % base_swing)
    swing = round(min(66.0, max(50.0, base_swing + FEELS[feel])), 1)
    seed = int(seed)
    rng = random.Random(seed)

    pads = dict(PADS_909)
    perc_pads = PADS_PERC if v["perc_kit"] == "perc" else PADS_909
    parts = {t: [] for t in TRACKS}
    grid = {}
    for role, steps in v["drums"].items():
        track = ROLE_TRACK.get(role, "PERC")
        pitch = (pads if track != "PERC" else perc_pads)[role]
        if role == "kick" and ref.get("kick"):
            steps = [ref["kick"]]
        offset = ROLE_OFFSET_MS.get(role, 0.0)
        if role in ("clap", "snare") and ref.get("clap_ms") is not None:
            offset = ref["clap_ms"]
        if role == "closed_hat" and ref.get("hats"):
            notes = _template_hats(ref["hats"]["template"], ref["hats"].get("presence"),
                                   pitch, bars, bpm, rng)
        else:
            notes = _steps_notes(steps, pitch, bars, swing, bpm, offset,
                                 LENGTHS.get(role, 0.1), v.get("end", {}).get(role), rng,
                                 0.8 if role == "snare" and vibe != "ukg" else 1.0)
        parts[track].extend(notes)
        grid[role] = _grid(notes, bpm)
    for role, end in v.get("end", {}).items():
        if role not in v["drums"]:          # a part that only plays the phrase end
            pitch = perc_pads[role]
            parts["PERC"].extend(_steps_notes(["................"], pitch, bars, swing, bpm,
                                              end=end, rng=rng))

    recipe = None
    bass_id = v["bass"] if bass == "auto" else bass
    if bass in ("auto", "referencia") and ref.get("bass"):
        recipe = _profile_bass(ref["bass"], seed)
        if recipe:
            bass_id = "referencia"
    if recipe is None and bass == "auto" and mine and mine["bass_scores"]:
        scores = mine["bass_scores"]
        best = max(sorted(scores), key=scores.get)
        if scores[best] > 0 and scores[best] > scores.get(bass_id, 0):
            bass_id = best
            taught.append("baixo %s" % BASSES[best]["label"].lower())
    if recipe is None:
        if bass_id == "referencia":
            bass_id = v["bass"]
        if bass_id not in BASSES:
            raise ValueError("Baixo: auto, referencia ou %s" % ", ".join(BASSES))
        recipe = BASSES[bass_id]
    root = _bass_root(tonic)
    parts["BASS"] = _bass_notes(recipe, root, mode, bars, swing)
    grid["bass"] = _grid(parts["BASS"], bpm)
    for track in parts:
        parts[track].sort(key=lambda n: (n[1], n[0]))

    key_name = "%s %s" % (NOTE_NAMES[_pc(tonic)], mode)
    kicks = {round(n[1], 2) for n in parts["KICK"]}
    with_kick = sum(round(n[1], 2) in kicks for n in parts["BASS"]) / max(1, len(parts["BASS"]))
    why = [v["why"],
           "Swing de %.0f %% em tudo (menos no kick, que é a régua): um só bolso." % swing,
           "Baixo %s em %s, %s e com sidechain do kick." % (
               recipe["label"].lower(), key_name,
               "fora das batidas do kick" if with_kick <= .15 else "dividindo %d %% das notas com o kick" % round(100 * with_kick)),
           "Graves só no kick e no baixo: clap, hats e percussão com corte abaixo de 180-350 Hz."]
    if ref:
        n = ref.get("n_tracks") or 0
        why.insert(0, "Inspirado em %s (%s): %s BPM, swing %.0f %%%s." % (
            ref["name"], "%d faixa%s" % (n, "" if n == 1 else "s") if n else "referências",
            ref.get("bpm", bpm), ref.get("swing", swing),
            "".join(part for part, on in (
                (", hats com o tempo e os acentos delas", ref.get("hats")),
                (", o kick delas", ref.get("kick")),
                (", o clap %+.0f ms como nelas" % ref.get("clap_ms", 0), ref.get("clap_ms") is not None))
                if on)))
    if mine and (mine["likes"] or mine["dislikes"]):
        why.append("Aprendendo com você (%d gostei, %d não gostei)%s." % (
            mine["likes"], mine["dislikes"], ": " + ", ".join(taught) if taught else ""))
    groove = {
        "vibe": vibe, "label": v["label"], "bars": bars, "bpm": bpm, "swing": swing,
        "base_swing": round(base_swing, 1),
        "tonic": NOTE_NAMES[_pc(tonic)], "mode": mode, "key": key_name, "feel": feel,
        "bass": bass_id, "bass_label": recipe["label"], "seed": seed,
        "inspired_by": ref.get("name"), "perc_kit": v["perc_kit"],
        "bass_presets": recipe["presets"], "notes": parts, "grid": grid, "why": why,
        "break_bars": ref.get("break_bars"),
        "counts": {t: len(n) for t, n in parts.items()},
        "learned": {"likes": mine["likes"], "dislikes": mine["dislikes"]} if mine else None,
    }
    groove["id"] = hashlib.sha1(json.dumps(groove, sort_keys=True).encode()).hexdigest()[:10]
    return groove


def _grid(notes, bpm):
    """The first bar as 16 cells for the app's step view: '.', 'g', 'x', 'X'."""
    cells = ["."] * 16
    for _, start, _, vel in notes:
        if start >= 4:
            continue
        step = int(round(start * 4))
        if step >= 16:
            continue
        mark = "X" if vel >= 110 else "x" if vel >= 75 else "g"
        if cells[step] == "." or mark == "X":
            cells[step] = mark
    return "".join(cells)


def summary(groove):
    """The groove without its note lists: what the app shows before applying."""
    return {k: v for k, v in groove.items() if k != "notes"}


def tile(notes, loop_beats, beats, cut_last_beat=False):
    out = []
    k = 0
    while k * loop_beats < beats:
        for p, s, d, vel in notes:
            t = s + k * loop_beats
            if t < beats - (1.0 if cut_last_beat else 0.0) - 1e-9:
                out.append([p, round(t, 4), round(min(d, beats - t), 4), vel])
        k += 1
    return out


def sections(groove, layout):
    """[(name, start_offset_bars, bars, tracks, cut_last_beat)] relative to the start bar."""
    if layout == "loop":
        return [("Groove", 0, groove["bars"], TRACKS, set())]
    if layout != "pista":
        raise ValueError("Formato: loop ou pista.")
    plan = [(n, b, t) for n, b, t in DANCEFLOOR]
    if groove.get("break_bars"):
        plan = [(n, groove["break_bars"] if n == "Break" else b, t) for n, b, t in plan]
    out, at = [], 0
    for i, (name, bars, tracks) in enumerate(plan):
        nxt = plan[i + 1][2] if i + 1 < len(plan) else tracks
        cut = {t for t in tracks if t == "KICK" and t not in nxt}
        out.append((name, at, bars, tracks, cut))
        at += bars
    return out


def _start_bar(song):
    num, den = map(int, song.get("signature", "4/4").split("/"))
    bpb = num * 4.0 / den
    occupied = any(t.get("clips_active", 0) for t in song.get("tracks", []))
    start = math.ceil(float(song.get("song_length_beats", 0)) / bpb) + 9 if occupied else 1
    return start, occupied, bpb


def _names(song):
    taken = {t.get("name") for t in song.get("tracks", [])}
    n = 1
    while any("G%d · %s" % (n, t) in taken for t in TRACKS):
        n += 1
    return {t: "G%d · %s" % (n, t) for t in TRACKS}, n


def apply(groove, call, layout="loop"):
    """Build the groove in the open Live set through `call(cmd, args)`. Stops on the first
    failure that matters (a track, a kit, a clip); polish that fails (an EQ value, the
    sidechain) is reported and skipped. Returns a receipt with what to remove later."""
    if layout not in LAYOUTS:
        raise ValueError("Formato: loop ou pista.")
    song = call("get_song", {})
    start, occupied, bpb = _start_bar(song)
    if bpb != 4:
        raise ValueError("O groove rápido funciona em 4/4.")
    names, number = _names(song)
    receipt = {"groove": groove["id"], "number": number, "tracks": [], "start_bar": start,
               "layout": layout, "warnings": [], "cues": [], "tempo_before": song.get("tempo")}
    if not occupied:
        call("set_tempo", {"bpm": groove["bpm"]})
        receipt["tempo_set"] = groove["bpm"]
    else:
        receipt["warnings"].append("O set já tem música: mantive o tempo dele (%.1f BPM) e coloquei o "
                                   "groove depois do fim, no compasso %d." % (song.get("tempo", 0), start))
    kits = {"KICK": KIT_909, "CLAP": KIT_909, "HATS": KIT_909,
            "PERC": KIT_PERC if groove["perc_kit"] == "perc" else KIT_909}
    for track in TRACKS:
        name = names[track]
        call("create_track", {"kind": "midi", "name": name})
        receipt["tracks"].append(name)
        if track == "BASS":
            loaded = None
            for path in groove["bass_presets"] + [BASS_FALLBACK]:
                try:
                    call("load_device", {"track": name, "path": path})
                    loaded = path
                    break
                except Exception:
                    continue
            if loaded is None:
                raise RuntimeError("Nenhum som de baixo carregou no Live.")
            receipt["bass_sound"] = loaded.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        else:
            call("load_device", {"track": name, "path": kits[track]})
        mix = dict(MIX[track], track=name)
        call("set_track", mix)
        if track in HIGH_PASS:
            _polish(call, receipt, name, "EQ Eight", {
                "1 Filter On A": ("item", "On"), "1 Filter Type A": ("item", "High Pass 12dB"),
                "1 Frequency A": ("display", HIGH_PASS[track])})
    # The bass ducks under the kick for its first ~90 ms: the pump that locks them.
    _polish(call, receipt, names["BASS"], "Compressor", {
        "Ratio": ("display", "4.00 : 1"), "Attack": ("display", "0.10 ms"),
        "Release": ("display", "90.0 ms"), "Threshold": ("display", "-24.0 dB")},
        sidechain=names["KICK"])

    loop_beats = groove["bars"] * 4.0
    plan = sections(groove, layout)
    for sec_name, offset, bars, tracks, cut in plan:
        bar = start + offset
        for track in tracks:
            notes = tile(groove["notes"][track], loop_beats, bars * 4.0, track in cut)
            if notes:
                call("create_midi_clip", {"track": names[track], "length": bars * 4.0, "bar": bar,
                                          "notes": notes, "name": sec_name})
        if layout == "pista":
            try:
                call("set_cue", {"name": "%s G%d" % (sec_name, number), "bar": bar})
                receipt["cues"].append(bar)
            except Exception as exc:
                receipt["warnings"].append("Marcador %s: %s" % (sec_name, exc))
    end = start + sum(b for _, _, b, _, _ in plan)
    receipt["end_bar"] = end
    try:
        call("set_loop", {"on": True, "start_bar": start,
                          "end_bar": start + groove["bars"] if layout == "loop" else end})
    except Exception as exc:
        receipt["warnings"].append("Loop do Live: %s" % exc)
    return receipt


def _polish(call, receipt, track, device, params, sidechain=None):
    try:
        call("load_device", {"track": track, "path": "audio_effects/" + device})
    except Exception as exc:
        receipt["warnings"].append("%s em %s: %s" % (device, track, exc))
        return
    for param, (kind, value) in params.items():
        try:
            call("set_param", {"track": track, "device": device, "param": param, kind: value})
        except Exception as exc:
            receipt["warnings"].append("%s %s: %s" % (device, param, exc))
    if sidechain:
        # No channel: a track's default is Post FX, and reading the channel list right after
        # switching the input is the read that crashed Live (docs/one-pass-crash.md).
        try:
            call("set_device_input", {"track": track, "device": device, "source": sidechain})
        except Exception as exc:
            receipt["warnings"].append("Sidechain do baixo: %s" % exc)


def remove(receipt, call):
    """Take a groove back out: its tracks, its markers and the tempo it set."""
    removed, warnings = [], []
    for name in reversed(receipt.get("tracks", [])):
        try:
            call("delete_track", {"track": name})
            removed.append(name)
        except Exception as exc:
            warnings.append("%s: %s" % (name, exc))
    for bar in receipt.get("cues", []):
        try:
            call("delete_cue", {"bar": bar})
        except Exception as exc:
            warnings.append("Marcador %s: %s" % (bar, exc))
    if receipt.get("tempo_set") and receipt.get("tempo_before"):
        try:
            call("set_tempo", {"bpm": receipt["tempo_before"]})
        except Exception as exc:
            warnings.append("Tempo: %s" % exc)
    return {"removed": removed, "warnings": warnings}
