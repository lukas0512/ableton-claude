"""Pitch classes, scales, chord symbols, roman numerals and voice leading.

Everything works on MIDI note numbers (60 = C4) and pitch classes (0 = C).
"""
import itertools
import re

NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
_PC = {n: i for i, n in enumerate(NOTE_NAMES)}
_PC.update({"Db": 1, "D#": 3, "Gb": 6, "G#": 8, "A#": 10, "Cb": 11, "B#": 0,
            "E#": 5, "Fb": 4})

SCALES = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "harmonic_minor": (0, 2, 3, 5, 7, 8, 11),
    "melodic_minor": (0, 2, 3, 5, 7, 9, 11),
    "minor_pentatonic": (0, 3, 5, 7, 10),
    "major_pentatonic": (0, 2, 4, 7, 9),
    # Aeolian and Dorian minus their 6th: sits under both, a deep house staple.
    "minor_hexatonic": (0, 2, 3, 5, 7, 10),
}
SCALES["ionian"] = SCALES["major"]
SCALES["aeolian"] = SCALES["minor"]

# interval sets, root = 0; 14/17/21 are 9th/11th/13th
QUALITIES = {
    "": (0, 4, 7), "maj": (0, 4, 7), "m": (0, 3, 7), "min": (0, 3, 7),
    "dim": (0, 3, 6), "aug": (0, 4, 8), "5": (0, 7),
    "sus2": (0, 2, 7), "sus4": (0, 5, 7), "sus": (0, 5, 7),
    "6": (0, 4, 7, 9), "m6": (0, 3, 7, 9), "6/9": (0, 4, 7, 9, 14),
    "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10),
    "m7b5": (0, 3, 6, 10), "dim7": (0, 3, 6, 9), "mmaj7": (0, 3, 7, 11),
    "7sus4": (0, 5, 7, 10), "7sus2": (0, 2, 7, 10),
    "add9": (0, 4, 7, 14), "madd9": (0, 3, 7, 14),
    "9": (0, 4, 7, 10, 14), "maj9": (0, 4, 7, 11, 14), "m9": (0, 3, 7, 10, 14),
    "11": (0, 4, 7, 10, 14, 17), "m11": (0, 3, 7, 10, 14, 17),
    "m7add11": (0, 3, 7, 10, 17), "9sus4": (0, 5, 7, 10, 14),
    "13": (0, 4, 7, 10, 14, 21), "maj13": (0, 4, 7, 11, 14, 21),
}

_CHORD_RE = re.compile(r"^([A-G](?:#|b)?)(.*?)(?:/([A-G](?:#|b)?))?$")
_ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7}


def pc(name):
    """'Bb' -> 10. Integers pass through as pitch classes."""
    if isinstance(name, int):
        return name % 12
    if name not in _PC:
        raise ValueError("unknown note name: %r" % name)
    return _PC[name]


