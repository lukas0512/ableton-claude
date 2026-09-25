"""Why the references sound the way they do.

The ear reports of a genre's references are pooled into habits: where the kick, clap and
hats sit in the bar and how the hats swing, how the bass dodges the kick and which
degrees it leans on, how often chords change, what a break keeps, when each element
enters, and how loud each layer sits against the drums. Each habit comes with how widely
the references share it and the musical reason it works, so "this is how deep house is
made" becomes numbers a producer (or Claude) can argue with and apply.
"""
import collections
import glob
import json
import os

import numpy as np

from . import listen as L

ROLES = ("kick", "clap", "hats")


def load_reports(ids=None):
    out = []
    for p in sorted(glob.glob(os.path.join(L.CACHE_DIR, "*", "report.json"))):
        r = json.load(open(p))
        if ids is None or r["id"] in ids:
            out.append(r)
    return out


def _stats(vals):
    v = np.array([x for x in vals if x is not None], float)
    if not v.size:
        return None
    return {"median": round(float(np.median(v)), 2), "p25": round(float(np.percentile(v, 25)), 2),
            "p75": round(float(np.percentile(v, 75)), 2), "n": int(v.size)}


def principles(reports):
    n = len(reports)
    P = {"n_tracks": n}
    P["bpm"] = _stats([r["grid"]["bpm"] for r in reports])
    modes = collections.Counter((r["key"] or "? ?").split()[1] for r in reports)
    P["minor_share"] = round(modes.get("minor", 0) / max(1, n), 2)

    # form
    P["enter_bar"] = {e: _stats([r["arrangement"]["first_bar"].get(e) for r in reports])
                      for e in ("bass", "other", "vocals", "clap", "hats")}
    P["has_vocals"] = round(np.mean([bool(r["arrangement"]["first_bar"].get("vocals")) for r in reports]), 2)
    brk_keep = collections.Counter()
    n_breaks, main_len, main_pos = 0, [], []
    for r in reports:
        secs = r["arrangement"]["sections"]
        bars = r["grid"]["n_bars"]
        form = L.form(secs)
        brks = [f for f in form if f[0] == "break"]
        if brks:
            longest = max(brks, key=lambda f: f[2] - f[1])
            main_len.append(longest[2] - longest[1] + 1)
            main_pos.append((longest[1] - 1) / bars)
        for s in secs:
            if s["label"] == "break":
                n_breaks += 1
                for e in s["elements"]:
                    brk_keep[e] += 1
    P["break_keeps"] = {e: round(brk_keep[e] / max(1, n_breaks), 2) for e in
                        ("kick", "clap", "hats", "bass", "other", "vocals")}
    P["main_break_bars"] = _stats(main_len)
    P["main_break_at"] = _stats(main_pos)

    # drums: per-step presence averaged over tracks
    P["drums"] = {}
    for role in ROLES:
        profs = [r["drums"]["main_patterns"][role]["step_share"] for r in reports
                 if role in r["drums"].get("main_patterns", {})]
        if not profs:
            continue
        mean = np.mean(np.array(profs), axis=0)
        typical = "".join("x" if v >= 0.5 else ("g" if v >= 0.25 else ".") for v in mean)
        P["drums"][role] = {"typical": typical, "step_presence": [round(float(v), 2) for v in mean],
                            "n": len(profs), "template": groove_template(reports, role)}
    kicks = [r["drums"]["main_patterns"].get("kick", {}).get("step_share") for r in reports]
    P["four_on_floor_share"] = round(np.mean([bool(k) and min(k[0], k[4], k[8], k[12]) >= 0.5 for k in kicks]), 2)
    claps = [r["drums"]["main_patterns"].get("clap", {}).get("step_share") for r in reports]
    P["backbeat_share"] = round(np.mean([bool(c) and min(c[4], c[12]) >= 0.5 for c in claps]), 2)
    P["hat_swing_pct"] = _stats([r["drums"]["hats"].get("swing_pct") for r in reports])
    P["hat_timing_spread_ms"] = _stats([r["drums"]["hats"].get("timing_spread_ms") for r in reports])

    # bass
    B = [r["bass"] for r in reports if r["bass"].get("notes_per_bar")]
    P["bass"] = {k: _stats([b.get(k) for b in B]) for k in
                 ("notes_per_bar", "offbeat_share", "with_kick_share", "median_len_steps", "long_share")}
    deg = collections.defaultdict(list)
    for b in B:
        for d, v in (b.get("degrees") or {}).items():
            deg[d].append(v)
    P["bass"]["degrees"] = {d: round(float(np.sum(v)) / max(1, len(B)), 2)
                            for d, v in sorted(deg.items(), key=lambda kv: -np.sum(kv[1]))}
    rh = collections.Counter()
    for b in B:
        for r_, c in b.get("common_rhythms", [])[:3]:
            rh[r_] += 1
    P["bass"]["rhythms"] = rh.most_common(10)

    # harmony
    H = [r["harmony"] for r in reports]
    P["harmony"] = {"changes_per_8_bars": _stats([h.get("changes_per_8_bars") for h in H])}
    q = collections.Counter()
    for h in H:
        for k, v in (h.get("qualities") or {}).items():
            q[k] += v
    tot = sum(q.values()) or 1
    P["harmony"]["qualities"] = {k: round(v / tot, 2) for k, v in q.most_common(8)}
    cyc = collections.Counter()
    for h in H:
        if h.get("tonic_pc") is None:
            continue
        for c, _ in (h.get("loops") or [])[:2]:
            cyc[L.roman_cycle(c, h["tonic_pc"], h["mode"])] += 1
    P["harmony"]["cycles"] = cyc.most_common(10)

    # mix
    P["mix"] = {}
    for stem in ("bass", "other", "vocals"):
        P["mix"][stem + "_vs_drums_db"] = _stats([r["mix"].get(stem, {}).get("vs_drums_db") for r in reports])
        P["mix"][stem + "_width_db"] = _stats([r["mix"].get(stem, {}).get("width_db") for r in reports])
    P["why"] = explain(P)
    return P


