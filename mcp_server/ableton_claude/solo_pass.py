"""The solo measurement pass: each element rendered soloed over the same bars with the
master limiter off, its integrated loudness against the soloed kick and its 1/3-octave
spectrum, and a masking report (who fights whom, band by band).

The producer's rule: "the kick always loudest, everything else guided by the kick's
level". From The Streets set its faders from these numbers (LEVELS_VS_KICK in
scripts/build_from_the_streets.py), and the spectra found the kick's box masking the bass
at 250-630 Hz. Renders are real time: ~(bars x 4 x 60 / tempo + 4) s per element.
"""
import time

import numpy as np
import soundfile as sf
from scipy import signal

THIRD_OCTAVES = [31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
                 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500,
                 16000]
MASK_DB = 6.0          # elements within this of a band's loudest element mask each other
FLOOR_DB = 30.0        # bands more than this under the loudest band anywhere are ignored
PREFIX = "lvl"         # render tracks: quality_gate flags any left behind
POLL_S = 2.0           # record_status polling while a render runs


def third_octave_abs_db(mono, sr):
    """Absolute band power (dB) per 1/3 octave: comparable between elements rendered alike."""
    f, p = signal.welch(mono, sr, nperseg=16384)
    return [float(10 * np.log10(p[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-20))
            for c in THIRD_OCTAVES]


def measure(path):
    """(integrated LUFS, sample peak dBFS, 1/3-octave dB) of a rendered WAV."""
    import pyloudnorm as pyln
    x, sr = sf.read(path, dtype="float64")
    lufs = float(pyln.Meter(sr).integrated_loudness(x))
    peak = float(20 * np.log10(np.abs(x).max() + 1e-9))
    mono = x.mean(axis=1) if x.ndim == 2 else x
    return lufs, peak, third_octave_abs_db(mono, sr)


def masking(spectra, mask_db=MASK_DB, floor_db=FLOOR_DB):
    """Per 1/3-octave band: the loudest element and every other element within `mask_db`
    of it. spectra = {name: [dB per band]}. Bands where the loudest element sits more than
    `floor_db` under the loudest band of any element are left out (nothing audible to
    fight over). Returns [{hz, loudest, within: [[name, dB under]]}] for contested bands."""
    names = [n for n, s in spectra.items() if s and all(np.isfinite(s))]
    if len(names) < 2:
        return []
    top = max(max(spectra[n]) for n in names)
    out = []
    for i, hz in enumerate(THIRD_OCTAVES):
        lv = sorted(((spectra[n][i], n) for n in names), reverse=True)
        best, who = lv[0]
        if best < top - floor_db:
            continue
        within = [[n, round(best - v, 1)] for v, n in lv[1:] if best - v <= mask_db]
        if within:
            out.append({"hz": hz, "loudest": who, "within": within})
    return out


def _delete_render_tracks(call, name):
    """Delete every track named `name`. Live strips trailing spaces from track names:
    match stripped, or a leftover render track keeps playing in the set."""
    tracks = call("get_song")["tracks"]
    for t in sorted([t for t in tracks if t["name"].strip() == name.strip()], key=lambda t: -t["i"]):
        call("delete_track", {"track": t["i"]})


def render(call, start_bar, end_bar, name, timeout_s, sleep=time.sleep, poll_s=None):
    """Record the master over [start_bar, end_bar), delete the render track, return the file."""
    call("record_master", {"start_bar": start_bar, "end_bar": end_bar, "name": name})
    t0 = time.time()
    try:
        while True:
            sleep(POLL_S if poll_s is None else poll_s)
            st = call("record_status")
            if st.get("state") == "done":
                return st["file"]
            if st.get("state") not in ("recording", "finalizing"):
                raise RuntimeError("render %s: %s" % (name, st))
            if time.time() - t0 > timeout_s:
                try:
                    call("record_abort")
                finally:
                    raise RuntimeError("render %s timed out: %s" % (name, st))
    finally:
        _delete_render_tracks(call, name)


def expected_seconds(n_elements, start_bar, end_bar, tempo):
    return round(n_elements * ((end_bar - start_bar) * 4 * 60.0 / tempo + 6))


def run(call, tracks, start_bar, end_bar, kick="KICK", spectra=True, mask_db=MASK_DB,
        sleep=time.sleep, measure_fn=None, timeout_s=None, log=None):
    """Solo each of `tracks` (the kick first) over [start_bar, end_bar) with the master
    limiter off and render it. Solo states and the limiter are restored whatever happens.
    Returns {elements: {name: {lufs, vs_kick_lu, peak_db, third_octave_db?}}, hz?,
    masking?, failed}."""
    measure_fn = measure_fn or measure
    song = call("get_song")
    tempo = song.get("tempo", 120.0)
    seconds = (end_bar - start_bar) * 4 * 60.0 / tempo
    timeout_s = timeout_s or seconds + 60
    names = [kick] + [t for t in tracks if t != kick]
    soloed = [t["name"] for t in song["tracks"] if t.get("solo")]
    limiters = [d for d in song.get("master", {}).get("devices", []) if d == "Limiter"]
    was_on = {}
    out, failed = {}, {}
    try:
        for d in limiters:
            r = call("set_device_on", {"track": "master", "device": d, "on": False})
            was_on[d] = (r or {}).get("before", {}).get("on", True)
        for n in soloed:
            call("set_track", {"track": n, "solo": False})
        for n in names:
            call("set_track", {"track": n, "solo": True})
            try:
                path = render(call, start_bar, end_bar, ("%s %s" % (PREFIX, n[:12])).strip(),
                              timeout_s, sleep=sleep)
                lufs, peak, third = measure_fn(path)
                if not np.isfinite(lufs):     # nothing played in these bars
                    out[n] = {"lufs": None, "silent": True, "file": path}
                else:
                    out[n] = {"lufs": round(lufs, 1), "peak_db": round(peak, 1), "file": path}
                    if spectra:
                        out[n]["third_octave_db"] = [round(v, 1) for v in third]
            except Exception as e:   # one element failing must not leave the set soloed
                failed[n] = str(e)
            finally:
                call("set_track", {"track": n, "solo": False})
            if log:
                log("%s: %s" % (n, out[n]["lufs"] if n in out else "failed"))
    finally:
        for n in soloed:
            call("set_track", {"track": n, "solo": True})
        for d in limiters:
            call("set_device_on", {"track": "master", "device": d, "on": was_on.get(d, True)})
    k = out.get(kick, {}).get("lufs")
    for e in out.values():
        e["vs_kick_lu"] = round(e["lufs"] - k, 1) if k is not None and e["lufs"] is not None else None
    res = {"bars": [start_bar, end_bar], "kick": kick, "elements": out, "failed": failed}
    if spectra:
        res["hz"] = THIRD_OCTAVES
        res["masking"] = masking({n: e["third_octave_db"] for n, e in out.items()
                                  if e["lufs"] is not None}, mask_db)
    return res
