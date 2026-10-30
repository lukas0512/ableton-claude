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

VERSION = "0.8.0"

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


# While Live records (a render), every parameter or mixer change is written into the
# Arrangement as automation that later plays back on its own: on Murder pista toggling the
# master limiters during a render left them switching off for 4 bars, a reverb decay of
# 60 s and the bass fader riding 5 dB. These commands are refused until the render ends.
_MUTATING = ("set_", "add_notes", "create_", "delete_", "load_device", "move_device",
             "copy_device", "duplicate_", "fill_range", "shift_clips", "trim_clip",
             "mute_clips_in_range", "clip_envelope", "clear_cues")
_SAFE_WHILE_RECORDING = ("set_cue",)


def _run(ctx, cmd, args):
    fn = COMMANDS.get(cmd)
    if fn is None:
        raise LookupError("unknown command: %s" % cmd)
    if (cmd.startswith(_MUTATING) and cmd not in _SAFE_WHILE_RECORDING
            and getattr(ctx.song, "record_mode", False)):
        raise RuntimeError("Live is recording (a render): %s would be written into the "
                           "Arrangement as automation. Wait for the render to finish." % cmd)
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
    exact = [t for t in s.tracks if t.name == spec]
    if len(exact) == 1:
        return exact[0]
    if exact:
        # Three tracks named "CLOSED/OPENHH": by name, every edit landed on the first one.
        raise ValueError("%d tracks are named %r: address them by index %s"
                         % (len(exact), spec, [i for i, t in enumerate(s.tracks) if t.name == spec]))
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
    """Device by index, exact name, "Name#k" (k-th of several with that name, 0-based)
    or a unique name fragment."""
    devs = list(track.devices)
    if isinstance(spec, int):
        return devs[spec]
    if "#" in spec and spec.rsplit("#", 1)[1].isdigit():
        name, k = spec.rsplit("#", 1)
        same = [d for d in devs if d.name == name]
        if int(k) < len(same):
            return same[int(k)]
        raise ValueError("only %d devices named %r on %s" % (len(same), name, track.name))
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
    param.value = _raw_for_display(param, target)


_UNIT_RE = re.compile(r"([-+]?(?:\d+(?:\.\d+)?|\.\d+))\s*(khz|hz|ms|s|db|%)?", re.I)   # Glue shows '.6'
_UNIT_SCALE = {"khz": 1000.0, "hz": 1.0, "ms": 0.001, "s": 1.0}


def _to_base(text):
    """'1.50 kHz' -> 1500.0, '250 ms' -> 0.25, '2.2 s' -> 2.2, '-3 dB' -> -3.0.
    Live switches units inside one parameter (ms below a second, s above), so every
    comparison happens in base units (Hz, seconds)."""
    t = str(text).replace("\u2212", "-").strip()
    if "inf" in t:
        return float("-inf") if t.startswith("-") else float("inf")
    m = _UNIT_RE.search(t)
    if not m:
        return None
    return float(m.group(1)) * _UNIT_SCALE.get((m.group(2) or "").lower(), 1.0)


def _raw_for_display(param, target):
    """Raw value whose display reads `target`. A bare number is taken in base units
    (Hz, seconds, dB, %); a string may carry its unit: "22 ms", "2.2 s", "1.2 kHz"."""
    lo, hi = param.min, param.max
    goal = _to_base(target) if isinstance(target, str) else float(target)

    def num(v):
        x = _to_base(param.str_for_value(v))
        return float("-inf") if x is None else x

    # the numeric stretch of the range: a Glue release ends in 'Auto', a filter in 'Off'
    probe = [(lo + (hi - lo) * k / 16.0) for k in range(17)]
    finite = [(v, num(v)) for v in probe if num(v) not in (float("inf"), float("-inf"))]
    if len(finite) >= 2:
        lo, hi = finite[0][0], finite[-1][0]
        increasing = finite[-1][1] >= finite[0][1]
    else:
        increasing = num(hi) >= num(lo)
    for _ in range(48):
        mid = (lo + hi) / 2.0
        if (num(mid) < goal) == increasing:
            lo = mid
        else:
            hi = mid
    # the side whose display has reached the goal ('7.9 dB', not the '7.8 dB' just under it)
    return hi if increasing else lo


def _param_info(p):
    d = {"name": p.name, "value": round(p.value, 5), "min": p.min, "max": p.max,
         "display": p.str_for_value(p.value), "quantized": p.is_quantized}
    if p.is_quantized:
        d["items"] = list(p.value_items)
    return d


def _track_kind(t):
    if getattr(t, "is_foldable", False):
        return "group"
    if t.has_midi_input:
        return "midi"
    return "audio"


WARP_MODES = {"beats": 0, "tones": 1, "texture": 2, "repitch": 3, "re-pitch": 3, "complex": 4,
              "rex": 5, "complex_pro": 6, "complex pro": 6}


def _warp_mode(mode):
    if isinstance(mode, int):
        return mode
    key = str(mode).strip().lower()
    if key not in WARP_MODES:
        raise ValueError("warp_mode must be one of %s" % sorted(WARP_MODES))
    return WARP_MODES[key]


def _shape_audio(c, warp=None, warp_mode=None, pitch=None, detune=None):
    """Warp first: Live ignores the warp mode and detune of an unwarped clip."""
    if warp is not None:
        c.warping = bool(warp)
    if warp_mode is not None:
        c.warp_mode = _warp_mode(warp_mode)
    if pitch is not None:
        c.pitch_coarse = int(pitch)
    if detune is not None:
        c.pitch_fine = max(-50.0, min(49.0, float(detune)))


