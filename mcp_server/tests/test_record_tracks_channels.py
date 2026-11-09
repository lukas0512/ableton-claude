"""record_tracks must not read a channel list that Live is still rebuilding.

The fake models what Live 12.4.6 does (docs/one-pass-crash.md): setting input_routing_type
leaves available_input_routing_channels stale until a later tick, when Live rebuilds it and
notifies listeners. In real Live a stale read is an unchecked out-of-bounds access that only
sometimes segfaults, so the fake counts every stale read instead of crashing.
"""
import importlib
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "remote_script"
TICK_LIMIT = 200


class Channel:
    def __init__(self, name):
        self.display_name = name


class FakeTrack:
    can_be_armed = True

    def __init__(self, song, name):
        self.song, self.name = song, name
        self.arm = False
        self.current_monitoring_state = 1
        self.input_routing_type = Channel("Ext. In")
        self.input_routing_channel = None
        self.channels = [Channel("1/2"), Channel("1"), Channel("2"), Channel("Configure...")]
        self.rebuild_in = None
        self.listeners = []
        self.arrangement_clips = []

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)
        if key == "input_routing_type" and value.display_name != "Ext. In":
            self.rebuild_in = self.song.rebuild_ticks

    @property
    def available_input_routing_types(self):
        return [Channel("Ext. In")] + [Channel("%d-%s" % (i + 1, t.name))
                                       for i, t in enumerate(self.song.tracks)]

    @property
    def available_input_routing_channels(self):
        self.song.channel_reads += 1
        if self.rebuild_in is not None:
            self.song.stale_reads.append(self.name)
        return list(self.channels)

    def add_available_input_routing_channels_listener(self, fn):
        self.listeners.append(fn)

    def available_input_routing_channels_has_listener(self, fn):
        return fn in self.listeners

    def remove_available_input_routing_channels_listener(self, fn):
        self.listeners.remove(fn)

    def live_tick(self):
        if self.rebuild_in is None or self.song.never_rebuild:
            return
        self.rebuild_in -= 1
        if self.rebuild_in <= 0:
            self.rebuild_in = None
            self.channels = [Channel("Pre FX"), Channel("Post FX"), Channel("Post Mixer")]
            for fn in list(self.listeners):
                fn()


class FakeSong:
    signature_numerator, signature_denominator, tempo = 4, 4, 120.0
    metronome, loop, record_mode, is_playing = True, True, False, False
    current_song_time, start_time = 0.0, 0.0

    def __init__(self, rebuild_ticks=3, never_rebuild=False):
        self.rebuild_ticks, self.never_rebuild = rebuild_ticks, never_rebuild
        self.channel_reads = 0
        self.stale_reads = []
        self.tracks = []
        self.tracks = [FakeTrack(self, "KICK"), FakeTrack(self, "CLAP")]
        self.tracks[1].arm = True
        self.return_tracks, self.visible_tracks = [], self.tracks
        self.master_track = FakeTrack(self, "Main")

    def create_audio_track(self, index):
        self.tracks.append(FakeTrack(self, "%d-Audio" % (len(self.tracks) + 1)))

    def delete_track(self, index):
        del self.tracks[index]

    def start_playing(self):
        self.is_playing = True

    def stop_playing(self):
        self.is_playing = False

    def live_tick(self):
        for t in self.tracks:
            t.live_tick()


@pytest.fixture()
def handlers(monkeypatch):
    fw = types.ModuleType("_Framework")
    cs = types.ModuleType("_Framework.ControlSurface")
    cs.ControlSurface = object
    monkeypatch.setitem(sys.modules, "_Framework", fw)
    monkeypatch.setitem(sys.modules, "_Framework.ControlSurface", cs)
    monkeypatch.setitem(sys.modules, "Live", types.ModuleType("Live"))
    monkeypatch.syspath_prepend(str(ROOT))
    for m in [m for m in sys.modules if m.startswith("ClaudeBridge")]:
        del sys.modules[m]
    return importlib.import_module("ClaudeBridge.handlers")


