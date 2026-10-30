"""One track out of a DJ set: fetch a stretch of a set (a YouTube link or a file) and find
where the track heard at a given moment plays alone.

A set mixes each track into the next for 16-64 bars, so a cut taken at the timestamp a
listener names holds the previous track's tail, and a long one the next track's intro.
Analysed whole, the next track's kick pattern and chords read as the reference's (Mochakk,
Mixmag Lab Mocambique, 17:10: the cut 17:22-24:30 swapped to an XX..XX.. kick and new
chords from bar 169). Here every 4-bar block is compared with the track's core, the 30-90 s
after the named moment, on the three things that tell one record from another: the kick's
16-step pattern, the hats' 16-step pattern and the chroma. That similarity has three
levels: the track alone (core ~0.9, breaks ~0.6-0.75), mixed with a neighbour (~0.45-0.7)
and another record (<0.4)."""
import os
import re
import shutil
import subprocess

import numpy as np
import soundfile as sf
from scipy import signal

from . import references
from .music import samples

BLOCK = 4               # bars per block
SOLO = 0.7              # similarity to the core of a block where the track plays alone
IN_MIX = 0.45           # ... where it still plays, under or over a neighbour
LOOKAHEAD = 8           # blocks a dip may last and still be the track's own break: house
                        # breaks run 16-32 bars, and a record mixed out never comes back


def seconds(t):
    """'17:10', '1:02:03', '1030', '1030s' or a number -> seconds."""
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    t = str(t).strip().rstrip("s")
    parts = [float(p) for p in t.split(":")]
    s = 0.0
    for p in parts:
        s = s * 60 + p
    return s


def clock(s):
    s = max(0.0, float(s))
    h, rem = divmod(int(round(s)), 3600)
    m, sec = divmod(rem, 60)
    return "%d:%02d:%02d" % (h, m, sec) if h else "%d:%02d" % (m, sec)


def url_start(url):
    """The start time a YouTube link carries (t=1097s, t=18m17s, start=...)."""
    m = re.search(r"[?&#](?:t|start)=([0-9hms:]+)", url or "")
    if not m:
        return None
    v = m.group(1)
    if re.fullmatch(r"[0-9.]+s?", v):
        return float(v.rstrip("s"))
    hms = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", v)
    if hms and any(hms.groups()):
        h, mi, s = (int(g or 0) for g in hms.groups())
        return float(h * 3600 + mi * 60 + s)
    return seconds(v)


def fetch(url, start_s, end_s, out_dir):
    """Download [start_s, end_s] of a set's audio as WAV with yt-dlp. Returns its path."""
    exe = shutil.which("yt-dlp")
    if not exe:
        raise RuntimeError("yt-dlp is not installed (brew install yt-dlp)")
    os.makedirs(out_dir, exist_ok=True)
    stem = "set_%s-%s" % (clock(start_s).replace(":", "m"), clock(end_s).replace(":", "m"))
    out = os.path.join(out_dir, stem + ".wav")
    if os.path.exists(out):
        return out
    subprocess.run([exe, "-q", "--no-playlist", "-x", "--audio-format", "wav",
                    "--download-sections", "*%s-%s" % (clock(start_s), clock(end_s)),
                    "-o", os.path.join(out_dir, stem + ".%(ext)s"), url],
                   check=True, capture_output=True, timeout=900)
    if not os.path.exists(out):
        raise RuntimeError("yt-dlp finished without writing %s" % out)
    return out


def _flux(mono, sr, lo, hi, hop):
    sos = signal.butter(4, [lo, hi], "bandpass", fs=sr, output="sos")
    env = np.sqrt(signal.sosfilt(sos, mono) ** 2)
    n = len(env) // hop
    env = np.log1p(100 * env[: n * hop].reshape(n, hop).mean(axis=1))
    return np.r_[0.0, np.maximum(0.0, np.diff(env))]


def _chroma(mono, sr, hop):
    import librosa
    y = signal.resample_poly(mono, 22050, sr) if sr != 22050 else mono
    return librosa.feature.chroma_cqt(y=y, sr=22050, hop_length=hop), 22050 / hop


def _unit(v):
    v = v - v.mean()
    return v / (np.linalg.norm(v) + 1e-9)