def _clip_info(c, markers=False):
    d = {"name": c.name, "start": round(c.start_time, 4), "end": round(c.end_time, 4),
         "length": round(c.length, 4), "muted": c.muted,
         "type": "audio" if c.is_audio_clip else "midi"}
    g = getattr(c, "groove", None)
    if g is not None:
        d["groove"] = g.name
    if markers:
        d.update({"looping": c.looping, "loop_start": c.loop_start, "loop_end": c.loop_end,
                  "start_marker": c.start_marker, "end_marker": c.end_marker})
    if c.is_audio_clip:
        d["file"] = c.file_path
        d["warping"] = c.warping
        d["warp_mode"] = c.warp_mode
        d["pitch"] = c.pitch_coarse
        d["detune"] = round(c.pitch_fine, 1)
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
def get_track(ctx, track, clips=True, max_clips=200, markers=False):
    t = _track(ctx, track)
    d = {"name": t.name, "kind": _track_kind(t),
         "vol_db": _db_of(t.mixer_device.volume),
         "pan": t.mixer_device.panning.value,
         "mute": t.mute if t != ctx.song.master_track else False,
         "sends_db": [_db_of(sd) for sd in t.mixer_device.sends],
         "devices": [{"i": i, "name": dv.name, "class": dv.class_name,
                      "on": dv.parameters[0].value > 0 if len(dv.parameters) else None}
                     for i, dv in enumerate(t.devices)]}
    # group tracks raise RuntimeError (not AttributeError) on arrangement_clips
    if clips and not getattr(t, "is_foldable", False) and t != ctx.song.master_track \
            and t not in ctx.song.return_tracks:
        cl = _arr_clips(t)
        d["n_clips"] = len(cl)
        d["clips"] = [dict(_clip_info(c, markers), i=i) for i, c in enumerate(cl[:max_clips])]
    return d


@command
def get_device(ctx, track, device):
    dv = _device(_track(ctx, track), device)
    return {"name": dv.name, "class": dv.class_name,
            "params": [dict(_param_info(p), i=i) for i, p in enumerate(dv.parameters)]}


@command
def api_methods(ctx, track="master", device=None, param=None):
    """Introspection: the automation-related members Live exposes on a track, a device
    parameter (or the mixer volume) and the song, to find what the API allows."""
    t = _track(ctx, track)
    p = t.mixer_device.volume if device is None else _param(_device(t, device), param)
    pick = lambda o: sorted(n for n in dir(o) if "autom" in n.lower() or "envelope" in n.lower()
                            or "clear" in n.lower())
    return {"track": pick(t), "param": pick(p), "song": pick(ctx.song)}


@command
def automated_params(ctx):
    """Every parameter in the set that carries Arrangement automation (automation_state 1 =
    playing, 2 = overridden by a manual move): mixer volume/pan/sends and every device
    parameter on every track, return and the master. Arrangement automation is invisible
    to get_track/get_device values and to clip envelopes; a level ride hidden in a bus
    or master device shows up here."""
    s = ctx.song
    tracks = [(t.name, t) for t in s.tracks] + \
             [("return:" + t.name, t) for t in s.return_tracks] + [("master", s.master_track)]
    out = []
    for name, t in tracks:
        m = t.mixer_device
        params = [("mixer", "volume", m.volume), ("mixer", "pan", m.panning)]
        params += [("mixer", "send:%d" % i, p) for i, p in enumerate(m.sends)]
        for d in t.devices:
            params += [(d.name, p.name, p) for p in d.parameters]
        for owner, pname, p in params:
            st = getattr(p, "automation_state", 0)
            if st:
                out.append({"track": name, "device": owner, "param": pname,
                            "state": {1: "playing", 2: "overridden"}.get(st, st),
                            "now": p.str_for_value(p.value)})
    return out


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
    before = {"bpm": ctx.song.tempo}
    ctx.song.tempo = float(bpm)
    return {"tempo": ctx.song.tempo, "before": before}


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
def create_return(ctx, name=None):
    """Add a return track (its send appears on every track at the next index)."""
    s = ctx.song
    s.create_return_track()
    r = s.return_tracks[len(s.return_tracks) - 1]
    if name:
        r.name = name
    return {"return_index": len(s.return_tracks) - 1, "name": r.name}


@command
def delete_track(ctx, track):
    t = _track(ctx, track)
    s = ctx.song
    for k, r in enumerate(s.return_tracks):
        if r == t:
            s.delete_return_track(k)
            return {"deleted_return": k}
    i = _track_index(ctx, t)
    s.delete_track(i)
    return {"deleted": i}


@command
def set_track(ctx, track, name=None, volume_db=None, pan=None, mute=None, solo=None,
              arm=None, monitoring=None, color_index=None):
    t = _track(ctx, track)
    m = t.mixer_device
    before = {}
    for key, arg, read in (("name", name, lambda: t.name),
                           ("volume_raw", volume_db, lambda: m.volume.value),
                           ("pan_raw", pan, lambda: m.panning.value),
                           ("mute", mute, lambda: t.mute), ("solo", solo, lambda: t.solo),
                           ("arm", arm, lambda: t.arm if t.can_be_armed else None),
                           ("monitoring", monitoring,
                            lambda: ["in", "auto", "off"][t.current_monitoring_state]),
                           ("color_index", color_index, lambda: t.color_index)):
        if arg is not None:
            try:
                before[key] = read()
            except Exception:
                pass
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
            "pan": t.mixer_device.panning.value, "mute": t.mute, "before": before}


