"""Command handlers for ClaudeBridge. Hot-reloadable via the `reload` command.

Every handler runs on Live's main thread and takes (ctx, **kwargs).
Times are in beats (quarter notes) unless an argument name says `bar`.
Tracks are addressed by index, exact name, unique name fragment,
"master", or "return:<index|name>".
"""
import re
import time
import traceback
import types

import Live

VERSION = "0.2.3"

COMMANDS = {}
DEFERRED_TIMEOUT_S = 30.0


def command(fn):
    COMMANDS[fn.__name__] = fn
    return fn


class Context(object):
    def __init__(self, cs, previous=None):
        self.cs = cs
        self.record_job = getattr(previous, "record_job", None)
        self.browser_cache = getattr(previous, "browser_cache", {})
        self.pending = getattr(previous, "pending", [])
        _install_main_loop(cs)

    @property
    def song(self):
        return self.cs.song()

    @property
    def app(self):
        return self.cs.application()

    def log(self, msg):
        self.cs.log_message("ClaudeBridge: %s" % msg)


# ======================================================================
# main loop
#
# Live keeps Remote Script modules in memory until it restarts: re-selecting the
# control surface builds a new instance from the *old* __init__ code. So the main
# loop lives here and is installed onto the control surface class every time this
# module is (re)loaded. __init__.py only has to provide the socket, the inbox queue
# and a `reload` path; everything else follows this file.
# ======================================================================

def _main_loop(cs):
    import importlib
    import queue
    import sys
    mod = sys.modules[__name__]
    type(cs).__mro__[1].update_display(cs)
    for _ in range(64):
        try:
            cmd, args, reply = cs._inbox.get_nowait()
        except queue.Empty:
            break
        if cmd == "reload":
            try:
                mod = importlib.reload(mod)
                cs._ctx = mod.Context(cs, previous=cs._ctx)
                reply.put((True, {"reloaded": True, "handlers_version": mod.VERSION}))
            except Exception as e:
                reply.put((False, {"error": "reload failed: %s" % e,
                                   "trace": traceback.format_exc(limit=6)}))
            continue
        try:
            mod.dispatch(cs._ctx, cmd, args, reply)
        except Exception as e:
            reply.put((False, _err(e)))
    try:
        mod.tick(cs._ctx)
    except Exception as e:
        cs.log_message("ClaudeBridge: tick error: %s" % e)


def _install_main_loop(cs):
    type(cs).update_display = _main_loop


# ======================================================================
# dispatch
#
# A handler either returns a value, or is a generator: each bare `yield` hands
# control back to Live until the next tick (~100 ms), which is how a command waits
# for Live to apply a change (Live applies e.g. playhead moves only on the next
# tick). The generator's `return` value is the reply.
# ======================================================================

def _err(e):
    return {"error": "%s: %s" % (type(e).__name__, e), "trace": traceback.format_exc(limit=6)}


def _run(ctx, cmd, args):
    fn = COMMANDS.get(cmd)
    if fn is None:
        raise LookupError("unknown command: %s" % cmd)
    return fn(ctx, **args)


def dispatch(ctx, cmd, args, reply):
    if cmd == "batch":
        out = []
        for item in args.get("commands", []):
            try:
                r = _run(ctx, item.get("cmd"), item.get("args") or {})
                if isinstance(r, types.GeneratorType):
                    r.close()
                    raise RuntimeError("%s waits on Live and cannot run inside a batch"
                                       % item.get("cmd"))
                out.append({"ok": True, "result": r})
            except Exception as e:
                out.append(dict({"ok": False}, **_err(e)))
        reply.put((True, out))
        return
    if cmd not in COMMANDS:
        reply.put((False, {"error": "unknown command: %s" % cmd, "available": sorted(COMMANDS)}))
        return
    try:
        r = _run(ctx, cmd, args)
    except Exception as e:
        reply.put((False, _err(e)))
        return
    if isinstance(r, types.GeneratorType):
        ctx.pending.append({"gen": r, "reply": reply, "cmd": cmd,
                            "deadline": time.time() + DEFERRED_TIMEOUT_S})
        _advance(ctx, ctx.pending[-1])
    else:
        reply.put((True, r))


def _advance(ctx, job):
    """Run a deferred command up to its next `yield`. Returns True when finished."""
    try:
        next(job["gen"])
    except StopIteration as stop:
        job["reply"].put((True, stop.value))
        ctx.pending.remove(job)
        return True
    except Exception as e:
        job["reply"].put((False, _err(e)))
        ctx.pending.remove(job)
        return True
    if time.time() > job["deadline"]:
        job["gen"].close()
        job["reply"].put((False, {"error": "%s timed out waiting on Live" % job["cmd"]}))
        ctx.pending.remove(job)
        return True
    return False