def groove_template(reports, role="hats"):
    """The references' shared feel for one drum, per 16th step: the median over tracks of
    each track's own template (offset against its own on-beats, accent against its strong
    hits, timing variation). A step fewer than half the tracks play stays None."""
    offs, accs, spr = ([[] for _ in range(16)] for _ in range(3))
    n = 0
    for r in reports:
        t = r["drums"].get(role, {}).get("template")
        if not t or len(t) != 16:
            continue
        n += 1
        for s in t:
            if s.get("offset_ms") is None:
                continue
            offs[s["step"]].append(s["offset_ms"])
            accs[s["step"]].append(s["accent_db"])
            if s.get("spread_ms") is not None:
                spr[s["step"]].append(s["spread_ms"])
    steps = []
    for i in range(16):
        used = len(offs[i]) >= max(1, n / 2.0)
        med = lambda v: round(float(np.median(v)), 1) if used and v else None
        steps.append({"step": i, "offset_ms": med(offs[i]), "accent_db": med(accs[i]),
                      "spread_ms": med(spr[i]), "share": round(len(offs[i]) / max(1, n), 2)})
    return {"n": n, "steps": steps}


def _pct(x):
    return "%d%%" % round(100 * x)


def explain(P):
    """The habits in words, each with why it works."""
    w = []
    b = P["bass"]
    if b.get("with_kick_share") and b.get("offbeat_share"):
        w.append("Kick and bass take turns. The median reference plays %s of its bass notes off the beat and only %s "
                 "together with the kick, so each owns its moment in the low end: the sub stays clean and the "
                 "groove bounces between them." % (_pct(b["offbeat_share"]["median"]), _pct(b["with_kick_share"]["median"])))
    if b.get("degrees"):
        top = list(b["degrees"].items())[:4]
        w.append("Basslines lean on the root: degrees %s. Staying on 1 and 5 keeps the low end stable under "
                 "harmony that can drift above it." % ", ".join("%s %s" % (d, _pct(v)) for d, v in top))
    d = P["drums"]
    if d.get("kick"):
        w.append("The kick is four on the floor in %s of the references (typical %s): the constant pulse that "
                 "lets everything else be syncopated." % (_pct(P["four_on_floor_share"]), d["kick"]["typical"]))
    if d.get("clap"):
        w.append("Clap/snare on 2 and 4 in %s of them (typical mid-percussion %s): the backbeat marks the bar "
                 "for dancers." % (_pct(P["backbeat_share"]), d["clap"]["typical"]))
    sw = P.get("hat_swing_pct")
    if sw:
        w.append("Hats swing: median %.0f%% (middle half %.0f-%.0f%%), timing spread %.0f ms. Late off-beat 16ths "
                 "are what make a straight 4/4 feel played rather than programmed."
                 % (sw["median"], sw["p25"], sw["p75"], (P.get("hat_timing_spread_ms") or {}).get("median", 0)))
    h = P["harmony"]
    if h.get("changes_per_8_bars"):
        w.append("Harmony is patient: %.1f chord changes per 8 bars (median), mostly %s. Rich but slow chords "
                 "colour the groove without pulling focus from it."
                 % (h["changes_per_8_bars"]["median"], ", ".join(list(h["qualities"])[:4])))
    bk = P["break_keeps"]
    if bk:
        w.append("Breaks work by subtraction: the kick stays in %s of breaks, the bass in %s, chords/pads in %s, "
                 "vocals in %s. Taking the pulse away builds the tension the drop releases."
                 % (_pct(bk["kick"]), _pct(bk["bass"]), _pct(bk["other"]), _pct(bk["vocals"])))
    eb = P["enter_bar"]
    if eb.get("bass"):
        w.append("The track unfolds slowly: bass enters at bar %d, chords/stabs at bar %s (medians). DJs need "
                 "those drum bars to mix in, and each entry is an event."
                 % (eb["bass"]["median"], int(eb["other"]["median"]) if eb.get("other") else "?"))
    mx = P["mix"]
    if mx.get("other_vs_drums_db") and mx.get("bass_vs_drums_db"):
        w.append("Balance: bass %.0f dB, chords/stabs %.0f dB and vocals %s dB against the drums (medians). "
                 "The drums lead; harmony colours from behind."
                 % (mx["bass_vs_drums_db"]["median"], mx["other_vs_drums_db"]["median"],
                    "%.0f" % mx["vocals_vs_drums_db"]["median"] if mx.get("vocals_vs_drums_db") else "?"))
    return w