@command
def set_send(ctx, track, send, db):
    t = _track(ctx, track)
    p = t.mixer_device.sends[int(send)]
    before = {"raw": p.value}
    _set_db(p, float(db))
    return {"send": send, "db": _db_of(p), "before": before}


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
              "points": [[beat_from_clip_start, value], ...], "unit": "raw"|"db",
              "resolution": beats per step (default 0.25; a stab gate needs ~1/64)}
    Linear ramps between points, drawn as steps of `resolution` beats."""
    resolution = float(spec.get("resolution", resolution))
    device = spec.get("device")
    pname = spec.get("param", "volume")
    p = _mixer_param(track, pname) if device is None else _param(_device(track, device), pname)
    unit = spec.get("unit", "raw")
    if unit == "db":
        to_raw = lambda v: _raw_for_db(p, v)
    elif unit == "display":
        to_raw = lambda v: _raw_for_display(p, v)
    else:
        to_raw = float
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


@command
def read_clip_envelopes(ctx, track, clip, samples=16):
    """Which parameters a clip automates and their values across the clip: the mixer
    (volume, pan, sends) and every device parameter with a clip envelope, each sampled at
    `samples` evenly spaced points (beats from the clip start, display strings). Live 12's
    API returns no envelope for Arrangement clips (measured 2026-10-22: an Arrangement clip
    with a drawn filter envelope read empty): this works on Session clips only. For
    Arrangement automation use automated_params."""
    t = _track(ctx, track)
    c = _clip(t, clip)
    offset = c.loop_start if c.looping else c.start_marker
    length = c.end_time - c.start_time
    n = max(2, min(int(samples), 64))
    times = [length * i / (n - 1) for i in range(n)]
    candidates = [("mixer", "volume", t.mixer_device.volume),
                  ("mixer", "pan", t.mixer_device.panning)]
    candidates += [("mixer", "send:%d" % i, s) for i, s in enumerate(t.mixer_device.sends)]
    for d in t.devices:
        candidates += [(d.name, p.name, p) for p in d.parameters]
    out = []
    for owner, name, p in candidates:
        env = c.automation_envelope(p)
        if env is None:
            continue
        vals = []
        for x in times:
            v = env.value_at_time(offset + x)
            vals.append([round(x, 3), p.str_for_value(v)])
        out.append({"device": owner, "param": name, "values": vals})
    return {"clip": c.name, "start": c.start_time, "length": length, "envelopes": out}


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


def _envelope_check(c, envelopes):
    """Live 12.4 drops a Session clip's envelopes when it copies the clip into the
    Arrangement: say so instead of returning a clip that silently does nothing."""
    if envelopes and not getattr(c, "has_envelopes", True):
        return {"envelopes_lost": True,
                "warning": "Live dropped the clip envelopes on the copy to the Arrangement; "
                           "use velocity, a separate track with fixed settings, or clips "
                           "per stage instead"}
    return {}


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
                n_envelopes=len(envelopes or []), **_envelope_check(c, envelopes))


@command
def add_notes(ctx, track, clip, notes, replace=False):
    c = _clip(_track(ctx, track), clip)
    if replace:
        c.remove_notes_extended(0, 128, -1e6, 2e6)
    c.add_new_notes(_note_specs(notes))
    return {"clip": c.name, "added": len(notes)}


@command
def create_audio_clip(ctx, track, path, beat=None, bar=None, name=None, warp=None,
                      gain_db=None, pitch=None, length=None, envelopes=None, warp_mode=None,
                      detune=None, beats=None):
    """`beats` pins the whole file to that many beats (auto-warp guessed 1.14 beats for a
    33-beat recording); `length` loops the clip and sets its length in beats."""
    t = _track(ctx, track)
    start = _t(ctx, beat, bar)

    def shape(c):
        if name:
            c.name = name
        _shape_audio(c, warp, warp_mode, pitch, detune)
        if beats is not None:
            _pin_warp(c, float(beats))
        if gain_db is not None:
            _set_clip_gain_db(c, float(gain_db))
        if length is not None:
            c.looping = True
            c.loop_start = 0.0
            c.loop_end = float(length)
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
    return dict(_clip_info(c), method=method, n_envelopes=len(envelopes or []),
                **_envelope_check(c, envelopes))


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
             looping=None, loop_start=None, loop_end=None, warping=None,
             start_marker=None, end_marker=None, warp_mode=None, detune=None):
    c = _clip(_track(ctx, track), clip)
    before = {}
    for key, arg, attr in (("start_marker", start_marker, "start_marker"),
                           ("end_marker", end_marker, "end_marker"), ("name", name, "name"),
                           ("muted", muted, "muted"), ("looping", looping, "looping"),
                           ("loop_start", loop_start, "loop_start"),
                           ("loop_end", loop_end, "loop_end"), ("pitch", pitch, "pitch_coarse"),
                           ("warping", warping, "warping"), ("warp_mode", warp_mode, "warp_mode"),
                           ("detune", detune, "pitch_fine")):
        if arg is not None and hasattr(c, attr):
            before[key] = getattr(c, attr)
    if gain_db is not None:
        before["gain_raw"] = c.gain
    if start_marker is not None:
        c.start_marker = float(start_marker)
    if end_marker is not None:
        c.end_marker = float(end_marker)
    if name is not None:
        c.name = name
    if muted is not None:
        c.muted = bool(muted)
    if gain_db is not None:
        _set_clip_gain_db(c, float(gain_db))
    if looping is not None:
        c.looping = bool(looping)
    if loop_start is not None:
        c.loop_start = float(loop_start)
    if loop_end is not None:
        c.loop_end = float(loop_end)
    if c.is_audio_clip:
        _shape_audio(c, warping, warp_mode, pitch, detune)
    elif pitch is not None:
        c.pitch_coarse = int(pitch)
    return dict(_clip_info(c, markers=True), before=before)


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
def delete_clips_in_range(ctx, track, start_bar, end_bar):
    """Delete every arrangement clip that starts in [start_bar, end_bar)."""
    t = _track(ctx, track)
    a, b = _t(ctx, bar=start_bar), _t(ctx, bar=end_bar)

    def in_range():
        return [c for c in t.arrangement_clips if a - 1e-3 <= c.start_time < b - 1e-3]

    # Delete from a snapshot, then re-check: a few passes cover handles invalidated by
    # overlapping clips, and a pass without progress stops (Live silently ignores
    # delete_clip on some malformed clips; retrying those forever froze Live once).
    deleted = 0
    remaining = in_range()
    for _ in range(4):
        if not remaining:
            break
        for c in remaining:
            try:
                t.delete_clip(c)
            except Exception:
                pass
        now = in_range()
        if len(now) >= len(remaining):
            break
        deleted += len(remaining) - len(now)
        remaining = now
    return {"track": t.name, "deleted": deleted, "left_in_range": len(remaining),
            "stuck": [round(c.start_time, 3) for c in remaining[:20]]}


PARK = 1.0e6      # beats: far beyond any song, where clips wait while a trim runs


def _trim_at(t, cut):
    """Shorten every clip that crosses `cut` so it ends there. Live has no API for a
    clip's length, but a clip dropped on top of another truncates it: drop a copy at
    `cut`, then delete the copy. Clips that start inside the copy's span would be eaten
    by it, so they are parked far away first and brought back after."""
    n = 0
    for _ in range(64):
        crossing = [c for c in t.arrangement_clips
                    if c.start_time < cut - 1e-3 and c.end_time > cut + 1e-3]
        if not crossing:
            break
        c = crossing[0]
        span = c.end_time - c.start_time
        parked = []
        for other in list(t.arrangement_clips):
            if cut - 1e-3 <= other.start_time < cut + span + 1e-3:
                offset = other.start_time - cut
                t.duplicate_clip_to_arrangement(other, PARK + offset)
                t.delete_clip(other)
                parked.append(offset)
        t.duplicate_clip_to_arrangement(c, cut)
        blocker = next((x for x in t.arrangement_clips if abs(x.start_time - cut) < 1e-3),
                       None)
        if blocker is not None:
            t.delete_clip(blocker)
        for offset in sorted(parked):
            p = next((x for x in t.arrangement_clips if abs(x.start_time - (PARK + offset)) < 1e-3), None)
            if p is not None:
                t.duplicate_clip_to_arrangement(p, cut + offset)
                t.delete_clip(p)
        n += 1
    return n


@command
def trim_clip(ctx, track, clip, end_bar=None, end_beat=None):
    """End an arrangement clip at end_bar/end_beat (see _trim_at for the caveat)."""
    t = _track(ctx, track)
    c = _clip(t, clip)
    start = c.start_time
    cut = _t(ctx, end_beat, end_bar)
    if not (c.start_time < cut < c.end_time):
        raise ValueError("cut %.3f is not inside the clip %.3f-%.3f"
                         % (cut, c.start_time, c.end_time))
    _trim_at(t, cut)
    return _clip_info(_clip(t, {"at": start}), markers=False)


def _device_inputs(d):
    if not hasattr(d, "available_input_routing_types"):
        raise ValueError("%s has no sidechain input" % d.name)
    return {"types": [r.display_name for r in d.available_input_routing_types],
            "channels": [r.display_name for r in d.available_input_routing_channels],
            "type": d.input_routing_type.display_name if d.input_routing_type else None,
            "channel": d.input_routing_channel.display_name if d.input_routing_channel else None}


def _pick(options, name, what):
    m = [r for r in options if r.display_name == name] or \
        [r for r in options if name.lower() in r.display_name.lower()]
    if not m:
        raise ValueError("no %s %r; choices: %s" % (what, name, [r.display_name for r in options]))
    return m[0]


@command
def track_routing(ctx, track):
    t = _track(ctx, track)
    return {"output": t.output_routing_type.display_name,
            "output_channel": t.output_routing_channel.display_name if t.output_routing_channel else None,
            "outputs": [r.display_name for r in t.available_output_routing_types],
            "input": t.input_routing_type.display_name if hasattr(t, "input_routing_type") and t.input_routing_type else None}


@command
def set_track_input(ctx, track, source, channel=None):
    """A track's input: "No Input" for a bus (a fresh audio track listens to Ext. In, the
    interface's mic, and monitoring "in" then feeds it back), a track name, "Ext. In"."""
    t = _track(ctx, track)
    t.input_routing_type = _pick(list(t.available_input_routing_types), source, "input")
    if channel is not None:
        t.input_routing_channel = _pick(list(t.available_input_routing_channels), channel, "channel")
    return track_routing(ctx, track)


