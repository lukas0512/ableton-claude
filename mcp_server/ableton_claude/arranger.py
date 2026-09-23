"""Build arrangements in Live from a library of phrases.

Workflow: stash() copies a clean phrase of each track into a library zone far past the
song; clear() empties the song area; fill()/place() lay phrases out; drop_library()
removes the zone. Everything goes through ClaudeBridge commands, so Live itself keeps
clip positions, warping and sample offsets consistent. Build each track left to right:
fill() cuts overhangs by dropping a copy on top, which assumes the space after is empty.
"""
from dataclasses import dataclass

from . import client as _client


@dataclass
class Phrase:
    track: str
    start_bar: float     # position in the library zone
    end_bar: float

    @property
    def bars(self):
        return self.end_bar - self.start_bar


class Arranger(object):
    def __init__(self, call=None, library_bar=601, slot_bars=24, log=print):
        self.call = call or _client.call
        self.library_bar = library_bar
        self.slot_bars = slot_bars
        self.slots = {}
        self.log = log
        self.parts = []           # (track, start_bar, end_bar) for the energy map

    def stash(self, track, src_start_bar, src_end_bar):
        length = src_end_bar - src_start_bar
        if length > self.slot_bars:
            raise ValueError("phrase longer than a library slot")
        k = self.slots.get(track, 0)
        self.slots[track] = k + 1
        dest = self.library_bar + k * self.slot_bars
        r = self.call("duplicate_range", {"track": track, "start_bar": src_start_bar,
                                          "end_bar": src_end_bar, "dest_bar": dest})
        if not r["copied"]:
            raise RuntimeError("nothing to stash on %s bars %s-%s"
                               % (track, src_start_bar, src_end_bar))
        return Phrase(track, dest, dest + length)

    def clear(self, track, start_bar=1, end_bar=None):
        r = self.call("delete_clips_in_range", {"track": track, "start_bar": start_bar,
                                                "end_bar": end_bar or self.library_bar})
        if r["left_in_range"]:
            raise RuntimeError("could not clear %s: %s" % (track, r))
        return r["deleted"]

    def fill(self, phrase, start_bar, end_bar):
        self.call("fill_range", {"track": phrase.track, "src_start_bar": phrase.start_bar,
                                 "src_end_bar": phrase.end_bar, "start_bar": start_bar,
                                 "end_bar": end_bar})
        self.parts.append((phrase.track, start_bar, end_bar))

    def place(self, phrase, bar):
        self.call("duplicate_range", {"track": phrase.track, "start_bar": phrase.start_bar,
                                      "end_bar": phrase.end_bar, "dest_bar": bar})
        self.parts.append((phrase.track, bar, bar + phrase.bars))

    def drop_library(self):
        for track in self.slots:
            self.call("delete_clips_in_range", {"track": track, "start_bar": self.library_bar,
                                                "end_bar": self.library_bar + 5000})


def energy(parts, bars, weights=None):
    """Weighted count of sounding parts per bar: a quick picture of the story arc."""
    weights = weights or {}
    curve = [0.0] * bars
    for track, a, b in parts:
        w = weights.get(track, 1.0)
        for bar in range(int(a), int(min(b, bars + 1))):
            if 1 <= bar <= bars:
                curve[bar - 1] += w
    return curve
