"""Everything we measure about a render, against a genre's references, in one report.

Sections: structure (intro, main break, outro, duration), loudness and band balance,
groove/harmony/timbre fingerprint, element timbre (kick, bass, hats, clap, breakdown)
and tension/release around the main break. Every measure gets the references' middle
half and a verdict; the summary counts what sits inside it.
"""
import json

from . import knowledge, references, tension, timbre


def verdict(v, p):
    if v is None or not p or p.get("p25") is None:
        return None
    return "ok" if p["p25"] <= v <= p["p75"] else ("low" if v < p["p25"] else "high")


def rows_for(ours, prof, keys=None):
    out = {}
    for k in (keys or ours.keys()):
        v, p = ours.get(k), prof.get(k)
        if v is None or not p:
            continue
        out[k] = {"ours": v, "p25": p["p25"], "median": p["median"], "p75": p["p75"],
                  "verdict": verdict(v, p)}
    return out


def report(src, genre="deep house", out=None, echo=print):
    bpm = None
    if src.endswith(".json"):
        d = json.load(open(src))
        src, bpm = d["file"], d.get("render", {}).get("tempo")
    prof = knowledge.load_profile(genre)
    a = references.analyze_reference(src, bpm=bpm)
    x, sr = references.load_audio(src)
    report = {"file": src, "bpm": a["bpm"], "first_beat_s": a["first_beat_s"], "key": a["key"],
              "segments": a["segments"]}

    st = a["structure"]
    st["duration_s"] = a["duration_s"]
    sp = dict(prof["structure"])
    sp["duration_s"] = prof["duration_s"]
    report["structure"] = rows_for(st, sp, ["intro_bars", "main_break_bars", "main_break_at",
                                            "break_depth_lu", "outro_bars", "duration_s"])
    lo = {"integrated_lufs": a["loudness"]["integrated_lufs"], "crest_db": a["loudness"]["crest_db"],
          "true_peak_dbtp": a["loudness"]["true_peak_dbtp"]}
    report["loudness"] = rows_for(lo, prof["loudness"])
    report["bands"] = rows_for(a["bands_share"], prof["bands_share"])
    fp = references.fingerprint(x, sr, a["bpm"], a["first_beat_s"], a["segments"])
    report["fingerprint"] = rows_for(fp, prof["fingerprint"])
    tim = timbre.element_timbre(x, sr, a["bpm"], a["first_beat_s"], a["segments"], a["bars_matrix"])
    report["timbre"] = rows_for(tim, prof.get("timbre", {}))
    ten = tension.for_track(a["bars_matrix"], a["segments"]) or {}
    report["tension"] = rows_for(ten, prof.get("tension", {}), list(tension.KEYS))
    report["tension_where"] = {"break_bars": ten.get("break_bars"), "drop_bar": ten.get("drop_bar")}

    n_ok = n_all = 0
    for sec in ("structure", "loudness", "bands", "fingerprint", "timbre", "tension"):
        rows = report[sec]
        ok = sum(1 for r in rows.values() if r["verdict"] == "ok")
        n_ok, n_all = n_ok + ok, n_all + len(rows)
        echo("\n%s  (%d/%d inside the references' middle half)" % (sec.upper(), ok, len(rows)))
        for k, r in rows.items():
            mark = "" if r["verdict"] == "ok" else r["verdict"].upper()
            echo("  %-28s %9s   refs %9s .. %-9s (median %s)  %s" % (k, r["ours"], r["p25"], r["p75"],
                                                                 r["median"], mark))
    report["summary"] = {"inside": n_ok, "measured": n_all}
    echo("\n%d of %d measures inside the references' middle half" % (n_ok, n_all))
    if out:
        json.dump(report, open(out, "w"), indent=1, default=float)
    return report