@command
def set_track_output(ctx, track, dest, channel=None):
    """Send a track's output to another track (a bus: Live's API makes no group tracks),
    to "Main" or to "Sends Only". The bus must monitor "in" (set_track monitoring=in)."""
    t = _track(ctx, track)
    t.output_routing_type = _pick(list(t.available_output_routing_types), dest, "output")
    if channel is not None:
        t.output_routing_channel = _pick(list(t.available_output_routing_channels), channel, "channel")
    return track_routing(ctx, track)


@command
def device_inputs(ctx, track, device):
    """A device's sidechain input choices (Compressor, Gate, Auto Filter...)."""
    return _device_inputs(_device(_track(ctx, track), device))


@command
def set_device_input(ctx, track, device, source, channel=None):
    """Route a device's sidechain input: `source` is a track name as the chooser shows
    it (e.g. "Kick"), `channel` one of its channels ("Post FX", "Post Mixer", "Pre FX")."""
    d = _device(_track(ctx, track), device)
    info = _device_inputs(d)
    types = list(d.available_input_routing_types)
    match = [r for r in types if r.display_name == source] or \
            [r for r in types if source.lower() in r.display_name.lower()]
    if not match:
        raise ValueError("no input %r; choices: %s" % (source, info["types"]))
    d.input_routing_type = match[0]
    if channel is not None:
        chans = list(d.available_input_routing_channels)
        cm = [r for r in chans if r.display_name == channel] or \
             [r for r in chans if channel.lower() in r.display_name.lower()]
        if not cm:
            raise ValueError("no channel %r; choices: %s" % (channel, [r.display_name for r in chans]))
        d.input_routing_channel = cm[0]
    # Routing alone leaves Compressor's sidechain switched off: it listened and never reacted.
    for p in d.parameters:
        if p.name == "S/C On" and p.value < 0.5:
            p.value = 1.0
    return _device_inputs(d)


@command
def fill_range(ctx, track, src_start_bar, src_end_bar, start_bar, end_bar):
    """Repeat the phrase of clips starting in [src_start_bar, src_end_bar) across
    [start_bar, end_bar), cutting whatever overhangs end_bar. Build each track from left
    to right: the cut assumes nothing sits after end_bar yet."""
    t = _track(ctx, track)
    sa, sb = _t(ctx, bar=src_start_bar), _t(ctx, bar=src_end_bar)
    a, b = _t(ctx, bar=start_bar), _t(ctx, bar=end_bar)
    period = sb - sa
    src = [(c, c.start_time - sa) for c in _arr_clips(t)
           if sa - 1e-3 <= c.start_time < sb - 1e-3 and not c.muted]
    if not src:
        raise ValueError("no active clips in source bars %s-%s on %s"
                         % (src_start_bar, src_end_bar, t.name))
    placed = 0
    pos = a
    while pos < b - 1e-3:
        for c, off in src:
            if pos + off < b - 1e-3:
                t.duplicate_clip_to_arrangement(c, pos + off)
                placed += 1
        pos += period
    trimmed = _trim_at(t, b)
    return {"track": t.name, "placed": placed, "trimmed": trimmed}