def _shape(pattern):
    """A 16-step pattern by its rhythm, not its phase: the magnitudes of its 16-step
    Fourier series stay the same when the grid's bar line falls on another beat."""
    return _unit(np.abs(np.fft.rfft(pattern))[1:])


def block_features(mono, sr, bpm, t0):
    """Per 4-bar block: kick and hat 16-step attack patterns (as rhythm shapes) and chroma,
    each unit length, so each counts the same whatever its level."""
    hop = 256
    fps = sr / hop
    kick, hats = _flux(mono, sr, 30, 150, hop), _flux(mono, sr, 5000, 11000, hop)
    chroma, cfps = _chroma(mono, sr, 1024)
    bar = 240.0 / bpm
    n = int((len(mono) / sr - t0) / bar)
    rows = []
    for b in range(n):
        a = t0 + b * bar
        steps = [int((a + k * bar / 16) * fps) for k in range(16)]
        kp = np.array([kick[s: s + 3].max() for s in steps])
        hp = np.array([hats[s: s + 3].max() for s in steps])
        ch = chroma[:, int(a * cfps): max(int(a * cfps) + 1, int((a + bar) * cfps))].mean(axis=1)
        rows.append(np.r_[_shape(kp), _shape(hp), _unit(ch)] / np.sqrt(3))
    rows = np.array(rows)
    nb = len(rows) // BLOCK
    return np.array([rows[i * BLOCK:(i + 1) * BLOCK].mean(axis=0) for i in range(nb)])


def similarity(blocks, core_from, core_to):
    core = np.median(blocks[core_from:core_to], axis=0)
    norms = np.linalg.norm(blocks, axis=1) * np.linalg.norm(core) + 1e-9
    return blocks @ core / norms


def _run(sim, seed, thr):
    """Blocks around `seed` where the track holds `thr`, letting a dip of up to LOOKAHEAD
    blocks (a break) through when the track comes back after it."""
    lo = hi = seed
    while hi + 1 < len(sim) and np.max(sim[hi + 1: hi + 1 + LOOKAHEAD]) >= thr:
        hi += 1 + int(np.argmax(sim[hi + 1: hi + 1 + LOOKAHEAD] >= thr))
    while lo > 0 and np.max(sim[max(0, lo - LOOKAHEAD): lo]) >= thr:
        win = sim[max(0, lo - LOOKAHEAD): lo]
        lo = max(0, lo - LOOKAHEAD) + int(np.flatnonzero(win >= thr)[0])
    return lo, hi


def isolate(path, at_s, offset_s=0.0, bpm=None):
    """Find the track playing `at_s` seconds into the file. `offset_s` is where the file
    starts in the set, so the result's times read as set times."""
    x, sr = references.load_audio(path)
    mono = x.mean(axis=1)
    i = int(max(0.0, at_s) * sr)
    mid = mono[i: i + 60 * sr]
    tempo = bpm or references.refine_tempo(mono, sr, samples.estimate_tempo(
        mid if len(mid) > 10 * sr else mono, sr, lo=100.0, hi=140.0))
    t0 = references.beat_grid(mono[: 90 * sr], sr, tempo)
    blocks = block_features(mono, sr, tempo, t0)
    block_s = BLOCK * 240.0 / tempo
    seed = int((at_s - t0) / block_s)
    # the core: 30-90 s after the named moment, where a DJ has finished mixing it in
    c0 = min(len(blocks) - 1, seed + int(round(30 / block_s)))
    c1 = min(len(blocks), max(c0 + 2, seed + int(round(90 / block_s))))
    sim = similarity(blocks, c0, c1)
    s_lo, s_hi = _run(sim, int(np.argmax(sim[c0:c1])) + c0, SOLO)
    m_lo, m_hi = _run(sim, s_lo, IN_MIX)
    m_hi = max(m_hi, _run(sim, s_hi, IN_MIX)[1])
    at = lambda blk: round(float(t0 + blk * block_s), 2)
    span = lambda a, b: {"start_s": at(a), "end_s": at(b + 1),
                         "set_start": clock(offset_s + at(a)),
                         "set_end": clock(offset_s + at(b + 1)),
                         "bars": (b + 1 - a) * BLOCK}
    return {
        "bpm": float(tempo), "first_beat_s": round(float(t0), 3), "block_bars": BLOCK,
        "alone": span(s_lo, s_hi), "in_mix": span(m_lo, m_hi),
        "similarity": [{"set_time": clock(offset_s + at(k)), "sim": round(float(v), 2)}
                       for k, v in enumerate(sim)],
    }


