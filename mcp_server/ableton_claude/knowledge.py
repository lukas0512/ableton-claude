"""Genre knowledge: curated conventions plus what the references measure.

CONVENTIONS are the craft rules producers of each style share (tempo, harmony, drums,
bass, arrangement, palette, mix). They are starting points, written down so a generator
can use them explicitly. Measured profiles (references.build_profile) sit beside them;
where both speak, the measurement of the user's own references wins for numbers, and
the conventions still explain *why*.
"""
import json
import os

from . import references

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge", "genres")

CONVENTIONS = {
    "deep_house": {
        "bpm": [118, 125],
        "keys": "mostly minor; Aeolian and Dorian. A hexatonic minor (no 6th) sits under both.",
        "harmony": {
            "chords": "minor 7, minor 9, minor 11, maj7, 7sus4, add9; rarely plain triads",
            "progressions": [["i7", "IV7sus4"], ["i7", "iv7"], ["i7", "III7", "VII", "IV7sus4"],
                             ["i9", "VI7", "III7", "VII"], ["ii7", "V7sus4", "Imaj7"]],
            "voicing": "rootless or open voicings in C3-C5, common tones held; the bass takes "
                       "the root. Chord stabs anticipate the bar on the 'and' of 4.",
        },
        "drums": {"kick": "four on the floor", "clap": "beats 2 and 4, often layered",
                  "hats": "open hat on the off-beat 8ths, 16th shaker",
                  "swing_pct": [54, 60],
                  "percussion": "rims, congas, bongos; ghost notes at low velocity"},
        "bass": "warm sub or Juno-style; pedal on the root or syncopated root-octave-fifth "
                "figures on off-beats, leaving the kick's downbeats clear",
        "arrangement": {"phrase_bars": [8, 16, 32], "intro_bars": [16, 32],
                        "main_break": "one main breakdown of 16-32 bars around 50-65 % in",
                        "outro_bars": [16, 32], "length_min": [6, 8],
                        "moves": ["drop the kick for a bar before a section",
                                  "filter or strip the groove instead of adding layers",
                                  "call and response between two hook parts"]},
        "palette": ["Rhodes / e-piano", "organ or chord stabs", "warm analog pads",
                    "vocal chops and shots", "reverse swells", "noise sweeps"],
        "mix": {"integrated_lufs": [-10, -7], "low_end": "mono below ~120 Hz",
                "top": "softer and warmer than tech house"},
    },
    "tech_house": {
        "bpm": [124, 128],
        "keys": "minor; often a single chord or no chord at all",
        "harmony": {"chords": "sparse; one-note stabs or a single minor chord",
                    "progressions": [["i"], ["i", "VII"]],
                    "voicing": "the bassline carries the harmony"},
        "drums": {"kick": "four on the floor, punchy", "clap": "2 and 4",
                  "hats": "busy 16ths, open hat off-beats, shakers",
                  "swing_pct": [50, 56], "percussion": "toms and percussive loops, rolls"},
        "bass": "rolling 16th-note bass, groove-defining, sidechained to the kick",
        "arrangement": {"phrase_bars": [8, 16, 32], "intro_bars": [16, 32],
                        "main_break": "short breakdown (8-16 bars) with a filtered build",
                        "outro_bars": [16, 32], "length_min": [5.5, 7],
                        "moves": ["vocal hook repeated and chopped", "filter sweeps into drops",
                                  "percussion fills every 8 bars"]},
        "palette": ["vocal chops", "rolling bass", "percussive stabs", "noise risers"],
        "mix": {"integrated_lufs": [-8, -6], "low_end": "mono below ~120 Hz",
                "top": "bright, crisp hats"},
    },
    "minimal_tech": {
        "bpm": [123, 128],
        "keys": "minor or atonal; texture over harmony",
        "harmony": {"chords": "one short stab or none", "progressions": [["i"]],
                    "voicing": "tiny motifs, often a single repeated note"},
        "drums": {"kick": "four on the floor, tight", "clap": "2 and 4 or rim",
                  "hats": "micro-variations, 16ths with small velocity changes",
                  "swing_pct": [52, 58], "percussion": "clicks, shakers, glitches"},
        "bass": "short, dry, syncopated; locks with the kick",
        "arrangement": {"phrase_bars": [16, 32], "intro_bars": [32, 64],
                        "main_break": "often no full breakdown; tension from subtraction",
                        "outro_bars": [32, 64], "length_min": [6, 9],
                        "moves": ["slow evolution: change one element every 16-32 bars"]},
        "palette": ["clicks", "short percussion", "dry bass", "sparse stabs"],
        "mix": {"integrated_lufs": [-10, -8], "low_end": "tight and mono",
                "top": "detailed, not harsh"},
    },
    "uk_garage": {
        "bpm": [130, 136],
        "keys": "minor, R&B-influenced",
        "harmony": {"chords": "minor 7 and 9 organ or piano stabs",
                    "progressions": [["i7", "iv7"], ["i9", "VI7", "VII"]],
                    "voicing": "stabs on the off-beat, syncopated"},
        "drums": {"kick": "2-step: beat 1 and a skipped kick before 3, not four on the floor",
                  "clap": "2 and 4", "hats": "shuffled 16ths",
                  "swing_pct": [60, 66], "percussion": "rimshots, shuffled shakers"},
        "bass": "sub or warp bass with syncopated slides",
        "arrangement": {"phrase_bars": [8, 16], "intro_bars": [16, 32],
                        "main_break": "breakdown of 8-16 bars, often vocal-led",
                        "outro_bars": [16, 32], "length_min": [4.5, 6.5],
                        "moves": ["pitched and chopped vocal hooks", "drop the kick for fills"]},
        "palette": ["organ stabs", "chopped R&B vocals", "warp bass", "shuffled hats"],
        "mix": {"integrated_lufs": [-9, -7], "low_end": "heavy sub, mono",
                "top": "crisp shuffled hats"},
    },
    "soulful_house": {
        "bpm": [120, 124],
        "keys": "major or minor with jazz and gospel harmony",
        "harmony": {"chords": "maj7, min9, 9sus4, 13; passing chords",
                    "progressions": [["ii7", "V7", "Imaj7"], ["IVmaj7", "iii7", "vi7"],
                                     ["Imaj7", "vi7", "ii7", "V7sus4"]],
                    "voicing": "piano voicings with extensions, gospel movement"},
        "drums": {"kick": "four on the floor", "clap": "2 and 4",
                  "hats": "live-feel hats, off-beat open hat", "swing_pct": [54, 60],
                  "percussion": "congas, tambourine"},
        "bass": "melodic, walking or syncopated, often live",
        "arrangement": {"phrase_bars": [8, 16, 32], "intro_bars": [16, 32],
                        "main_break": "piano- or vocal-led breakdown", "outro_bars": [16, 32],
                        "length_min": [6, 8],
                        "moves": ["vocal call and response", "key lift for the last chorus"]},
        "palette": ["piano", "strings", "organ", "live bass", "vocals"],
        "mix": {"integrated_lufs": [-10, -8], "low_end": "full but controlled",
                "top": "open and airy"},
    },
    "disco_house": {
        "bpm": [118, 125],
        "keys": "major common, minor for darker cuts",
        "harmony": {"chords": "disco loops: maj7, 7, min7; filtered samples",
                    "progressions": [["I", "vi", "ii", "V"], ["i7", "iv7"],
                                     ["IVmaj7", "V", "iii7", "vi7"]],
                    "voicing": "strings and guitar chops"},
        "drums": {"kick": "four on the floor", "clap": "2 and 4",
                  "hats": "open hat on off-beats (the disco 'tss')", "swing_pct": [52, 58],
                  "percussion": "tambourine, congas"},
        "bass": "octave-bouncing 8ths",
        "arrangement": {"phrase_bars": [8, 16, 32], "intro_bars": [16, 32],
                        "main_break": "filtered breakdown, loop drops out", "outro_bars": [16, 32],
                        "length_min": [5.5, 7.5],
                        "moves": ["filter sweeps on the loop", "strings as the hook"]},
        "palette": ["disco strings", "funk guitar", "octave bass", "filtered samples"],
        "mix": {"integrated_lufs": [-9, -7], "low_end": "punchy", "top": "bright"},
    },
}