@command
def duplicate_range(ctx, track, start_bar, end_bar, dest_bar, active_only=True):
    """Copy every arrangement clip starting in [start_bar, end_bar) so the range begins
    at dest_bar, keeping each clip's offset. Uses Live's own duplication, so clip
    positions, warp and sample offsets stay consistent."""
    t = _track(ctx, track)
    a, b = _t(ctx, bar=start_bar), _t(ctx, bar=end_bar)
    shift = _t(ctx, bar=dest_bar) - a
    src = [c for c in _arr_clips(t) if a - 1e-3 <= c.start_time < b - 1e-3
           and not (active_only and c.muted)]
    for c in src:
        t.duplicate_clip_to_arrangement(c, c.start_time + shift)
    return {"track": t.name, "copied": len(src), "shift_beats": shift}


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
def shift_clips(ctx, track, from_bar, bars):
    """Move every Arrangement clip starting at or after `from_bar` by `bars` (negative =
    earlier), keeping clip envelopes, mutes and warping. Two phases through a scratch area
    past the song end, so a moved clip never lands on one that has not moved yet. Clear the
    destination first when moving earlier: what lies there is overwritten by Live."""
    t = _track(ctx, track)
    bpb = _beats_per_bar(ctx)
    a = _t(ctx, bar=from_bar)
    d = float(bars) * bpb
    clips = sorted((c for c in t.arrangement_clips if c.start_time >= a - 1e-6),
                   key=lambda c: c.start_time)
    if not clips:
        return {"track": t.name, "moved": 0}
    end = max(c.end_time for c in t.arrangement_clips)
    scratch = (int(end / bpb) + 64) * bpb - clips[0].start_time    # well past the song
    staged = []
    for c in clips:
        target = c.start_time + d
        at = c.start_time + scratch
        t.duplicate_clip_to_arrangement(c, at)
        # Find the copy by position: comparing Live's clip objects with `in` picked wrong
        # clips and left 1-bar strays of other clips around the song.
        new = [x for x in t.arrangement_clips if abs(x.start_time - at) < 1e-4]
        t.delete_clip(c)
        if new:
            staged.append((new[0], target))
    moved = 0
    for c, target in staged:
        t.duplicate_clip_to_arrangement(c, target)
        t.delete_clip(c)
        moved += 1
    return {"track": t.name, "moved": moved, "shift_beats": d}


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


def _unfold_groups(t):
    g = getattr(t, "group_track", None)
    while g is not None:
        if getattr(g, "fold_state", 0):
            g.fold_state = 0
        g = getattr(g, "group_track", None)


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
    _unfold_groups(t)       # Live refuses to select a track inside a folded group
    ctx.song.view.selected_track = t
    if ctx.song.view.selected_track != t:
        raise RuntimeError("could not select %s to load onto it" % t.name)
    n = len(t.devices)
    ctx.app.browser.load_item(item)
    # Live finishes a load over the next ticks and applies the device's default preset
    # then: parameters set right after load_item were reset to defaults (seen on Reverb
    # and EQ Eight). Wait until the device list has settled before returning.
    last, stable = None, 0
    for _ in range(20):
        yield
        names = [d.name for d in t.devices]
        stable = stable + 1 if names == last else 0
        last = names
        if stable >= 2:
            break
    return {"loaded": path, "devices": [d.name for d in t.devices], "added": len(t.devices) - n}


@command
def set_param(ctx, track, device, param, value=None, display=None, db=None, item=None):
    """Set a device parameter by raw value, by display number (e.g. 150 for '150 Hz'),
    by dB, or by the name of a list option (item="Low Shelf")."""
    p = _param(_device(_track(ctx, track), device), param)
    before = {"value": p.value, "display": p.str_for_value(p.value)}
    if item is not None:
        items = list(p.value_items)
        if item not in items:
            raise ValueError("%r is not an option of %s: %s" % (item, p.name, items))
        p.value = float(items.index(item))
    elif db is not None:
        _set_db(p, float(db))
    elif display is not None:
        _set_by_display(p, display)
    else:
        p.value = max(p.min, min(p.max, float(value)))
    return dict(_param_info(p), before=before)


# Device state that is not a parameter (Wavetable's tables, voicing). Category before index.
_DEVICE_PROPS = ("oscillator_1_wavetable_category", "oscillator_1_wavetable_index",
                 "oscillator_2_wavetable_category", "oscillator_2_wavetable_index",
                 "oscillator_1_effect_mode", "oscillator_2_effect_mode", "filter_routing",
                 "mono_poly", "poly_voices", "unison_mode", "unison_voice_count")


@command
def copy_device(ctx, src_track, src_device, track, device):
    """Copy every parameter (by name) and Wavetable's table/voice settings from one device
    to another of the same class, e.g. to clone a frozen track's synth patch."""
    s = _device(_track(ctx, src_track), src_device)
    d = _device(_track(ctx, track), device)
    if s.class_name != d.class_name:
        raise ValueError("%s is %s, %s is %s" % (s.name, s.class_name, d.name, d.class_name))
    props = []
    for a in _DEVICE_PROPS:
        if hasattr(s, a) and hasattr(d, a):
            try:
                setattr(d, a, getattr(s, a))
                props.append(a)
            except Exception:
                pass
    by_name = {p.name: p for p in d.parameters}
    copied, skipped = 0, []
    for p in s.parameters:
        q = by_name.get(p.name)
        if q is None or not q.is_enabled:
            skipped.append(p.name)
            continue
        q.value = max(q.min, min(q.max, p.value))
        copied += 1
    return {"from": s.name, "to": d.name, "params": copied, "props": props,
            "skipped": skipped[:20]}