def cut(path, start_s, end_s, out):
    x, sr = sf.read(path, always_2d=True, dtype="float32")
    a, e = int(start_s * sr), int(end_s * sr)
    seg = x[a:e].copy()
    fade = min(len(seg) // 4, int(0.05 * sr))
    if fade:
        ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
        seg[:fade] *= ramp
        seg[-fade:] *= ramp[::-1]
    sf.write(out, seg, sr, subtype="PCM_24")
    return out


def reference_from_set(source, at=None, before_s=90.0, after_s=600.0, out_dir=None,
                       name=None, bpm=None):
    """Fetch the stretch of a set around `at` (a link's own t= when omitted), find where
    that track plays alone and write it as a WAV for analyze_reference / listen /
    study_references."""
    is_url = bool(re.match(r"https?://", str(source)))
    at_s = seconds(at) if at is not None else (url_start(source) if is_url else None)
    if at_s is None:
        raise ValueError("give `at` (the set time the track starts, e.g. '17:10')")
    out_dir = os.path.expanduser(out_dir or "~/Desktop/Tracks/refs_from_sets")
    os.makedirs(out_dir, exist_ok=True)
    if is_url:
        start = max(0.0, at_s - before_s)
        path = fetch(source, start, at_s + after_s, out_dir)
        found = isolate(path, at_s - start, offset_s=start, bpm=bpm)
    else:
        path, start = source, 0.0
        found = isolate(path, at_s, bpm=bpm)
    alone = found["alone"]
    stem = name or "ref_%s" % found["alone"]["set_start"].replace(":", "m")
    out = cut(path, alone["start_s"], alone["end_s"], os.path.join(out_dir, stem + ".wav"))
    sims = found.pop("similarity")
    note = ("%d bars alone (%s-%s in the set); mixed with its neighbours %s-%s. Analyse the "
            "alone cut: the mixed edges carry the other records' kick and chords."
            % (alone["bars"], alone["set_start"], alone["set_end"],
               found["in_mix"]["set_start"], found["in_mix"]["set_end"]))
    return {"path": out, "set_audio": path, **found, "summary": note,
            "similarity_by_block": sims}


def fetch_full(url, out_dir, name):
    """The whole set's audio as the site serves it (opus/m4a, ~100 MB for 100 minutes)."""
    exe = shutil.which("yt-dlp")
    if not exe:
        raise RuntimeError("yt-dlp is not installed (brew install yt-dlp)")
    os.makedirs(out_dir, exist_ok=True)
    have = [f for f in os.listdir(out_dir) if f.startswith(name + "_full.")]
    if have:
        return os.path.join(out_dir, have[0])
    subprocess.run([exe, "-q", "--no-playlist", "-f", "bestaudio",
                    "-o", os.path.join(out_dir, name + "_full.%(ext)s"), url],
                   check=True, capture_output=True, timeout=1800)
    have = [f for f in os.listdir(out_dir) if f.startswith(name + "_full.")]
    if not have:
        raise RuntimeError("yt-dlp finished without writing the set")
    return os.path.join(out_dir, have[0])


def _decode(path, start_s, dur_s, out, sr=references.SR):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % start_s, "-t", "%.3f" % dur_s,
                    "-i", path, "-ac", "2", "-ar", str(sr), out], check=True)
    return out


def _duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], check=True, capture_output=True, text=True)
    return float(r.stdout.strip())