# ======================================================================
# addressing helpers
# ======================================================================

def _beats_per_bar(ctx):
    s = ctx.song
    return s.signature_numerator * 4.0 / s.signature_denominator


def _t(ctx, beat=None, bar=None, default=None):
    """Resolve a time given either in beats or in 1-based bars."""
    if beat is not None:
        return float(beat)
    if bar is not None:
        return (float(bar) - 1.0) * _beats_per_bar(ctx)
    if default is not None:
        return float(default)
    raise ValueError("time required: pass beat or bar")


def _track(ctx, spec):
    s = ctx.song
    if isinstance(spec, int):
        return s.tracks[spec]
    if not isinstance(spec, str):
        raise ValueError("bad track spec: %r" % (spec,))
    if spec == "master":
        return s.master_track
    if spec.startswith("return:"):
        key = spec[7:]
        if key.isdigit():
            return s.return_tracks[int(key)]
        for r in s.return_tracks:
            if r.name == key:
                return r
        raise ValueError("return track not found: %s" % key)
    if spec.lstrip("-").isdigit():
        return s.tracks[int(spec)]
    for t in s.tracks:
        if t.name == spec:
            return t
    hits = [t for t in s.tracks if spec.lower() in t.name.lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ValueError("track not found: %s" % spec)
    raise ValueError("ambiguous track %r: %s" % (spec, [t.name for t in hits]))


def _track_index(ctx, track):
    for i, t in enumerate(ctx.song.tracks):
        if t == track:
            return i
    return None


def _device(track, spec):
    devs = list(track.devices)
    if isinstance(spec, int):
        return devs[spec]
    for d in devs:
        if d.name == spec:
            return d
    hits = [d for d in devs if spec.lower() in d.name.lower()]
    if len(hits) == 1:
        return hits[0]
    raise ValueError("device %r not found/ambiguous on %s: %s"
                     % (spec, track.name, [d.name for d in devs]))


def _param(device, spec):
    ps = list(device.parameters)
    if isinstance(spec, int):
        return ps[spec]
    for p in ps:
        if p.name == spec:
            return p
    hits = [p for p in ps if spec.lower() in p.name.lower()]
    if len(hits) == 1:
        return hits[0]
    raise ValueError("param %r not found/ambiguous on %s: %s"
                     % (spec, device.name, [p.name for p in ps][:60]))


def _mixer_param(track, which):
    m = track.mixer_device
    if which == "volume":
        return m.volume
    if which in ("pan", "panning"):
        return m.panning
    if which.startswith("send:"):
        return m.sends[int(which[5:])]
    raise ValueError("mixer param must be volume, pan or send:<n>")


def _arr_clips(track):
    return sorted(track.arrangement_clips, key=lambda c: c.start_time)


def _clip(track, spec):
    clips = _arr_clips(track)
    if isinstance(spec, int):
        return clips[spec]
    if isinstance(spec, dict) and "at" in spec:
        at = float(spec["at"])
        for c in clips:
            if abs(c.start_time - at) < 1e-3:
                return c
        for c in clips:
            if c.start_time <= at < c.end_time:
                return c
        raise ValueError("no clip at beat %s on %s" % (at, track.name))
    if isinstance(spec, str):
        for c in clips:
            if c.name == spec:
                return c
    raise ValueError("clip not found: %r" % (spec,))


# ======================================================================
# value helpers
# ======================================================================

_DB_RE = re.compile(r"(-?inf|[-+]?\d+(?:\.\d+)?)")


def _db_of(param, value=None):
    txt = param.str_for_value(param.value if value is None else value)
    txt = txt.replace("−", "-")
    m = _DB_RE.search(txt)
    if not m:
        return None
    v = m.group(1)
    return float("-inf") if "inf" in v else float(v)


def _set_db(param, db):
    """Bisection on the parameter's own display string: exact for any curve."""
    if db == float("-inf") or db <= -69.9:
        param.value = param.min
        return
    lo, hi = param.min, param.max
    for _ in range(40):
        mid = (lo + hi) / 2.0
        d = _db_of(param, mid)
        if d is None or d < db:
            lo = mid
        else:
            hi = mid
    param.value = hi


def _set_by_display(param, target):
    """Set a param so its display (e.g. '150 Hz', '-12 dB') matches target number."""
    lo, hi = param.min, param.max
    target = float(target)

    def num(v):
        m = _DB_RE.search(param.str_for_value(v).replace("−", "-").replace("k", "e3"))
        if not m or "inf" in m.group(1):
            return float("-inf")
        s = param.str_for_value(v)
        n = float(m.group(1))
        return n * 1000.0 if "kHz" in s else n

    increasing = num(hi) >= num(lo)
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if (num(mid) < target) == increasing:
            lo = mid
        else:
            hi = mid
    param.value = (lo + hi) / 2.0


def _param_info(p):
    return {"name": p.name, "value": round(p.value, 5), "min": p.min, "max": p.max,
            "display": p.str_for_value(p.value), "quantized": p.is_quantized}


def _track_kind(t):
    if getattr(t, "is_foldable", False):
        return "group"
    if t.has_midi_input:
        return "midi"
    return "audio"


def _clip_info(c):
    d = {"name": c.name, "start": round(c.start_time, 4), "end": round(c.end_time, 4),
         "length": round(c.length, 4), "muted": c.muted,
         "type": "audio" if c.is_audio_clip else "midi"}
    if c.is_audio_clip:
        d["file"] = c.file_path
        d["warping"] = c.warping
        d["pitch"] = c.pitch_coarse
        d["gain_db"] = _db_of_clip_gain(c)
    return d


def _db_of_clip_gain(c):
    try:
        txt = c.gain_display_string.replace("−", "-")
        m = _DB_RE.search(txt)
        return float(m.group(1)) if m and "inf" not in m.group(1) else None
    except Exception:
        return None


# ======================================================================
# read
# ======================================================================

@command
def ping(ctx):
    app = ctx.app
    return {"bridge": VERSION,
            "live": "%d.%d.%d" % (app.get_major_version(), app.get_minor_version(),
                                  app.get_bugfix_version())}


@command
def get_song(ctx):
    s = ctx.song
    bpb = _beats_per_bar(ctx)
    tracks = []
    for i, t in enumerate(s.tracks):
        clips = list(t.arrangement_clips) if not getattr(t, "is_foldable", False) else []
        active = [c for c in clips if not c.muted]
        item = {"i": i, "name": t.name, "kind": _track_kind(t),
                "vol_db": _db_of(t.mixer_device.volume),
                "pan": round(t.mixer_device.panning.value, 2),
                "mute": t.mute, "solo": t.solo,
                "devices": [d.name for d in t.devices],
                "clips": len(clips), "clips_active": len(active)}
        if getattr(t, "is_grouped", False) and t.group_track is not None:
            item["group"] = t.group_track.name
        if active:
            item["bars"] = [round(min(c.start_time for c in active) / bpb + 1, 2),
                            round(max(c.end_time for c in active) / bpb + 1, 2)]
        tracks.append(item)
    return {
        "tempo": s.tempo,
        "signature": "%d/%d" % (s.signature_numerator, s.signature_denominator),
        "song_length_beats": s.song_length,
        "is_playing": s.is_playing,
        "time_beats": round(s.current_song_time, 3),
        "cues": [{"name": c.name, "beat": c.time, "bar": round(c.time / bpb + 1, 2)}
                 for c in sorted(s.cue_points, key=lambda c: c.time)],
        "tracks": tracks,
        "returns": [{"name": r.name, "devices": [d.name for d in r.devices],
                     "vol_db": _db_of(r.mixer_device.volume)} for r in s.return_tracks],
        "master": {"devices": [d.name for d in s.master_track.devices],
                   "vol_db": _db_of(s.master_track.mixer_device.volume)},
    }


@command
def get_track(ctx, track, clips=True, max_clips=200):
    t = _track(ctx, track)
    d = {"name": t.name, "kind": _track_kind(t),
         "vol_db": _db_of(t.mixer_device.volume),
         "pan": t.mixer_device.panning.value,
         "devices": [{"i": i, "name": dv.name, "class": dv.class_name,
                      "on": dv.parameters[0].value > 0 if len(dv.parameters) else None}
                     for i, dv in enumerate(t.devices)]}
    if clips and hasattr(t, "arrangement_clips"):
        cl = _arr_clips(t)
        d["n_clips"] = len(cl)
        d["clips"] = [dict(_clip_info(c), i=i) for i, c in enumerate(cl[:max_clips])]
    return d


@command
def get_device(ctx, track, device):
    dv = _device(_track(ctx, track), device)
    return {"name": dv.name, "class": dv.class_name,
            "params": [dict(_param_info(p), i=i) for i, p in enumerate(dv.parameters)]}


@command
def get_notes(ctx, track, clip):
    c = _clip(_track(ctx, track), clip)
    notes = c.get_notes_extended(0, 128, -1e6, 2e6)
    return [[n.pitch, round(n.start_time, 4), round(n.duration, 4), n.velocity]
            for n in sorted(notes, key=lambda n: (n.start_time, n.pitch))]


# ======================================================================
# song / tracks
# ======================================================================

@command
def set_tempo(ctx, bpm):
    ctx.song.tempo = float(bpm)
    return {"tempo": ctx.song.tempo}


@command
def create_track(ctx, kind="midi", name=None, index=-1):
    s = ctx.song
    n_before = len(s.tracks)
    if kind == "midi":
        s.create_midi_track(index)
    elif kind == "audio":
        s.create_audio_track(index)
    else:
        raise ValueError("kind must be midi or audio")
    i = n_before if index == -1 else index
    t = s.tracks[i]
    if name:
        t.name = name
    return {"i": i, "name": t.name}


@command
def delete_track(ctx, track):
    t = _track(ctx, track)
    i = _track_index(ctx, t)
    ctx.song.delete_track(i)
    return {"deleted": i}


@command
def set_track(ctx, track, name=None, volume_db=None, pan=None, mute=None, solo=None,
              arm=None, monitoring=None, color_index=None):
    t = _track(ctx, track)
    if name is not None:
        t.name = name
    if volume_db is not None:
        _set_db(t.mixer_device.volume, float(volume_db))
    if pan is not None:
        t.mixer_device.panning.value = max(-1.0, min(1.0, float(pan)))
    if mute is not None:
        t.mute = bool(mute)
    if solo is not None:
        t.solo = bool(solo)
    if arm is not None and t.can_be_armed:
        t.arm = bool(arm)
    if monitoring is not None:
        t.current_monitoring_state = {"in": 0, "auto": 1, "off": 2}[monitoring]
    if color_index is not None:
        t.color_index = int(color_index)
    return {"name": t.name, "vol_db": _db_of(t.mixer_device.volume),
            "pan": t.mixer_device.panning.value, "mute": t.mute}


@command
def set_send(ctx, track, send, db):
    t = _track(ctx, track)
    _set_db(t.mixer_device.sends[int(send)], float(db))
    return {"send": send, "db": _db_of(t.mixer_device.sends[int(send)])}


# ======================================================================
# clips
# ======================================================================

def _find_new_clip(track, start, before):
    """Live hands out a fresh Python wrapper on every access, so identity is compared
    with == (same underlying clip), never with id()."""
    at = [c for c in _arr_clips(track) if abs(c.start_time - start) < 1e-3]
    fresh = [c for c in at if not any(c == b for b in before)]
    if fresh:
        return fresh[0]
    return at[0] if at else None


def _raw_for_db(param, db):
    lo, hi = param.min, param.max
    if db <= -69.9:
        return lo
    for _ in range(40):
        mid = (lo + hi) / 2.0
        d = _db_of(param, mid)
        if d is None or d < db:
            lo = mid
        else:
            hi = mid
    return hi


def _write_envelope(track, clip, spec, resolution=0.25):
    """spec: {"param": "volume"|"pan"|"send:<n>"|<device param>, "device": None|name|index,
              "points": [[beat_from_clip_start, value], ...], "unit": "raw"|"db"}
    Linear ramps between points, drawn as steps of `resolution` beats."""
    device = spec.get("device")
    pname = spec.get("param", "volume")
    p = _mixer_param(track, pname) if device is None else _param(_device(track, device), pname)
    to_raw = (lambda v: _raw_for_db(p, v)) if spec.get("unit") == "db" else float
    env = clip.automation_envelope(p)
    if env is not None:
        clip.clear_envelope(p)
    env = clip.automation_envelope(p) or clip.create_automation_envelope(p)
    offset = clip.loop_start if clip.looping else clip.start_marker
    pts = sorted((float(a), to_raw(v)) for a, v in spec["points"])
    steps = 0
    for (a0, v0), (a1, v1) in zip(pts, pts[1:]):
        x = a0
        while x < a1 - 1e-9:
            f = (x - a0) / (a1 - a0)
            val = max(p.min, min(p.max, v0 + (v1 - v0) * f))
            env.insert_step(offset + x, min(resolution, a1 - x), val)
            x += resolution
            steps += 1
    if len(pts) == 1:
        env.insert_step(offset + pts[0][0], resolution, pts[0][1])
        steps = 1
    return {"param": p.name, "steps": steps}


def _via_session(ctx, t, start, fill):
    """Build a clip in a free Session slot, let `fill(clip)` shape it (notes, envelopes...),
    copy it into the Arrangement at `start`, then remove the Session copy. Needed because
    Live's API only creates automation envelopes on Session clips."""
    slot = _free_slot(ctx, t)
    before = list(t.arrangement_clips)
    try:
        sc = fill(slot)
        t.duplicate_clip_to_arrangement(sc, start)
    finally:
        if slot.has_clip:
            slot.delete_clip()
    return _find_new_clip(t, start, before)


def _free_slot(ctx, track):
    for slot in track.clip_slots:
        if not slot.has_clip:
            return slot
    ctx.song.create_scene(-1)
    return track.clip_slots[-1]


def _note_specs(notes):
    specs = []
    for n in notes:
        if isinstance(n, dict):
            p, st, du, v = n["pitch"], n["start"], n["duration"], n.get("velocity", 100)
            mute = n.get("mute", False)
        else:
            p, st, du = n[0], n[1], n[2]
            v = n[3] if len(n) > 3 else 100
            mute = False
        specs.append(Live.Clip.MidiNoteSpecification(
            pitch=int(p), start_time=float(st), duration=float(du),
            velocity=float(max(1, min(127, v))), mute=bool(mute)))
    return tuple(specs)


@command
def create_midi_clip(ctx, track, length, notes=None, name=None, beat=None, bar=None,
                     loop=False, envelopes=None):
    """MIDI clip in the Arrangement. notes: [[pitch, start, dur, vel], ...] with start
    relative to the clip, in beats. envelopes: see _write_envelope."""
    t = _track(ctx, track)
    start = _t(ctx, beat, bar)
    length = float(length)

    def shape(c):
        if name:
            c.name = name
        c.looping = bool(loop)
        if notes:
            c.add_new_notes(_note_specs(notes))
        for spec in envelopes or []:
            _write_envelope(t, c, spec)
        return c

    if envelopes or not hasattr(t, "create_midi_clip"):
        def fill(slot):
            slot.create_clip(length)
            return shape(slot.clip)
        c = _via_session(ctx, t, start, fill)
        method = "session_dup"
    else:
        before = list(t.arrangement_clips)
        t.create_midi_clip(start, length)
        c = _find_new_clip(t, start, before)
        if c is not None:
            shape(c)
        method = "native"
    if c is None:
        raise RuntimeError("clip not created")
    return dict(_clip_info(c), method=method, n_notes=len(notes or []),
                n_envelopes=len(envelopes or []))


@command
def add_notes(ctx, track, clip, notes, replace=False):
    c = _clip(_track(ctx, track), clip)
    if replace:
        c.remove_notes_extended(0, 128, -1e6, 2e6)
    c.add_new_notes(_note_specs(notes))
    return {"clip": c.name, "added": len(notes)}


@command
def create_audio_clip(ctx, track, path, beat=None, bar=None, name=None, warp=None,
                      gain_db=None, pitch=None, length=None, envelopes=None):
    t = _track(ctx, track)
    start = _t(ctx, beat, bar)

    def shape(c):
        if name:
            c.name = name
        if warp is not None:
            c.warping = bool(warp)
        if pitch is not None:
            c.pitch_coarse = int(pitch)
        if gain_db is not None:
            _set_clip_gain_db(c, float(gain_db))
        if length is not None and c.looping:
            c.loop_end = c.loop_start + float(length)
        for spec in envelopes or []:
            _write_envelope(t, c, spec)
        return c

    if envelopes or not hasattr(t, "create_audio_clip"):
        def fill(slot):
            slot.create_audio_clip(path)
            return shape(slot.clip)
        c = _via_session(ctx, t, start, fill)
        method = "session_dup"
    else:
        before = list(t.arrangement_clips)
        t.create_audio_clip(path, start)
        c = _find_new_clip(t, start, before)
        if c is not None:
            shape(c)
        method = "native"
    if c is None:
        raise RuntimeError("audio clip not created")
    return dict(_clip_info(c), method=method, n_envelopes=len(envelopes or []))


def _set_clip_gain_db(c, db):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        c.gain = mid
        if (_db_of_clip_gain(c) or -1e9) < db:
            lo = mid
        else:
            hi = mid
    c.gain = hi


@command
def set_clip(ctx, track, clip, name=None, muted=None, pitch=None, gain_db=None,
             looping=None, loop_start=None, loop_end=None, warping=None):
    c = _clip(_track(ctx, track), clip)
    if name is not None:
        c.name = name
    if muted is not None:
        c.muted = bool(muted)
    if pitch is not None:
        c.pitch_coarse = int(pitch)
    if gain_db is not None:
        _set_clip_gain_db(c, float(gain_db))
    if looping is not None:
        c.looping = bool(looping)
    if loop_start is not None:
        c.loop_start = float(loop_start)
    if loop_end is not None:
        c.loop_end = float(loop_end)
    if warping is not None:
        c.warping = bool(warping)
    return _clip_info(c)


@command
def mute_clips_in_range(ctx, track, muted, start_bar, end_bar):
    """Deactivate (or reactivate) every arrangement clip overlapping [start_bar, end_bar)."""
    t = _track(ctx, track)
    a, b = _t(ctx, bar=start_bar), _t(ctx, bar=end_bar)
    n = 0
    for c in t.arrangement_clips:
        if c.start_time < b - 1e-3 and c.end_time > a + 1e-3:
            c.muted = bool(muted)
            n += 1
    return {"track": t.name, "changed": n}


@command
def duplicate_clip(ctx, track, clip, beat=None, bar=None):
    t = _track(ctx, track)
    c = _clip(t, clip)
    dest = _t(ctx, beat, bar)
    t.duplicate_clip_to_arrangement(c, dest)
    return {"from": c.start_time, "to": dest}


@command
def delete_clip(ctx, track, clip):
    t = _track(ctx, track)
    c = _clip(t, clip)
    info = _clip_info(c)
    t.delete_clip(c)
    return {"deleted": info}


@command
def clip_envelope(ctx, track, points, param="volume", device=None, unit="raw", slot=None,
                  clip=None):
    """Write an automation envelope on a Session clip (`slot` index).
    Live's API refuses to create envelopes on Arrangement clips, so for the Arrangement
    pass `envelopes=[...]` to create_midi_clip / create_audio_clip instead: they build
    the clip in Session with its envelopes and copy it over."""
    t = _track(ctx, track)
    if slot is None:
        raise ValueError("Live only creates envelopes on Session clips: pass slot=<index>, "
                         "or recreate the Arrangement clip with create_*_clip(envelopes=...)")
    s = t.clip_slots[int(slot)]
    if not s.has_clip:
        raise ValueError("slot %s on %s is empty" % (slot, t.name))
    out = _write_envelope(t, s.clip, {"param": param, "device": device, "points": points,
                                      "unit": unit})
    out["clip"] = s.clip.name
    return out


# ======================================================================
# devices & browser
# ======================================================================

_ROOTS = ("instruments", "audio_effects", "midi_effects", "drums", "sounds",
          "plugins", "user_library", "samples", "packs")


def _walk(item, path, depth, out, limit):
    if len(out) >= limit or depth < 0:
        return
    for ch in item.children:
        p = path + [ch.name]
        if ch.is_loadable:
            out.append((p, ch))
        if ch.is_folder and depth > 0:
            _walk(ch, p, depth - 1, out, limit)
        if len(out) >= limit:
            return


def _index_root(ctx, root_name, depth=5, limit=40000):
    key = (root_name, depth)
    if key in ctx.browser_cache:
        return ctx.browser_cache[key]
    root = getattr(ctx.app.browser, root_name)
    out = []
    _walk(root, [root_name], depth, out, limit)
    ctx.browser_cache[key] = [p for p, _ in out]
    return ctx.browser_cache[key]


def _resolve_path(ctx, path):
    node = getattr(ctx.app.browser, path[0])
    for name in path[1:]:
        nxt = None
        for ch in node.children:
            if ch.name == name:
                nxt = ch
                break
        if nxt is None:
            raise ValueError("browser path broken at %r" % name)
        node = nxt
    return node


@command
def browse(ctx, query, roots=None, limit=30, depth=5):
    """Search the Live browser by name. Returns loadable item paths."""
    roots = roots or ["instruments", "audio_effects", "midi_effects", "drums"]
    q = [w for w in query.lower().split() if w]
    hits = []
    for r in roots:
        for p in _index_root(ctx, r, depth):
            hay = "/".join(p).lower()
            if all(w in hay for w in q):
                hits.append("/".join(p))
                if len(hits) >= limit:
                    return hits
    return hits


@command
def load_device(ctx, track, path=None, query=None, roots=None):
    """Load a browser item onto a track. Give the exact `path` from `browse`,
    or a `query` (first match wins)."""
    t = _track(ctx, track)
    if path is None:
        found = browse(ctx, query, roots=roots, limit=1)
        if not found:
            raise ValueError("nothing in browser matches %r" % query)
        path = found[0]
    item = _resolve_path(ctx, path.split("/"))
    ctx.song.view.selected_track = t
    n = len(t.devices)
    ctx.app.browser.load_item(item)
    return {"loaded": path, "devices": [d.name for d in t.devices], "added": len(t.devices) - n}


@command
def set_param(ctx, track, device, param, value=None, display=None, db=None):
    """Set a device parameter by raw value, by display number (e.g. 150 for '150 Hz'),
    or by dB."""
    p = _param(_device(_track(ctx, track), device), param)
    if db is not None:
        _set_db(p, float(db))
    elif display is not None:
        _set_by_display(p, display)
    else:
        p.value = max(p.min, min(p.max, float(value)))
    return _param_info(p)


@command
def set_device_on(ctx, track, device, on=True):
    dv = _device(_track(ctx, track), device)
    dv.parameters[0].value = 1.0 if on else 0.0
    return {"device": dv.name, "on": bool(on)}


@command
def delete_device(ctx, track, device):
    t = _track(ctx, track)
    dv = _device(t, device)
    idx = list(t.devices).index(dv)
    t.delete_device(idx)
    return {"deleted": dv.name}


# ======================================================================
# locators & transport
# ======================================================================

def _goto(ctx, at, max_ticks=20, settle_ticks=2):
    """Move the playhead and wait until Live has applied it.
    Reading current_song_time back returns the new value at once, but the engine only
    moves on a later tick: acting before then (play, set_or_delete_cue) uses the old
    position. So always give it `settle_ticks`, then confirm."""
    s = ctx.song
    s.current_song_time = at
    for _ in range(settle_ticks):
        yield
    for _ in range(max_ticks):
        if abs(s.current_song_time - at) < 1e-3:
            return
        s.current_song_time = at
        yield
    raise RuntimeError("playhead did not reach beat %s (at %s)" % (at, s.current_song_time))


def _cue_at(ctx, at):
    for c in ctx.song.cue_points:
        if abs(c.time - at) < 1e-3:
            return c
    return None


def _toggle_cue_at(ctx, at, want_present):
    """set_or_delete_cue acts at the playhead, so park the playhead first."""
    s = ctx.song
    if s.is_playing:
        raise RuntimeError("stop playback before editing locators")
    was = s.current_song_time
    yield from _goto(ctx, at)
    if (_cue_at(ctx, at) is not None) != want_present:
        s.set_or_delete_cue()
        yield
    yield from _goto(ctx, was)


@command
def set_cue(ctx, name, beat=None, bar=None):
    at = _t(ctx, beat, bar)
    c = _cue_at(ctx, at)
    if c is not None:
        c.name = name
        return {"name": name, "beat": at, "updated": True}
    yield from _toggle_cue_at(ctx, at, True)
    c = _cue_at(ctx, at)
    if c is None:
        raise RuntimeError("cue not created at beat %s" % at)
    c.name = name
    return {"name": name, "beat": at, "created": True}


@command
def delete_cue(ctx, name=None, beat=None, bar=None):
    at = _t(ctx, beat, bar) if (beat is not None or bar is not None) else None
    targets = [c.time for c in ctx.song.cue_points
               if (name is not None and c.name == name) or
                  (at is not None and abs(c.time - at) < 1e-3)]
    if not targets:
        raise ValueError("cue not found")
    for when in targets:
        yield from _toggle_cue_at(ctx, when, False)
    return {"deleted": targets}


@command
def clear_cues(ctx):
    times = [c.time for c in ctx.song.cue_points]
    for when in times:
        yield from _toggle_cue_at(ctx, when, False)
    return {"deleted": len(times)}


@command
def transport(ctx, action, beat=None, bar=None):
    s = ctx.song
    if beat is not None or bar is not None:
        if action in ("play", "locate"):
            s.stop_playing()
            yield
        yield from _goto(ctx, _t(ctx, beat, bar))
    if action == "play":
        s.start_playing()   # plays from the settled playhead (see record_master)
    elif action == "continue":
        s.continue_playing()
    elif action == "stop":
        s.stop_playing()
    elif action != "locate":
        raise ValueError("action: play | continue | stop | locate")
    return {"playing": s.is_playing, "time": s.current_song_time}


@command
def set_loop(ctx, on, start_bar=None, end_bar=None):
    s = ctx.song
    if start_bar is not None and end_bar is not None:
        a, b = _t(ctx, bar=start_bar), _t(ctx, bar=end_bar)
        s.loop_start = a
        s.loop_length = b - a
    s.loop = bool(on)
    return {"loop": s.loop, "start": s.loop_start, "length": s.loop_length}


# ======================================================================
# render: record the master bus into a new track via Resampling
# ======================================================================

@command
def record_master(ctx, start_bar, end_bar, name="Claude Render"):
    s = ctx.song
    job = ctx.record_job
    if job and job.get("state") in ("recording", "finalizing"):
        raise RuntimeError("a render is already running")
    a, b = _t(ctx, bar=start_bar), _t(ctx, bar=end_bar)

    saved = {"arm": [(t, t.arm) for t in s.tracks if t.can_be_armed],
             "metronome": s.metronome, "loop": s.loop, "record_mode": s.record_mode}
    for t, _ in saved["arm"]:
        t.arm = False

    s.create_audio_track(-1)
    rt = s.tracks[len(s.tracks) - 1]
    rt.name = name
    routes = list(rt.available_input_routing_types)
    res = [r for r in routes if "resampl" in r.display_name.lower()]
    if not res:
        raise RuntimeError("Resampling input not available: %s"
                           % [r.display_name for r in routes])
    rt.input_routing_type = res[0]
    rt.current_monitoring_state = 2   # Off: no feedback loop into master
    rt.arm = True

    s.metronome = False
    s.loop = False
    if s.is_playing:
        s.stop_playing()
        yield
    yield from _goto(ctx, a)
    s.record_mode = True
    # Measured on Live 12.4: after the playhead settles, start_playing() starts from it.
    # continue_playing() ignores a moved playhead and resumes where playback stopped.
    s.start_playing()
    ctx.record_job = {"state": "recording", "start": a, "end": b, "track": rt,
                      "saved": saved, "name": name, "ticks": 0,
                      "seconds": (b - a) * 60.0 / s.tempo}
    return {"state": "recording", "start_beat": a, "end_beat": b,
            "expected_seconds": round((b - a) * 60.0 / s.tempo, 1)}


def _finish_record(ctx, job):
    s = ctx.song
    s.stop_playing()
    s.record_mode = False
    job["track"].arm = False
    sv = job["saved"]
    for t, was in sv["arm"]:
        try:
            t.arm = was
        except Exception:
            pass
    s.metronome = sv["metronome"]
    s.loop = sv["loop"]
    job["state"] = "finalizing"
    job["ticks"] = 0


@command
def record_status(ctx):
    job = ctx.record_job
    if not job:
        return {"state": "idle"}
    out = {k: job[k] for k in ("state", "start", "end", "name")}
    out["now"] = ctx.song.current_song_time
    if job.get("file"):
        out["file"] = job["file"]
    if job.get("error"):
        out["error"] = job["error"]
    return out


@command
def record_abort(ctx):
    job = ctx.record_job
    if job and job["state"] == "recording":
        _finish_record(ctx, job)
        job["state"] = "aborted"
    return record_status(ctx)


def tick(ctx):
    """Called ~10x/s on the main thread by the control surface."""
    for pending in list(ctx.pending):
        _advance(ctx, pending)
    job = ctx.record_job
    if not job:
        return
    s = ctx.song
    if job["state"] == "recording":
        job["ticks"] += 1
        # start_playing() is asynchronous: is_playing stays False for a few ticks, and
        # a count-in can hold the playhead before `start`. Only treat "stopped" as the
        # user stopping once playback has demonstrably begun.
        now = s.current_song_time
        if not job.get("started") and s.is_playing and now > job["end"]:
            _finish_record(ctx, job)
            job["error"] = ("playback started at beat %.2f, outside the render range "
                            "%.2f-%.2f" % (now, job["start"], job["end"]))
            return
        if s.is_playing and now > job["start"] + 0.01:
            job["started"] = True
        if now >= job["end"]:
            _finish_record(ctx, job)
        elif job.get("started") and not s.is_playing:
            _finish_record(ctx, job)
        elif not job.get("started") and job["ticks"] > 150:
            _finish_record(ctx, job)
            job["error"] = "playback never started"
    elif job["state"] == "finalizing":
        job["ticks"] += 1
        clips = list(job["track"].arrangement_clips)
        if clips and clips[0].file_path:
            job["file"] = clips[0].file_path
            job["state"] = "error" if job.get("error") else "done"
        elif job["ticks"] > 100:
            job["state"] = "error"
            job.setdefault("error", "recording finished but no clip appeared")

