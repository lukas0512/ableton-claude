"""Section-level production evidence, not an emotion recogniser or quality score.

Keep bass amount, harmonic openness, stereo loss and rhythmic occupancy independent.
Compare transitions locally: an equal-loudness drop can still restore low end/pulse.
"""
import numpy as np
from scipy import signal

VERSION = 1
METRICS = {
    "bass_vs_drums_db": "bass/drums stereo RMS ratio; amount, not brightness",
    "bass_upper_to_low_db": "bass 180-2000 Hz over 25-180 Hz; spectral openness proxy, not filter cutoff",
    "bass_low_mono_loss_db": "bass 25-180 Hz mono/stereo power; negative means energy lost on mono sum",
    "mix_low_share_pct": "mix power share in 25-180 Hz within 25-8000 Hz",
    "bass_notes_per_bar": "transcribed bass note count in this bar",
    "bass_occupancy_pct": "union of transcribed bass note durations within the bar",
    "drum_attack_to_tail_db": "median beat 0-80 ms / 80-250 ms drum power; transient proxy, not perceived punch",
}
TRANSITION_KEYS = ("loudness_jump_lu", "bass_return_db", "drums_return_db",
                   "low_share_change_pct", "bass_openness_change_db", "predrop_dip_lu")


def _median(values):
    v = [float(x) for x in values if x is not None and np.isfinite(x)]
    return round(float(np.median(v)), 3) if v else None


def _ratio(a, b):
    if a is None or b is None or a < 1e-16 or b < 1e-16:
        return None
    return round(float(10 * np.log10(a / b)), 3)


def _power(x):
    return float(np.mean(np.asarray(x, dtype=float) ** 2)) if len(x) else 0.


def _spectrum(x, sr):
    if len(x) < 32:
        return None
    f, p = signal.welch(x, fs=sr, nperseg=min(8192, len(x)), axis=0)
    if p.ndim == 2:
        p = p.mean(axis=1)  # Do not cancel antiphase before measuring stereo energy.
    return f, p


def _band(spec, lo, hi):
    if spec is None:
        return None
    f, p = spec
    return float(p[(f >= lo) & (f < hi)].sum())


def _mono_loss(stereo, sr, stereo_spec):
    total = _band(stereo_spec, 25, 180)
    if total is None or total < 1e-16:
        return None
    mid = stereo.mean(axis=1) if stereo.ndim == 2 else stereo
    mono = _band(_spectrum(mid, sr), 25, 180)
    return round(float(10 * np.log10(max(mono, total * 1e-12) / total)), 3)


def _occupancy(intervals):
    intervals = sorted(intervals)
    occupied, end = 0., 0.
    for a, b in intervals:
        occupied += max(0., b - max(a, end))
        end = max(end, b)
    return round(100 * occupied / 16, 2)


def _attack_tail(x, sr, period):
    ratios = []
    for beat in range(4):
        a = int(beat * period * sr)
        split = a + int(min(.08, period * .2) * sr)
        end = a + int(min(.25, period * .7) * sr)
        if end <= len(x):
            ratios.append(_ratio(_power(x[a:split]), _power(x[split:end])))
    return _median(ratios)


def analyze(x, sr, stems, g, arrangement, bass_notes=()):
    """All bars in one forward pass; no separation/model calls, no audio copies to disk."""
    if sr < 4000 or not np.isfinite(g["period"]) or g["period"] <= 0:
        raise ValueError("perception requires sr >= 4000 and a finite positive beat period")
    bass, drums = stems["bass"], stems["drums"]
    ranges = [(max(0, int((g["first_downbeat"] + bar * 4 * g["period"]) * sr)),
               min(len(x), int((g["first_downbeat"] + (bar + 1) * 4 * g["period"]) * sr)))
              for bar in range(g["n_bars"])]
    # Do not call separation residue in a bass-free break an open/closed bass timbre.
    bass_floor = max(1e-16, max((_power(bass[a:b]) for a, b in ranges), default=0.) * 1e-3)
    drum_floor = max(1e-16, max((_power(drums[a:b]) for a, b in ranges), default=0.) * 1e-3)
    notes_by_bar, gates_by_bar = {}, {}
    for note in bass_notes:
        notes_by_bar.setdefault(note["bar"], []).append(note)
        start = note["bar"] * 16 + note["step"] + note.get("offset_ms", 0) / 1000 / (g["period"] / 4)
        end = start + note["dur_steps"]
        # Count sustained tails in following bars, union overlaps instead of adding them.
        for bar in range(max(0, int(np.floor(start / 16))), min(g["n_bars"], int(np.ceil(end / 16)))):
            gates_by_bar.setdefault(bar, []).append((max(0., start - bar * 16), min(16., end - bar * 16)))
    rows = []
    for bar, (a, b) in enumerate(ranges):
        if b <= a:
            break
        bs, ds, mix = bass[a:b], drums[a:b], x[a:b]
        ps = _spectrum(bs, sr)
        ms = _spectrum(mix, sr)
        low, upper = _band(ps, 25, 180), _band(ps, 180, 2000)
        total = _band(ms, 25, 8000)
        bp, dp = _power(bs), _power(ds)
        row = {"bar": bar + 1,
               "bass_usable": bool(bp >= bass_floor),
               "bass_level_db": round(10 * np.log10(bp), 3) if bp > 1e-16 else None,
               "drums_level_db": round(10 * np.log10(dp), 3) if dp > 1e-16 else None,
               "bass_vs_drums_db": _ratio(bp, dp) if bp >= bass_floor and dp >= drum_floor else None,
               "bass_upper_to_low_db": round(float(10 * np.log10(max(upper, low * 1e-12) / low)), 3)
                                        if bp >= bass_floor and low is not None and low > 1e-16 and upper is not None else None,
               "bass_low_mono_loss_db": _mono_loss(bs, sr, ps) if bp >= bass_floor else None,
               "mix_low_share_pct": round(100 * _band(ms, 25, 180) / total, 3) if total and total > 1e-16 else None,
               "bass_notes_per_bar": len(notes_by_bar.get(bar, [])),
               "bass_occupancy_pct": _occupancy(gates_by_bar.get(bar, [])),
               "drum_attack_to_tail_db": _attack_tail(ds, sr, g["period"]) if dp >= drum_floor else None,
               "lufs": arrangement.get("bar_lufs", [])[bar] if bar < len(arrangement.get("bar_lufs", [])) else None}
        rows.append(row)
    sections = []
    for section in arrangement["sections"]:
        selected = rows[section["start_bar"] - 1:section["end_bar"]]
        if not selected:
            continue
        sections.append({"label": section["label"], "start_bar": section["start_bar"],
                         "end_bar": min(section["end_bar"], len(rows)), "elements": section["elements"],
                         "metrics": {k: _median([r[k] for r in selected]) for k in METRICS}})
    return {"version": VERSION, "sections": sections, "activity_floor_db_below_stem_peak_bar": -30,
            "transitions": transitions(rows, arrangement["sections"]),
            "bars": rows, "definitions": METRICS,
            "limits": ["Stem separation bleed and transcription errors affect these proxies.",
                       "Openness is harmonic balance, not a measured synth filter setting or stereo width.",
                       "Emotion, taste and professional quality require contextual listening; no scalar score is inferred."]}