def set_blocks(path, start_s=0.0, end_s=None, chunk_s=480.0, log=print):
    """Block features over a long set, decoded `chunk_s` at a time (a 100-minute set does
    not fit in memory as float audio), each chunk on its own tempo and grid. Returns
    (start times in the set, features, bpm per block)."""
    import tempfile
    end_s = end_s or _duration(path)
    times, feats, bpms = [], [], []
    with tempfile.TemporaryDirectory() as d:
        t = start_s
        while t < end_s - 30:
            dur = min(chunk_s, end_s - t)
            x, sr = references.load_audio(_decode(path, t, dur, os.path.join(d, "c.wav")))
            mono = x.mean(axis=1)
            tempo = references.refine_tempo(mono, sr, samples.estimate_tempo(
                mono[: 60 * sr], sr, lo=100.0, hi=140.0))
            t0 = references.beat_grid(mono[: 90 * sr], sr, tempo)
            blocks = block_features(mono, sr, tempo, t0)
            block_s = BLOCK * 240.0 / tempo
            for k, f in enumerate(blocks):
                times.append(t + t0 + k * block_s)
                feats.append(f)
                bpms.append(tempo)
            log("blocks %s-%s at %.1f BPM" % (clock(t), clock(t + dur), tempo))
            t = times[-1] + block_s if len(blocks) else t + dur
    return np.array(times), np.array(feats), np.array(bpms)


def _stable_from(feats, j, span=6):
    """How much the `span` blocks from j agree with their own median: a track playing
    alone repeats its loop, a blend of two moves."""
    if j + span > len(feats):
        return 0.0
    return float(np.median(similarity(feats[j:j + span], 0, span)))


def split(times, feats, min_bars=48, span=6):
    """Walk the set: from each stretch that holds its own loop, extend the track as far as
    it plays alone (breaks pass), record it when long enough, go on after it."""
    tracks, i, n = [], 0, len(feats)
    while i < n - span:
        if _stable_from(feats, i, span) < SOLO:
            i += 1
            continue
        lo, hi = _run(similarity(feats, i, i + span), i, SOLO)
        # the first stable stretch can be the blend itself: re-centre the core on the
        # middle of what was found and walk again from there
        mid = (lo + hi) // 2
        c0 = max(0, min(mid - span // 2, n - span))
        lo, hi = _run(similarity(feats, c0, c0 + span), mid, SOLO)
        lo = max(lo, tracks[-1]["hi"] + 1 if tracks else 0)
        if (hi + 1 - lo) * BLOCK >= min_bars:
            # two 4x4 records share most of their rhythm shape, so a blend's edge can still
            # pass as the track: keep one block clear of each end when there is room
            if (hi - 1 - lo) * BLOCK >= min_bars:
                lo, hi = lo + 1, hi - 1
            tracks.append({"lo": lo, "hi": hi})
            i = hi + 1
        else:
            i += 1
    return tracks


def split_set(source, start=None, end=None, out_dir=None, name="set", min_bars=48, log=print):
    """Every track of a DJ set (a link or a file), each cut where it plays alone, for
    study_references(name, folder=<out_dir>)."""
    out_dir = os.path.expanduser(out_dir or "~/Desktop/Tracks/refs_from_sets/%s" % name)
    os.makedirs(out_dir, exist_ok=True)
    is_url = bool(re.match(r"https?://", str(source)))
    path = fetch_full(source, os.path.dirname(out_dir), name) if is_url else source
    cache = os.path.join(out_dir, ".blocks_%s_%s.npz" % (seconds(start) or 0, seconds(end) or "end"))
    if os.path.exists(cache):
        z = np.load(cache)
        times, feats, bpms = z["times"], z["feats"], z["bpms"]
    else:
        times, feats, bpms = set_blocks(path, seconds(start) or 0.0, seconds(end), log=log)
        np.savez(cache, times=times, feats=feats, bpms=bpms)
    found = []
    for k, tr in enumerate(split(times, feats, min_bars)):
        a, b = times[tr["lo"]], times[min(tr["hi"] + 1, len(times) - 1)]
        if tr["hi"] + 1 >= len(times):
            b = times[-1] + BLOCK * 240.0 / bpms[-1]
        out = os.path.join(out_dir, "%s_%02d_%s.wav" % (name, k + 1, clock(a).replace(":", "m")))
        _decode(path, a, b - a, out)
        found.append({"path": out, "set_start": clock(a), "set_end": clock(b),
                      "bars": (tr["hi"] + 1 - tr["lo"]) * BLOCK,
                      "bpm": round(float(np.median(bpms[tr["lo"]: tr["hi"] + 1])), 1)})
        log("track %d: %s-%s" % (k + 1, clock(a), clock(b)))
    return {"set_audio": path, "folder": out_dir, "tracks": found,
            "summary": "%d tracks cut alone from %s; study them with "
                       "study_references(name, folder=%r)" % (len(found), clock(times[-1]), out_dir)}