def note_name(midi):
    return "%s%d" % (NOTE_NAMES[midi % 12], midi // 12 - 1)


class Scale(object):
    def __init__(self, tonic, mode="minor"):
        if mode not in SCALES:
            raise ValueError("unknown scale %r; known: %s" % (mode, sorted(SCALES)))
        self.tonic = pc(tonic)
        self.mode = mode
        self.intervals = SCALES[mode]

    def __repr__(self):
        return "Scale(%s %s)" % (NOTE_NAMES[self.tonic], self.mode)

    @property
    def pcs(self):
        return [(self.tonic + i) % 12 for i in self.intervals]

    def contains(self, pitch):
        return pitch % 12 in self.pcs

    def degree(self, pitch):
        """1-based scale degree of a pitch, or None if outside the scale."""
        p = pitch % 12
        return self.pcs.index(p) + 1 if p in self.pcs else None

    def pitches(self, low, high):
        return [p for p in range(low, high + 1) if self.contains(p)]

    def nearest(self, pitch):
        for d in range(12):
            for cand in (pitch - d, pitch + d):
                if self.contains(cand):
                    return cand
        raise AssertionError("empty scale")

    def step(self, pitch, n):
        """Move n scale steps from pitch (snapped into the scale first)."""
        p = self.nearest(pitch)
        direction = 1 if n > 0 else -1
        for _ in range(abs(n)):
            p += direction
            while not self.contains(p):
                p += direction
        return p


def parse_chord(symbol):
    """'Gm7' -> (7, (0, 3, 7, 10), None); 'Bbmaj7/A' -> (10, (0,4,7,11), 9)."""
    m = _CHORD_RE.match(symbol.strip())
    if not m:
        raise ValueError("bad chord symbol: %r" % symbol)
    root, qual, bass = m.group(1), m.group(2), m.group(3)
    if qual not in QUALITIES:
        raise ValueError("unknown chord quality %r in %r; known: %s"
                         % (qual, symbol, sorted(QUALITIES)))
    return pc(root), QUALITIES[qual], (pc(bass) if bass else None)


def chord_pcs(symbol):
    root, ivs, bass = parse_chord(symbol)
    out = {(root + i) % 12 for i in ivs}
    if bass is not None:
        out.add(bass)
    return out


def roman(scale, numeral):
    """Diatonic chord symbol for a roman numeral in a 7-note scale.
    'i7' in G minor -> 'Gm7'; 'III' -> 'Bb'; 'VII' -> 'F'; 'iv9' -> 'Cm9';
    suffixes: 7, 9, add9, sus2, sus4, 7sus4 (sus chords keep the diatonic 7th)."""
    if len(scale.intervals) != 7:
        raise ValueError("roman numerals need a 7-note scale, got %s" % scale.mode)
    m = re.match(r"^([b#]?)([ivIV]+)(.*)$", numeral)
    if not m or m.group(2).lower() not in _ROMAN:
        raise ValueError("bad roman numeral: %r" % numeral)
    shift = {"b": -1, "#": 1, "": 0}[m.group(1)]
    deg = _ROMAN[m.group(2).lower()]
    suffix = m.group(3)
    pcs = scale.pcs
    root = (pcs[deg - 1] + shift) % 12

    def diatonic(k):  # k-th scale tone above the chord's degree, in semitones
        return (pcs[(deg - 1 + k) % 7] - pcs[deg - 1]) % 12

    third, fifth, seventh, ninth = diatonic(2), diatonic(4), diatonic(6), diatonic(1)
    if suffix.startswith("sus"):
        body = {"sus2": "sus2", "sus4": "sus4", "sus": "sus4"}.get(suffix)
        if body is None:
            raise ValueError("unsupported suffix %r" % suffix)
        return NOTE_NAMES[root] + body
    if suffix == "7sus4":
        return NOTE_NAMES[root] + ("7sus4" if seventh == 10 else "sus4")
    if (third, fifth) == (4, 7):
        tri = ""
    elif (third, fifth) == (3, 7):
        tri = "m"
    elif (third, fifth) == (3, 6):
        tri = "dim"
    elif (third, fifth) == (4, 8):
        tri = "aug"
    else:
        raise ValueError("no tertian triad on degree %d of %s" % (deg, scale))
    if suffix == "":
        return NOTE_NAMES[root] + tri
    if suffix in ("7", "9"):
        table = {("", 11): "maj7", ("", 10): "7", ("m", 10): "m7", ("m", 11): "mmaj7",
                 ("dim", 10): "m7b5", ("dim", 9): "dim7"}
        q = table.get((tri, seventh))
        if q is None:
            raise ValueError("no diatonic 7th chord on degree %d" % deg)
        if suffix == "9":
            if ninth != 2:
                raise ValueError("diatonic 9th on degree %d is not a major 9th" % deg)
            q = {"maj7": "maj9", "7": "9", "m7": "m9"}.get(q)
            if q is None:
                raise ValueError("no 9th chord for this degree")
        return NOTE_NAMES[root] + q
    if suffix == "add9":
        return NOTE_NAMES[root] + ("add9" if tri == "" else "madd9")
    raise ValueError("unsupported suffix %r" % suffix)


# ---------------------------------------------------------------------------
# voicing and voice leading
# ---------------------------------------------------------------------------

def _role(i):
    """How much a chord tone (interval above the root) defines the chord's sound.
    0 = third / seventh / sixth, 1 = extensions and sus tones, 2 = root (the bass
    usually covers it), 3 = fifth (the first tone to drop)."""
    if i >= 12 or i in (2, 5):
        return 1
    if i in (3, 4, 9, 10, 11):
        return 0
    if i == 0:
        return 2
    return 3


def _roles(ivs):
    return sorted(ivs, key=lambda i: (_role(i), i))


def chord_tones(symbol, n):
    """Pick n pitch classes for an n-voice voicing, dropping or doubling by role."""
    root, ivs, _ = parse_chord(symbol)
    order = _roles(ivs)
    chosen = order[:n]
    while len(chosen) < n:                       # small chord, more voices: double
        chosen.append(order[len(chosen) % len(order)] + 12)
    return [(root + i) % 12 for i in chosen]


def _candidates(pcs, low, high, max_spread):
    options = [[p for p in range(low, high + 1) if p % 12 == c] for c in pcs]
    seen = set()
    for combo in itertools.product(*options):
        v = tuple(sorted(combo))
        if v in seen or len(set(v)) < len(v):
            continue
        seen.add(v)
        if v[-1] - v[0] > max_spread:
            continue
        ok = True
        for a, b in zip(v, v[1:]):
            # low-interval limits: close intervals turn to mud in the low register
            if a < 48 and b - a < 7:
                ok = False
                break
            if a < 55 and b - a < 3:
                ok = False
                break
        if ok:
            yield v


def _move_cost(a, b):
    cost = sum(abs(x - y) for x, y in zip(a, b))
    top = abs(a[-1] - b[-1])
    if top > 5:
        cost += 2 * (top - 5)     # keep the top line (what the ear follows) smooth
    return cost


def voice_lead(chords, low=55, high=79, voices=4, max_spread=19):
    """Voicings for a progression that minimise total voice movement (Viterbi over all
    candidate voicings). Returns one sorted tuple of MIDI notes per chord."""
    layers = []
    for sym in chords:
        cands = list(_candidates(chord_tones(sym, voices), low, high, max_spread))
        if not cands:
            raise ValueError("no voicing for %s in %d-%d with %d voices"
                             % (sym, low, high, voices))
        layers.append(cands)
    center = (low + high) / 2.0
    best = [{v: (abs(sum(v) / len(v) - center), None) for v in layers[0]}]
    for layer in layers[1:]:
        prev = best[-1]
        cur = {}
        for v in layer:
            cost, arg = min((c + _move_cost(p, v), p) for p, (c, _) in prev.items())
            cur[v] = (cost, arg)
        best.append(cur)
    v = min(best[-1], key=lambda k: best[-1][k][0])
    path = [v]
    for layer in reversed(best[1:]):
        v = layer[v][1]
        path.append(v)
    return list(reversed(path))


def movement(voicings):
    """Total semitones moved between consecutive voicings (a voice-leading score)."""
    return sum(sum(abs(x - y) for x, y in zip(a, b)) for a, b in zip(voicings, voicings[1:]))
