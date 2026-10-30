"""Study a handful of reference tracks (about 5) chosen for the track being made.

The references become a named profile like a genre profile (measured: tempo, key,
loudness, spectrum, structure, fingerprint, timbre, tension; heard: form, entries, drum
steps and swing, bassline, chords, layer balance), so every tool that takes a `genre`
(compare_to_genre, validate_against_genre, analyze_tension, compare_by_ear,
genre_plan_structure, find_samples, groove_loop) also takes the study's name.

The study itself is a brief for the AI: each reference in a few lines, what they share
and why it works, where they disagree (the choices left to the producer), and a section
plan. Five tracks give a direction, not statistics: the brief says so.

Audio stays where the producer keeps it: the study folder holds links, not copies.
"""
import glob
import json
import os
import time

import numpy as np

from . import knowledge, references, tension, timbre
from .storage import DATA_DIR, serialized_analysis

STUDIES_DIR = os.environ.get("ABLETON_CLAUDE_STUDIES",
                             os.path.join(DATA_DIR, "References"))
CACHE_PATH = os.path.normpath(os.path.join(knowledge.KNOWLEDGE_DIR, "..", "cache.json"))
MAX_REFS = 12


def folder_of(name):
    return os.path.join(STUDIES_DIR, references.slug(name))


def collect(name, paths=None, folder=None):
    """Audio files of the study, linked into its folder (which is also an inbox: files the
    producer drops there are studied too). Returns the folder."""
    dest = folder_of(name)
    os.makedirs(dest, exist_ok=True)
    files = list(paths or [])
    if folder:
        files += [p for p in glob.glob(os.path.join(os.path.expanduser(folder), "**", "*"),
                                       recursive=True) if p.lower().endswith(references.AUDIO_EXT)]
    files = [os.path.abspath(os.path.expanduser(p)) for p in files]
    for p in files:
        if not os.path.isfile(p):
            raise FileNotFoundError(p)
        if not p.lower().endswith(references.AUDIO_EXT):
            raise ValueError("not an audio file: %s" % p)
    # refuse before linking: a refused call used to leave every file linked in the inbox,
    # and the next, smaller call was refused for them
    total = len({os.path.basename(p) for p in audio_files(dest)} |
                {os.path.basename(p) for p in files})
    if total > MAX_REFS:
        raise ValueError("%d files: a study is a handful of references (at most %d). For a "
                         "whole genre use scripts/build_profile.py" % (total, MAX_REFS))
    for p in files:
        link = os.path.join(dest, os.path.basename(p))
        if os.path.abspath(link) != p and not os.path.lexists(link):
            os.symlink(p, link)
    found = audio_files(dest)
    if not found:
        raise ValueError("no audio for study %r: pass paths, a folder, or drop files in %s"
                         % (name, dest))
    if len(found) > MAX_REFS:
        raise ValueError("%d files: a study is a handful of references (at most %d). For a "
                         "whole genre use scripts/build_profile.py" % (len(found), MAX_REFS))
    return dest


def audio_files(folder):
    return sorted(p for p in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
                  if os.path.isfile(p) and p.lower().endswith(references.AUDIO_EXT))


def _load_cache():
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_cache(c):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f)
    os.replace(tmp, CACHE_PATH)


def _stats(vals):
    v = np.array([x for x in vals if x is not None], float)
    if not v.size:
        return None
    return {"median": round(float(np.median(v)), 3), "p25": round(float(np.percentile(v, 25)), 3),
            "p75": round(float(np.percentile(v, 75)), 3), "n": int(v.size)}


@serialized_analysis
def run(name, folder, log=print, ear=True, brief_folder=None, kind="reference_set"):
    """Measure and hear every file in `folder`, save the profile under `name`, write the
    study brief next to it. Cached per file: a re-run only does what is new."""
    os.makedirs(knowledge.KNOWLEDGE_DIR, exist_ok=True)
    cache = _load_cache()
    log("measuring (loudness, spectrum, tempo, key, structure)")
    prof, cache = references.build_profile(folder, name, cache=cache, on_track=_save_cache, log=log)
    _save_cache(cache)
    if not prof["n_tracks"]:
        raise ValueError("no reference could be analysed")
    log("fingerprints (groove, harmony, width, movement)")
    refs = references.build_fingerprints(folder, cache, log=log, on_track=_save_cache)
    fkeys = sorted({k for r in refs for k in (r.get("fingerprint") or {})})
    prof["fingerprint"] = {k: s for k in fkeys
                           if (s := _stats([(r.get("fingerprint") or {}).get(k) for r in refs]))}
    log("element timbre (kick, bass, hats, clap, breakdown)")
    trefs = timbre.build_timbre(folder, cache, log=log, on_track=_save_cache)
    prof["timbre"] = timbre.profile_stats(trefs)
    _save_cache(cache)
    prof["tension"] = tension.profile_stats(refs)
    prof["kind"] = kind
    prof["studied"] = time.strftime("%Y-%m-%d %H:%M")

    reports = []
    if ear:
        try:
            from .ear import listen as EL, why
        except ImportError as e:
            log("ear not installed (%s): the study is measured, not heard" % e)
        else:
            for i, p in enumerate(audio_files(folder), 1):
                log("listening %d/%d: %s" % (i, prof["n_tracks"], os.path.basename(p)))
                try:
                    reports.append(EL.listen(p))
                except Exception as e:  # one bad file must not sink the study
                    log("could not hear %s: %s" % (os.path.basename(p), e))
            if reports:
                prof["ear"] = references.analysis._plain(why.principles(reports))
                ear_keys(prof, reports)
    references.save_profile(prof, knowledge.profile_path(name))
    brief = make_brief(name, prof, reports)
    dest = brief_folder or folder
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "study.json"), "w") as f:
        json.dump(brief, f, indent=1)
    log("done")
    return brief