# EQ Eight: global_mode 0 Stereo, 1 L/R, 2 M/S. Simpler: playback_mode 0 Classic, 1 One-Shot.
_SETTABLE_PROPS = {"global_mode", "edit_mode", "oversample", "playback_mode"}


@command
def set_device_prop(ctx, track, device, prop, value):
    """Set a device property that is not a parameter, from a short whitelist (EQ Eight's
    global_mode for Mid/Side, edit_mode to edit channel B, oversample; Simpler's
    playback_mode for one-shot drums)."""
    if prop not in _SETTABLE_PROPS:
        raise ValueError("prop must be one of %s" % sorted(_SETTABLE_PROPS))
    d = _device(_track(ctx, track), device)
    if not hasattr(d, prop):
        raise ValueError("%s has no %s" % (d.name, prop))
    before = getattr(d, prop)
    setattr(d, prop, type(before)(value) if not isinstance(before, bool) else bool(value))
    return {"device": d.name, "prop": prop, "value": getattr(d, prop), "before": before}


@command
def set_device_on(ctx, track, device, on=True):
    dv = _device(_track(ctx, track), device)
    before = {"on": dv.parameters[0].value > 0.5}
    dv.parameters[0].value = 1.0 if on else 0.0
    return {"device": dv.name, "on": bool(on), "before": before}


@command
def set_raw(ctx, track, target, value, device=None):
    """Restore an exact raw value: target = "volume" | "pan" | "send:<n>" | a parameter
    of `device` | "clip_gain" with device=<clip spec>. Used to revert journaled changes."""
    t = _track(ctx, track)
    if target == "clip_gain":
        c = _clip(t, device)
        c.gain = float(value)
        return {"clip": c.name, "gain_db": _db_of_clip_gain(c)}
    if device is None:
        p = _mixer_param(t, target)
    else:
        p = _param(_device(t, device), target)
    p.value = max(p.min, min(p.max, float(value)))
    return _param_info(p)


MAX_UNDO = 50


@command
def undo(ctx, steps=1):
    """Live's own undo, `steps` times (at most 50). Live groups API changes into undo
    steps its own way: check the result with get_track/get_song after undoing."""
    s = ctx.song
    done = 0
    for _ in range(max(0, min(int(steps), MAX_UNDO))):
        if not s.can_undo:
            break
        s.undo()
        done += 1
    return {"undone": done, "can_undo": s.can_undo}


@command
def move_device(ctx, track, device, position):
    """Move a device to `position` in its track's chain (0 = first)."""
    t = _track(ctx, track)
    dv = _device(t, device)
    ctx.song.move_device(dv, t, int(position))
    return {"devices": [d.name for d in t.devices]}


@command
def delete_device(ctx, track, device):
    t = _track(ctx, track)
    dv = _device(t, device)
    idx = list(t.devices).index(dv)
    name = dv.name            # the handle is dead once the device is gone
    t.delete_device(idx)
    return {"deleted": name, "devices": [d.name for d in t.devices]}


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
    # start_playing() starts from the start marker (Song.start_time), which a click in
    # the arrangement moves and a playhead move does not always follow: a render once
    # began at bar 125 instead of 97. Move both.
    try:
        s.start_time = at
    except Exception:
        pass
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
    def resampling(rt):
        routes = list(rt.available_input_routing_types)
        res = [r for r in routes if "resampl" in r.display_name.lower()]
        if not res:
            raise RuntimeError("Resampling input not available: %s"
                               % [r.display_name for r in routes])
        rt.input_routing_type = res[0]
    return (yield from _start_record(ctx, start_bar, end_bar, [(name, None, resampling)]))


def _source_route(options, track_name):
    """The routing type that is track `track_name`: Live lists tracks by name, unnamed
    ones as '<n>-Audio'. Exact first, then '<n>-<name>'; never a fragment ("KICK" must
    not pick "KICK 2")."""
    m = [r for r in options if r.display_name == track_name] or \
        [r for r in options if r.display_name.split("-", 1)[-1] == track_name]
    if not m:
        raise ValueError("no input %r; choices: %s"
                         % (track_name, [r.display_name for r in options]))
    return m[0]


@command
def record_tracks(ctx, tracks, start_bar, end_bar, tap="Post Mixer", prefix="tap"):
    """Record several tracks' outputs at once, each into its own new audio track (input =
    that track, channel `tap`: "Post Mixer" includes its fader and pan, "Post FX" not).
    One real-time pass instead of soloing and rendering each in turn. Returns sends do
    not reach these taps. record_status lists the files per source when done."""
    names = [_track(ctx, t).name for t in tracks]
    if len(set(names)) != len(names):
        raise ValueError("tracks must be distinct: %s" % names)

    def tap_of(src):
        def setup(rt):
            rt.input_routing_type = _source_route(list(rt.available_input_routing_types), src)
            # the channel list keeps the old input's channels (Ext. In "1/2") for a few
            # ticks after the type changes
            for _ in range(30):
                yield
                names = [c.display_name for c in rt.available_input_routing_channels]
                if tap in names:
                    break
            rt.input_routing_channel = _pick(list(rt.available_input_routing_channels),
                                             tap, "channel")
        return setup
    specs = [(("%s %s" % (prefix, n))[:31], n, tap_of(n)) for n in names]
    return (yield from _start_record(ctx, start_bar, end_bar, specs))