ALIASES = {"deep house": "deep_house", "tech house": "tech_house", "minimal": "minimal_tech",
           "minimal tech": "minimal_tech", "real deep tech": "minimal_tech", "ukg": "uk_garage",
           "garage": "uk_garage", "soulful": "soulful_house", "disco": "disco_house",
           "disco bangs": "disco_house", "nu disco": "disco_house"}


def key_of(genre):
    g = genre.strip().lower()
    return ALIASES.get(g, references.slug(g))


def profile_path(genre):
    return os.path.join(KNOWLEDGE_DIR, "%s.profile.json" % key_of(genre))


def load_profile(genre):
    p = profile_path(genre)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def get(genre):
    k = key_of(genre)
    prof = load_profile(genre)
    out = {"genre": k, "conventions": CONVENTIONS.get(k)}
    if prof:
        out["measured"] = {kk: prof[kk] for kk in ("n_tracks", "bpm", "swing_pct", "keys",
                                                    "modes", "duration_s", "loudness",
                                                    "bands_share", "tilt", "structure")}
    if not out["conventions"] and not prof:
        out["note"] = ("no conventions or profile for %r yet; build one with "
                       "reference_profile_build from a folder of references" % genre)
    return out


def plan_structure(genre, minutes, bpm=None):
    """Section plan for a new track, from the measured profile where there is one and the
    conventions otherwise. Lengths snap to 8 bars."""
    k = key_of(genre)
    conv = CONVENTIONS.get(k, {})
    prof = load_profile(genre)
    bpm = bpm or (prof["bpm"]["median"] if prof else sum(conv.get("bpm", [124, 124])) / 2)
    total = int(round(minutes * bpm / 4.0 / 8.0)) * 8
    snap = lambda v: max(8, int(round(v / 8.0)) * 8)
    st = prof["structure"] if prof else {}
    arr = conv.get("arrangement", {})
    intro = snap(st["intro_bars"]["median"]) if st.get("intro_bars") else arr.get("intro_bars", [16])[0]
    outro = snap(st["outro_bars"]["median"]) if st.get("outro_bars") else arr.get("outro_bars", [16])[0]
    brk = snap(st["main_break_bars"]["median"]) if st.get("main_break_bars") else 16
    at = st["main_break_at"]["median"] if st.get("main_break_at") else 0.55
    build = 8
    brk_start = snap(total * at)
    body1 = brk_start - intro
    drop = total - outro - (brk_start + brk + build)
    plan = [("Intro", intro), ("Groove", body1), ("Breakdown", brk), ("Build", build),
            ("Drop", drop), ("Outro", outro)]
    if body1 < 16 or drop < 16:
        raise ValueError("%s minutes is too short for this genre's structure" % minutes)
    bar = 1
    out = []
    for name, n in plan:
        out.append({"name": name, "start_bar": bar, "bars": n})
        bar += n
    return {"genre": k, "bpm": bpm, "total_bars": total, "sections": out,
            "source": "measured profile" if prof else "conventions"}