MINORISH = ("m", "m7", "m9", "m11", "m6", "m7b5", "dim")


def tonic_colour(rep):
    """Share of the bars on the tonic chord that are major vs minor: a track that plays
    both (Dm and D) is modal mixture, and the key's mode alone hides it."""
    h = rep.get("harmony") or {}
    tonic = h.get("tonic_pc")
    if tonic is None:
        return None
    from .ear import listen as EL
    maj = mino = 0
    for label in h.get("bars") or []:
        for chord in str(label).split():
            parsed = EL._parse_chord(chord)
            if not parsed or parsed[0] != tonic:
                continue
            q = parsed[1]
            if q in MINORISH:
                mino += 1
            elif not q.startswith("sus") and q != "N":
                maj += 1
    tot = maj + mino
    return {"major": round(maj / tot, 2), "minor": round(mino / tot, 2)} if tot else None


def ear_keys(prof, reports):
    """Take each track's key from the ear where it heard the track. The measured key reads
    the third above the bass from the full mix, where the root's 5th harmonic sits on the
    major third and turns minor tracks major; the ear reads chords from the separated
    harmony stem."""
    by_file = {r["file"]: r for r in reports}
    for t in prof["tracks"]:
        rep = by_file.get(t["file"])
        if not rep or not rep.get("key"):
            continue
        if rep["key"] != t["key"]:
            t["key_measured"] = t["key"]
        t["key"], t["key_source"] = rep["key"], "ear"
        colour = tonic_colour(rep)
        if colour and min(colour.values()) >= 0.25:
            t["tonic_chord"] = colour
    keys = {}
    for t in prof["tracks"]:
        keys[t["key"]] = keys.get(t["key"], 0) + 1
    prof["keys"] = dict(sorted(keys.items(), key=lambda kv: -kv[1]))
    prof["modes"] = {m: sum(1 for t in prof["tracks"] if t["key"].endswith(m))
                     for m in ("minor", "major")}


def _spread(vals):
    """Where the references disagree: (min, max) when the spread is wide."""
    v = [x for x in vals if x is not None]
    return (round(min(v), 2), round(max(v), 2)) if len(v) >= 2 else None


def make_brief(name, prof, reports):
    cards = []
    by_file = {r["file"]: r for r in reports}
    for t in prof["tracks"]:
        st = t["structure"]
        card = {"file": t["file"], "bpm": t["bpm"], "key": t["key"], "lufs": t["lufs"],
                **{k: t[k] for k in ("key_measured", "tonic_chord") if k in t},
                "minutes": round(t["duration_s"] / 60, 1), "bars": st.get("bars"),
                "intro_bars": st.get("intro_bars"), "main_break_bars": st.get("main_break_bars"),
                "main_break_at_pct": (round(100 * st["main_break_at"])
                                      if st.get("main_break_at") is not None else None),
                "swing_pct": t["swing_pct"]}
        rep = by_file.get(t["file"])
        if rep:
            from .ear import listen as EL
            card["heard"] = rep["summary"]
            card["form"] = ["%s %d-%d" % f for f in EL.form(rep["arrangement"]["sections"])]
        cards.append(card)

    shared = []
    disagree = {}
    if prof.get("ear"):
        from .ear import why
        shared = why.explain(prof["ear"])
    for label, vals in (("bpm", [t["bpm"] for t in prof["tracks"]]),
                        ("swing_pct", [t["swing_pct"] for t in prof["tracks"]]),
                        ("lufs", [t["lufs"] for t in prof["tracks"]]),
                        ("main_break_bars", [t["structure"].get("main_break_bars")
                                             for t in prof["tracks"]]),
                        ("intro_bars", [t["structure"].get("intro_bars") for t in prof["tracks"]])):
        s = _spread(vals)
        if s and s[1] - s[0] > {"bpm": 3, "swing_pct": 6, "lufs": 2.5}.get(label, 8):
            disagree[label] = s
    keys = sorted({t["key"] for t in prof["tracks"]})
    if len(keys) > 1:
        disagree["key"] = keys

    try:
        minutes = (prof["duration_s"]["median"] or 360) / 60
        plan = knowledge.plan_structure(name, minutes)
    except Exception as e:
        plan = {"error": str(e)}

    return references.analysis._plain({
        "study": name, "n_references": prof["n_tracks"], "heard": len(reports),
        "caution": ("%d references give a direction, not statistics: treat the medians as "
                    "the centre of this producer's taste for this track, and the "
                    "disagreements as choices to make." % prof["n_tracks"]),
        "use_as_genre": name,
        "references": cards,
        "shared_and_why": shared,
        "where_they_disagree": disagree,
        "centre": {"bpm": prof["bpm"], "swing_pct": prof["swing_pct"], "keys": prof["keys"],
                   "loudness": prof["loudness"], "structure": prof["structure"],
                   "bands_share": prof["bands_share"]},
        "section_plan": plan,
        "next": ["Compare the open project with the study: render it, then "
                 "validate_against_genre(render, '%s') and compare_by_ear(render, '%s')." % (name, name),
                 "Turn what the references share into 3-5 concrete ideas for this track, each "
                 "with PROBLEM / SOLUTION / EXPECTED RESULT (producer_brief), and ask the "
                 "producer which to try before changing the set.",
                 "Borrow feel, not material: extract_groove(reference) gives a reference's "
                 "groove for the Groove Pool; never copy its melodies or samples."],
    })


def load_brief(name):
    p = os.path.join(folder_of(name), "study.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)