def compare(rep, P):
    """Where a track leaves the references' middle half, in words, with the move to make."""
    out = []

    def chk(name, v, s, unit, advice_low, advice_high):
        if v is None or not s:
            return
        if v < s["p25"]:
            out.append("%s %.1f%s is below the references (%.1f-%.1f%s): %s" % (name, v, unit, s["p25"], s["p75"], unit, advice_low))
        elif v > s["p75"]:
            out.append("%s %.1f%s is above the references (%.1f-%.1f%s): %s" % (name, v, unit, s["p25"], s["p75"], unit, advice_high))
    b = rep["bass"]
    chk("Bass notes with the kick", 100 * (b.get("with_kick_share") or 0), _scale(P["bass"].get("with_kick_share")), "%",
        "fine: the bass already avoids the kick.", "move bass notes off the kick or sidechain harder.")
    chk("Bass notes per bar", b.get("notes_per_bar"), P["bass"].get("notes_per_bar"), "",
        "a busier line adds drive.", "fewer notes give the kick room.")
    chk("Hat swing", rep["drums"]["hats"].get("swing_pct"), P.get("hat_swing_pct"), "%",
        "swing the hats more (groove pool or MIDI).", "straighten the hats a little.")
    chk("Chord changes per 8 bars", rep["harmony"].get("changes_per_8_bars"),
        P["harmony"].get("changes_per_8_bars"), "", "a second chord adds motion.", "hold chords longer.")
    for stem, label in (("other", "Chords/stabs"), ("vocals", "Vocals"), ("bass", "Bass")):
        chk("%s vs drums" % label, rep["mix"].get(stem, {}).get("vs_drums_db"),
            P["mix"].get(stem + "_vs_drums_db"), " dB", "raise it.", "lower it.")
    mb = max([f[2] - f[1] + 1 for f in L.form(rep["arrangement"]["sections"]) if f[0] == "break"] or [None], key=lambda v: v or 0)
    chk("Main break", mb, P.get("main_break_bars"), " bars", "a longer break builds more tension.", "shorten the break.")
    mp = rep["drums"].get("main_patterns", {})
    for role in ROLES:
        typ = P["drums"].get(role, {}).get("typical")
        ours = mp.get(role, {}).get("pattern")
        if typ and ours:
            # only clear cases: a step most references play that we leave empty, or a step
            # they rarely play that we play strongly (ghost notes on either side are noise)
            missing = [i + 1 for i in range(16) if typ[i] == "x" and ours[i] == "."]
            extra = [i + 1 for i in range(16) if typ[i] == "." and ours[i] in "Xx"]
            if missing or extra:
                out.append("%s pattern %s vs typical %s:%s%s" % (
                    role, ours, typ, (" steps %s usually played" % missing) if missing else "",
                    (" steps %s usually empty" % extra) if extra else ""))
    return out


def _scale(s):
    if not s:
        return None
    return {k: (v * 100 if k in ("median", "p25", "p75") else v) for k, v in s.items()}