def drive(gen, song):
    """Run a deferred command the way the bridge does; returns (result, ticks)."""
    for ticks in range(TICK_LIMIT):
        try:
            next(gen)
        except StopIteration as stop:
            return stop.value, ticks
        song.live_tick()
    raise AssertionError("not bounded: still waiting after %d ticks" % TICK_LIMIT)


def start(handlers, song, **kw):
    ctx = types.SimpleNamespace(song=song, record_job=None, pending=[])
    return ctx, handlers.record_tracks(ctx, ["KICK", "CLAP"], 1, 2, **kw)


def taps(song):
    return [t for t in song.tracks if t.name.startswith("tap ")]


@pytest.mark.parametrize("rebuild_ticks", [1, 3, 12, 40])
def test_channels_are_never_read_while_live_rebuilds_them(handlers, rebuild_ticks):
    song = FakeSong(rebuild_ticks=rebuild_ticks)
    ctx, gen = start(handlers, song)
    result, _ = drive(gen, song)
    assert song.stale_reads == []
    assert result["tracks"] == ["tap KICK", "tap CLAP"]
    assert [t.input_routing_channel.display_name for t in taps(song)] == ["Post Mixer"] * 2
    assert all(t.arm and t.current_monitoring_state == 2 for t in taps(song))
    assert ctx.record_job["state"] == "recording"


def test_listeners_are_gone_when_recording_starts(handlers):
    song = FakeSong()
    _, gen = start(handlers, song)
    drive(gen, song)
    assert all(t.listeners == [] for t in taps(song))


def test_wait_restarts_when_a_later_notification_arrives(handlers):
    song = FakeSong()
    watch = handlers._ChannelWatch()
    a = song.tracks[0]
    watch.add(a)
    wait = watch.wait(max_ticks=20, quiet_ticks=3)
    next(wait)
    a.listeners[0]()            # first rebuild
    next(wait)
    next(wait)
    a.listeners[0]()            # rebuilt again before the quiet period ended
    for _ in range(3):
        next(wait)
    with pytest.raises(StopIteration):
        next(wait)


def test_refuses_with_a_clear_message_when_live_never_confirms(handlers):
    song = FakeSong(never_rebuild=True)
    before = [t.name for t in song.tracks]
    ctx, gen = start(handlers, song)
    with pytest.raises(RuntimeError, match=r"refused.*tap KICK.*one_pass=False"):
        drive(gen, song)
    assert song.channel_reads == 0
    assert [t.name for t in song.tracks] == before
    assert song.tracks[1].arm is True and ctx.record_job is None


def test_the_wait_is_bounded_and_fits_the_deferred_timeout(handlers):
    song = FakeSong(never_rebuild=True)
    _, gen = start(handlers, song)
    ticks = 0
    with pytest.raises(RuntimeError):
        for ticks in range(TICK_LIMIT):
            next(gen)
    assert ticks <= handlers.CHANNELS_MAX_TICKS
    assert handlers.CHANNELS_MAX_TICKS * 0.1 < handlers.DEFERRED_TIMEOUT_S


def test_closing_the_command_removes_the_tap_tracks(handlers):
    """_advance closes a command past its deadline: no orphan taps, no armed leftovers."""
    song = FakeSong()
    before = [t.name for t in song.tracks]
    _, gen = start(handlers, song)
    next(gen)
    gen.close()
    assert [t.name for t in song.tracks] == before and song.tracks[1].arm is True


def test_a_missing_channel_rolls_back_after_the_wait(handlers):
    song = FakeSong()
    before = [t.name for t in song.tracks]
    _, gen = start(handlers, song, tap="No Such Channel")
    with pytest.raises(ValueError, match="No Such Channel"):
        drive(gen, song)
    assert song.stale_reads == [] and [t.name for t in song.tracks] == before


def test_record_master_needs_no_channel_wait(handlers):
    song = FakeSong()

    def resampling(rt):
        pass
    ctx = types.SimpleNamespace(song=song, record_job=None, pending=[])
    gen = handlers._start_record(ctx, 1, 2, [("Claude Render", None, resampling)])
    result, _ = drive(gen, song)
    assert result["tracks"] == ["Claude Render"] and song.channel_reads == 0