def transitions(rows, sections):
    out = []
    for i, section in enumerate(sections):
        if section["label"] != "drop" or i == 0:
            continue
        drop = section["start_bar"] - 1
        if drop < 1 or drop >= len(rows):
            continue
        # Compare up to four actual bars on either side, never wrap negative slices.
        before = rows[max(0, sections[i - 1]["start_bar"] - 1, drop - 4):drop]
        after = rows[drop:min(section["end_bar"], drop + 4, len(rows))]
        if not after:
            continue
        def delta(key):
            a, b = _median([r[key] for r in after]), _median([r[key] for r in before])
            return round(a - b, 3) if a is not None and b is not None else None
        old = _median([r["lufs"] for r in rows[max(0, drop - 5):drop - 1]])
        last = rows[drop - 1]["lufs"]
        previous = set(sections[i - 1]["elements"])
        current = set(section["elements"])
        out.append({"drop_bar": drop + 1, "before_bars": [before[0]["bar"], before[-1]["bar"]],
                    "after_bars": [after[0]["bar"], after[-1]["bar"]],
                    "loudness_jump_lu": delta("lufs"), "bass_return_db": delta("bass_level_db"),
                    "drums_return_db": delta("drums_level_db"),
                    "low_share_change_pct": delta("mix_low_share_pct"),
                    "bass_openness_change_db": delta("bass_upper_to_low_db"),
                    "predrop_dip_lu": round(last - old, 3) if old is not None and last is not None else None,
                    "entering": sorted(current - previous), "leaving": sorted(previous - current),
                    "drum_attack_to_tail_db": _median([r["drum_attack_to_tail_db"] for r in after]),
                    "interpretation": "Independent contrast cues; no requirement that the drop be louder."})
    return out


def _stats(values):
    v = [float(x) for x in values if x is not None and np.isfinite(x)]
    if not v:
        return None
    return {"median": round(float(np.median(v)), 3), "p25": round(float(np.percentile(v, 25)), 3),
            "p75": round(float(np.percentile(v, 75)), 3), "n": len(v)}


def profile(reports):
    """Pool track medians by section role, giving each reference one vote per metric."""
    compatible = [r["perception"] for r in reports if (r.get("perception") or {}).get("version") == VERSION]
    labels = sorted({s["label"] for p in compatible for s in p["sections"]})
    sections = {}
    for label in labels:
        sections[label] = {}
        for key in METRICS:
            votes = [_median([s["metrics"].get(key) for s in p["sections"] if s["label"] == label]) for p in compatible]
            stats = _stats(votes)
            if stats:
                sections[label][key] = stats
    return {"version": VERSION, "n_tracks": len(compatible), "sections": sections,
            "transitions": {k: stats for k in TRANSITION_KEYS
                            if (stats := _stats([_median([t.get(k) for t in p["transitions"]]) for p in compatible]))},
            "meaning": "Reference distributions, not good/bad or emotion thresholds."}


def compare(ours, targets):
    """Keep section-local evidence; don't turn uncommon creative choices into defects."""
    if targets.get("version") != VERSION:
        return {"rows": [], "note": "No compatible perceptual reference profile; retrain references."}
    rows = []
    for section in ours["sections"]:
        target = targets.get("sections", {}).get(section["label"], {})
        for key, value in section["metrics"].items():
            t = target.get(key)
            if value is None or not t:
                continue
            rows.append({"section": section["label"], "bars": [section["start_bar"], section["end_bar"]],
                         "metric": key, "ours": value, "reference": t,
                         "position": "below" if value < t["p25"] else "above" if value > t["p75"] else "within"})
    for transition in ours.get("transitions", []):
        for key in TRANSITION_KEYS:
            value, t = transition.get(key), targets.get("transitions", {}).get(key)
            if value is not None and t:
                rows.append({"section": "transition", "bars": [transition["drop_bar"], transition["drop_bar"]],
                             "metric": key, "ours": value, "reference": t,
                             "position": "below" if value < t["p25"] else "above" if value > t["p75"] else "within"})
    return {"rows": rows, "note": "Outside the middle half is a difference, not a defect; check intention and audition."}