def _start_record(ctx, start_bar, end_bar, specs):
    """specs = [(render track name, source name or None, setup(rt))]; setup may be a
    generator (input channels appear a tick after the input type is set)."""
    s = ctx.song
    job = ctx.record_job
    if job and job.get("state") in ("recording", "finalizing"):
        raise RuntimeError("a render is already running")
    a, b = _t(ctx, bar=start_bar), _t(ctx, bar=end_bar)

    saved = {"arm": [(t, t.arm) for t in s.tracks if t.can_be_armed],
             "metronome": s.metronome, "loop": s.loop, "record_mode": s.record_mode}
    for t, _ in saved["arm"]:
        t.arm = False

    made = []
    try:
        for name, src, setup in specs:
            s.create_audio_track(-1)
            rt = s.tracks[len(s.tracks) - 1]
            rt.name = name
            made.append((rt, src))
            step = setup(rt)
            if step is not None and hasattr(step, "send"):
                yield from step
            rt.current_monitoring_state = 2   # Off: no feedback loop into master
            rt.arm = True
    except Exception:
        for rt, _ in reversed(made):
            try:
                s.delete_track(list(s.tracks).index(rt))
            except Exception:
                pass
        for t, was in saved["arm"]:
            try:
                t.arm = was
            except Exception:
                pass
        raise

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
    ctx.record_job = {"state": "recording", "start": a, "end": b, "track": made[0][0],
                      "tracks": made, "saved": saved, "name": specs[0][0], "ticks": 0,
                      "seconds": (b - a) * 60.0 / s.tempo}
    return {"state": "recording", "start_beat": a, "end_beat": b,
            "tracks": [rt.name for rt, _ in made],
            "expected_seconds": round((b - a) * 60.0 / s.tempo, 1)}


def _finish_record(ctx, job):
    s = ctx.song
    s.stop_playing()
    s.record_mode = False
    for rt, _ in job.get("tracks") or [(job["track"], None)]:
        rt.arm = False
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
    if job.get("files"):
        out["files"] = job["files"]
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
        if not job.get("started") and s.is_playing and not job.get("first_now_checked"):
            job["first_now_checked"] = True
            # recording runs from wherever playback starts: starting anywhere but the
            # render start silently shifts or truncates the file, so refuse it
            if abs(now - job["start"]) > 1.0:
                _finish_record(ctx, job)
                job["error"] = ("playback started at beat %.2f instead of %.2f (start "
                                "marker at %.2f)" % (now, job["start"],
                                                     getattr(s, "start_time", -1)))
                return
        if s.is_playing and now > job["start"] + 0.01:
            job["started"] = True
        if now >= job["end"]:
            _finish_record(ctx, job)
        elif job.get("started") and not s.is_playing:
            _finish_record(ctx, job)
        elif not job.get("started") and job["ticks"] > 300:
            _finish_record(ctx, job)
            job["error"] = "playback never started"
        elif not job.get("started") and not s.is_playing and job["ticks"] % 30 == 0:
            # Live drops start_playing() while it is busy (seen right after re-warping
            # ~3000 clips for a new groove): ask again every ~3 s, up to ~30 s
            s.start_playing()
    elif job["state"] == "finalizing":
        job["ticks"] += 1
        files = {}
        for rt, src in job.get("tracks") or [(job["track"], None)]:
            clips = list(rt.arrangement_clips)
            if clips and clips[0].file_path:
                files[src or rt.name] = clips[0].file_path
        if len(files) == len(job.get("tracks") or [1]):
            job["file"] = list(files.values())[0]
            if job.get("tracks") and job["tracks"][0][1] is not None:
                job["files"] = files
            job["state"] = "error" if job.get("error") else "done"
        elif job["ticks"] > 100:
            job["state"] = "error"
            job.setdefault("error", "recording finished but no clip appeared")


# ======================================================================
# grooves (Live 11+: Song.groove_pool, Clip.groove)
# ======================================================================

def _groove_dict(g):
    return {"name": g.name, "timing": round(g.timing_amount, 1),
            "random": round(g.random_amount, 1), "velocity": round(g.velocity_amount, 1),
            "quantization": round(g.quantization_amount, 1)}


def _groove(ctx, name):
    for g in ctx.song.groove_pool.grooves:
        if g.name == name:
            return g
    raise ValueError("no groove %r in the pool; have %s"
                     % (name, [g.name for g in ctx.song.groove_pool.grooves]))


@command
def grooves(ctx):
    """The Groove Pool: each groove's amounts, and the Song's global groove amount.
    Grooves get into the pool from the browser (load_device with a .agr path)."""
    s = ctx.song
    return {"groove_amount": round(getattr(s, "groove_amount", 1.0), 3),
            "grooves": [_groove_dict(g) for g in s.groove_pool.grooves]}


@command
def set_groove(ctx, name, timing=None, random=None, velocity=None, quantization=None,
               groove_amount=None):
    """Edit one pool groove (amounts in %, as Live shows them) and optionally the
    Song's global groove amount (0-1.31, 1.0 = 100 %)."""
    g = _groove(ctx, name)
    if timing is not None:
        g.timing_amount = float(timing)
    if random is not None:
        g.random_amount = float(random)
    if velocity is not None:
        g.velocity_amount = float(velocity)
    if quantization is not None:
        g.quantization_amount = float(quantization)
    if groove_amount is not None:
        ctx.song.groove_amount = float(groove_amount)
    return dict(_groove_dict(g), groove_amount=round(ctx.song.groove_amount, 3))


@command
def apply_groove(ctx, track, groove=None, start_bar=None, end_bar=None):
    """Assign a pool groove (None clears) to every arrangement clip on `track` that
    overlaps [start_bar, end_bar) (all clips when no range). Audio clips only follow a
    groove while warped; unwarped ones are reported, not changed."""
    t = _track(ctx, track)
    g = _groove(ctx, groove) if groove else None
    a = _t(ctx, bar=start_bar) if start_bar is not None else -1e9
    b = _t(ctx, bar=end_bar) if end_bar is not None else 1e9
    done, unwarped = 0, []
    for c in _arr_clips(t):
        if not (c.start_time < b - 1e-3 and c.end_time > a + 1e-3):
            continue
        if c.is_audio_clip and not c.warping:
            unwarped.append(round(c.start_time, 2))
            continue
        if g is None:
            if getattr(c, "has_groove", False):
                try:
                    del c.groove      # Live refuses None; older versions support delete
                except AttributeError:
                    # Live 12.4 has no deleter and still refuses None: no API clears it
                    raise ValueError("this Live version cannot clear a clip's groove "
                                     "through the API; neutralise it instead with "
                                     "set_groove(name, timing=0, random=0, velocity=0)")
        else:
            c.groove = g
        done += 1
    out = {"track": t.name, "clips": done, "groove": groove, "unwarped_skipped": unwarped}
    if groove and getattr(ctx.song, "groove_amount", 1.0) == 0:
        out["warning"] = ("the Song's Global Groove Amount is 0 %: grooves do nothing until "
                          "set_groove(name, groove_amount=1.0)")
    return out


@command
def transport_state(ctx):
    """Everything that decides where playback and recording start and stop."""
    s = ctx.song
    out = {}
    for k in ("is_playing", "current_song_time", "loop", "loop_start", "loop_length",
              "punch_in", "punch_out", "record_mode", "arrangement_overdub", "session_record",
              "metronome", "count_in_duration", "is_counting_in", "back_to_arranger",
              "start_time", "tempo", "re_enable_automation_enabled", "midi_recording_quantization"):
        if hasattr(s, k):
            v = getattr(s, k)
            out[k] = v if isinstance(v, (bool, int, float, str)) or v is None else str(v)
    return out


@command
def drum_pads(ctx, track):
    """The notes of the track's Drum Rack pads that hold a sound (a note elsewhere is
    silent: the 909 ride and tom once played pitch 60, an empty pad, for twenty versions)."""
    t = _track(ctx, track)
    for d in t.devices:
        if getattr(d, "can_have_drum_pads", False):
            return {"device": d.name,
                    "pads": sorted(p.note for p in d.drum_pads if len(p.chains))}
    return {"device": None, "pads": []}


@command
def re_enable_automation(ctx):
    """Live's Re-Enable Automation: setting a mixer value that a clip envelope drives
    (set_track volume on a clip with a volume ramp) overrides that envelope until this."""
    s = ctx.song
    if getattr(s, "re_enable_automation_enabled", False):
        s.re_enable_automation()
    return {"re_enable_automation_enabled": bool(getattr(s, "re_enable_automation_enabled", False))}


def _warp_info(c):
    return {"warping": c.warping, "sample_s": c.sample_length / float(c.sample_rate or 1),
            "markers": [{"beat": round(m.beat_time, 4), "sample_s": round(m.sample_time, 5)}
                        for m in c.warp_markers]}


@command
def warp_markers(ctx, track, clip):
    return _warp_info(_clip(_track(ctx, track), clip))


@command
def set_warp_markers(ctx, track, clip, markers=None, beats=None):
    """Replace a clip's warp markers. `markers` = [[beat, seconds], ...]; or `beats` alone
    pins the whole file to that many beats (a loop of known length: exact tempo, no
    auto-warp guess). Live keeps a marker at 0, so that one is moved, not removed."""
    c = _clip(_track(ctx, track), clip)
    if not c.is_audio_clip:
        raise ValueError("warp markers belong to audio clips")
    if beats is not None:
        markers = [[0.0, 0.0], [float(beats), _sample_seconds(c)]]
    if not markers:
        raise ValueError("give markers or beats")
    _replace_warp_markers(c, markers)
    return _warp_info(c)


@command
def add_warp_markers(ctx, track, clip, markers):
    """Add warp markers to a warped audio clip without touching the existing ones:
    `markers` = [[beat, seconds], ...] (at most 600 per call, so one call stays short on
    Live's main thread). Lets a long clip get a marker on every 16th in chunks: a pool
    groove assigned through the API does not move audio clips (measured 2026-10-30)."""
    c = _clip(_track(ctx, track), clip)
    if not c.is_audio_clip or not c.warping:
        raise ValueError("add_warp_markers needs a warped audio clip")
    if len(markers) > 600:
        raise ValueError("at most 600 markers per call; chunk them")
    import Live
    end = _sample_seconds(c)
    added = 0
    for b, sec in markers:
        if sec > end + 1e-6:
            continue
        c.add_warp_marker(Live.Clip.WarpMarker(float(sec), float(b)))
        added += 1
    return {"added": added, "total": len(list(c.warp_markers))}


def _sample_seconds(c):
    return c.sample_length / float(c.sample_rate or 1)


def _pin_warp(c, beats):
    _replace_warp_markers(c, [[0.0, 0.0], [beats, _sample_seconds(c)]])


def _replace_warp_markers(c, markers):
    c.warping = True
    for m in list(c.warp_markers):
        if m.beat_time > 1e-6:
            try:
                c.remove_warp_marker(m.beat_time)
            except Exception:
                pass
    import Live
    end = _sample_seconds(c)
    # Live lists a marker one 32nd past the sample's end; adding it back fails
    keep = [(b, s) for b, s in markers if s <= end + 1e-6]
    zero = [s for b, s in keep if abs(b) <= 1e-6]
    if zero:
        # auto-warp can pin beat 0 to the first transient (0.34 s into a City synth stem):
        # every target marker earlier in the sample is then "behind" it and refused.
        # Anchor the last target marker, drop the beat-0 one, re-add it at its own time.
        last = max(keep, key=lambda m: m[0])
        if last[0] > 1e-6:
            c.add_warp_marker(Live.Clip.WarpMarker(float(last[1]), float(last[0])))
        for m in list(c.warp_markers):
            if m.beat_time <= 1e-6:
                try:
                    c.remove_warp_marker(m.beat_time)
                except Exception:
                    pass
        if not any(m.beat_time <= 1e-6 for m in c.warp_markers):
            c.add_warp_marker(Live.Clip.WarpMarker(float(zero[0]), 0.0))
    have = set(round(m.beat_time, 6) for m in c.warp_markers)
    for beat, sec in keep:
        if beat <= 1e-6 or round(beat, 6) in have:
            continue
        c.add_warp_marker(Live.Clip.WarpMarker(float(sec), float(beat)))   # (sample_time, beat_time)


@command
def api_probe(ctx, expr):
    """Evaluate a read-only expression against the Live API (exploration only):
    names: Live, song, app. Returns repr() of the result."""
    import Live
    return repr(eval(expr, {"Live": Live, "song": ctx.song, "app": ctx.app, "dir": dir,
                            "getattr": getattr, "type": type}))[:4000]


@command
def clip_attrs(ctx, track, clip=0, match=""):
    """Names on a clip object containing `match` (API exploration)."""
    c = _clip(_track(ctx, track), clip)
    return [a for a in dir(c) if match.lower() in a.lower() and not a.startswith("_")]
