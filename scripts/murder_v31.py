"""Murder v31 (2026-10-28): his notes on v30: "tá ficando melhor, mas pode sempre tentar
resintetizar coisas do loop; vamos fazer algo melhor em questão de mix; o arranjo também,
pressão e alívio dos drops pode ser melhor".

Measured on v30 (2-bar LUFS): every kick section from bar 9 to 176 sat at -8.0..-8.4, the
breaks only 2 LU under the drops (refs 3.8-5), build 1 peaked over drop 1 (bars 61-62 -7.8
vs -8.2), build 2 reached -8.0 before drop 2 at -8.0, and the sine sub played bars 115-116 in
the middle of build 2 (the drop's release spent early). Soloed in drop 1 (89-96) against the
kick: four hat layers -9.1..-12 (target -15..-16), ride -13 (-20), the MIDI riff -8.1 (-12),
the choir -12.8 (-16), the two basses -6 together (-3).

- mix: those faders, the MIDI riff -2.5 dB at 350 Hz where it masked kick and bass.
- choir: the choir loop (htdemucs_6s 'other': Em = B3 G4 E5, then Em(maj7) = E3 G3 B4 D#5
  E5) replayed in MIDI on the preset whose spectrum is nearest, through the loop's chain;
  the loop stays 7 dB down as the record's air. In the builds the chord is struck again
  every bar, louder and opening (the track's own riser, no generic one).
- arc: one gain map for the riff, its loop and the choir: grooves -1.5, breaks -2.5, the
  builds climbing -1.5 -> +1.5, drop 2 +1.5. The breaks' sub 2 dB down (~8 dB under the
  drop), the drop hats (imite) kept for the drops, build 1's calls 2 dB down, the high-passed
  kick pulsing through both builds (HP 400 -> 150 Hz, quarters, 8ths in the last bars,
  velocity rising), the sine sub out of build 2.
- breath2: the last two beats before drop 2 empty but the tom run, the "Murder" stutter
  and the call into the drop (his pre-drop: the track stops, the title, then the drop).

Stages: python murder_v31.py timbre | choir <preset> | mix | arc | breath2
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_murder as M  # noqa: E402
import murder_v30 as V30  # noqa: E402
from build_murder import C, beat, client  # noqa: E402

CHOIR_LOOP = M.CHOIR
CHOIR_FILE = M.LOOPS / "Murder choir (6s, pocket 0.050).wav"
CHOIR_MIDI = "CHOIR MURDER - pad (MIDI)"
CHOIR_CANDIDATES = ["sounds/Pad/Choir Pad Avalon.adg", "sounds/Voices/Choir Metal Muted.adv",
                    "sounds/Voices/Choir Reverb.adv", "sounds/Voices/Choir Steam.adv",
                    "sounds/Strings/Synthetic Choir Strings.adg"]
BUILDS = [(57, 64), (113, 120.5)]          # (first bar, where the climb stops)
BREAKS = M.BREAKS
# v31b: (-1.5, -.5, .5, 1.5) opened the builds 0.5 LU under the breaks and topped at -10.8
BUILD_RAMP = (0.0, 1.5, 3.0, 4.5)


def choir_notes(bars, vel=96):
    """The loop's two chords, one per bar: Em (B3 G4 E5) then Em(maj7) (E3 G3 B4 D#5 E5)."""
    a = [(59, vel), (67, vel), (76, vel - 8)]
    b = [(52, vel - 6), (55, vel - 6), (71, vel), (75, vel - 18), (76, vel - 8)]
    out = []
    for k in range(bars):
        for p, v in (a if k % 2 == 0 else b):
            out.append([p, k * 4.0, 3.9, max(1, min(127, v))])
    return out


def arc_gain(bar):
    """dB for the music loops (riff, its loop, the choir) at `bar`."""
    for a, top in BUILDS:
        if a <= bar < top + .5:
            return BUILD_RAMP[min(3, int((bar - a) // 2))]
    if any(x <= bar < y for x, y in BREAKS):
        return -2.5
    if 17 <= bar < 49:
        return -1.5
    if 121 <= bar < 153:
        return 1.5
    return 0.0


# ---------------------------------------------------------------- timbre
def timbre():
    """Each candidate plays 2 bars of the choir past the song's end; its 1/3-octave shape
    against the loop's, 160 Hz-5 kHz (the loop's chain high-passes at 300 Hz)."""
    from ableton_claude.solo_pass import THIRD_OCTAVES, render_taps
    song = client.call("get_song")
    at = (int(song["song_length_beats"] // 16) + 4) * 16
    if "timbre probe" not in [t["name"] for t in song["tracks"]]:
        C("create_track", kind="midi", name="timbre probe")
    ref = V30._bands(CHOIR_FILE)
    sel = [i for i, hz in enumerate(THIRD_OCTAVES) if 160 <= hz <= 5000]
    out = {}
    try:
        for path in CHOIR_CANDIDATES:
            for _ in client.call("get_track", {"track": "timbre probe"})["devices"]:
                C("delete_device", track="timbre probe", device=0)
            C("load_device", track="timbre probe", path=path)
            for c in M._clips("timbre probe"):
                C("delete_clip", track="timbre probe", clip={"at": c["start"]})
            C("create_midi_clip", track="timbre probe", beat=at, length=8, notes=choir_notes(2))
            f = render_taps(client.call, ["timbre probe"], at / 4 + 1, at / 4 + 3, 60)["timbre probe"]
            d = V30._bands(f) - ref
            out[path] = round(float(np.sqrt(np.mean(d[sel] ** 2))), 2)
            print(path, out[path], flush=True)
    finally:
        C("delete_track", track="timbre probe")
    best = min(out, key=out.get)
    print("nearest:", best)
    return best, out


# ---------------------------------------------------------------- choir
def _copy_chain(src, dst):
    """The source track's devices onto `dst` after its instrument, in order (by index, so
    two EQ Eights stay two)."""
    devs = client.call("get_track", {"track": src})["devices"]
    have = len(client.call("get_track", {"track": dst})["devices"])
    for k, d in enumerate(devs):
        if have < k + 2:
            C("load_device", track=dst, path="audio_effects/" + d["name"])
            have += 1
        C("copy_device", src_track=src, src_device=k, track=dst, device=k + 1)


def _gain_env(L, bar):
    return {"param": "Output", "device": "Utility", "unit": "db",
            "points": [[0, arc_gain(bar)], [L, arc_gain(bar)]]}


def _choir_hz(bar):
    return 1800 if any(x <= bar < y for x, y in BREAKS) else 9000


def choir(preset):
    song = client.call("get_song")
    names = [t["name"] for t in song["tracks"]]
    idx = names.index(CHOIR_LOOP)
    info = client.call("get_track", {"track": CHOIR_LOOP})
    if CHOIR_MIDI not in names:
        C("create_track", kind="midi", name=CHOIR_MIDI, index=idx + 1)
        C("load_device", track=CHOIR_MIDI, path=preset)
        C("set_track_output", track=CHOIR_MIDI,
          dest=client.call("track_routing", {"track": CHOIR_LOOP})["output"])
        for k, db in enumerate(info["sends_db"]):
            if db is not None and db > -60:
                C("set_send", track=CHOIR_MIDI, send=k, db=db)
        C("set_track", track=CHOIR_MIDI, pan=info["pan"], color_index=19)
        _copy_chain(CHOIR_LOOP, CHOIR_MIDI)
        C("load_device", track=CHOIR_MIDI, path="audio_effects/Utility")
    for c in M._clips(CHOIR_MIDI):
        C("delete_clip", track=CHOIR_MIDI, clip={"at": c["start"]})
    cmds = []
    for c in [c for c in M._clips(CHOIR_LOOP) if not c["muted"]]:
        L, bar = c["end"] - c["start"], c["start"] / 4 + 1
        notes = [n for n in choir_notes(int(np.ceil(L / 4))) if n[1] < L - .01]
        hz = M.sr.filter_raw(_choir_hz(bar))
        cmds.append({"cmd": "create_midi_clip", "args": {
            "track": CHOIR_MIDI, "beat": c["start"], "length": L, "notes": notes,
            "name": "Murder choir (MIDI)", "envelopes": [
                {"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                 "points": [[0, hz], [L, hz]]}, _gain_env(L, bar)]}})
    # the builds: the chord struck every bar, louder and opening, up to the climb's end
    for a, top in BUILDS:
        L = beat(top) - beat(a)
        bars = int(np.ceil(L / 4))
        notes = []
        for k, n in enumerate(choir_notes(bars)):
            b = int(n[1] // 4)
            notes.append([n[0], n[1], min(3.9, L - n[1]), int(60 + 50 * b / max(1, bars - 1))])
        cmds.append({"cmd": "create_midi_clip", "args": {
            "track": CHOIR_MIDI, "beat": beat(a), "length": L, "notes": notes,
            "name": "Murder choir rising (build)", "envelopes": [
                {"param": "Frequency", "device": "Auto Filter", "unit": "raw",
                 "points": [[0, M.sr.filter_raw(400)], [L, M.sr.filter_raw(7000)]]},
                {"param": "Output", "device": "Utility", "unit": "db",
                 "points": [[0, -6], [L, 1.5]]}]}})
    for r in M.server._journaled_batch(cmds):
        if not r.get("ok"):
            print("choir clip:", r.get("error"))
    C("set_track", track=CHOIR_LOOP, volume_db=round(info["vol_db"] - 7, 1))


# ---------------------------------------------------------------- mix
FADERS = {"HAT OFF - persona": -3, "HAT OFF - shaker shot": -3, "HAT OFF - imite": -3,
          "HAT 16ths": -2, "RIDE 909": -4, "SNARE": -1.5, V30.RIFF_TRACK: -3,
          "BASS (clean)": 2, M.SINE: 1.5}


def mix():
    for tr, d in FADERS.items():
        v = client.call("get_track", {"track": tr})["vol_db"]
        C("set_track", track=tr, volume_db=round(v + d, 1))
    k = M._free(V30.RIFF_TRACK, set())
    M._eq(V30.RIFF_TRACK, k, "Bell", 350, -2.5, 1.2)
    C("re_enable_automation")


# ---------------------------------------------------------------- arc
def _riff_clips():
    """The MIDI riff again clip for clip under the loop, velocities as played, the level
    from the gain map on its Utility; the loop's clip gain from the same map."""
    for c in M._clips(V30.RIFF_TRACK):
        C("delete_clip", track=V30.RIFF_TRACK, clip={"at": c["start"]})
    cmds = []
    for c in [c for c in M._clips(V30.LOOP_TRACK) if not c["muted"]]:
        L, bar = c["end"] - c["start"], c["start"] / 4 + 1
        cmds.append({"cmd": "set_clip", "args": {"track": V30.LOOP_TRACK,
                                                 "clip": {"at": c["start"]},
                                                 "gain_db": arc_gain(bar)}})
        notes = [n for n in V30.riff_notes(int(np.ceil(L / 4))) if n[1] < L - .01]
        env = {"param": "Frequency", "device": "Auto Filter", "unit": "raw",
               "points": [[0, M.sr.filter_raw(M._bed_hz_v4(bar))],
                          [L, M.sr.filter_raw(M._bed_hz_v4(bar + L / 4))]]}
        cmds.append({"cmd": "create_midi_clip", "args": {
            "track": V30.RIFF_TRACK, "beat": c["start"], "length": L, "notes": notes,
            "name": "Murder riff (MIDI)", "envelopes": [env, _gain_env(L, bar)]}})
    for r in M.server._journaled_batch(cmds):
        if not r.get("ok"):
            print("riff clip:", r.get("error"))


def _hp_kick(a, top):
    """Quarters from the build's first bar, 8ths in its last two, velocity 70 -> 120,
    the high-pass sweeping 400 -> 150 Hz: the kick's weight returns, its sub saved for the
    drop."""
    T = "KICK - build (HP)"
    L = beat(top) - beat(a)
    for c in M._clips(T):
        if beat(a) - 1e-3 <= c["start"] < beat(top + 1):
            C("delete_clip", track=T, clip={"at": c["start"]})
    notes, t = [], 0.0
    while t < L - 1e-3:
        step = .5 if t >= L - 8 else 1.0
        notes.append([62, t, step * .9, int(70 + 50 * t / L)])
        t += step
    C("create_midi_clip", track=T, beat=beat(a), length=L, notes=notes,
      name="build kick: HP 400 -> 150 Hz", envelopes=[
          {"param": "1 Frequency A", "device": "EQ Eight", "unit": "display",
           "points": [[0, 400], [L, 150]]}])


def arc():
    _riff_clips()
    for a, top in BUILDS:
        _hp_kick(a, top)
    # the intro/outro HP kicks hold 180 Hz (an envelope stays where it ended): Live makes
    # no envelope on an existing Arrangement clip, so they are re-created with one
    T = "KICK - build (HP)"
    for c in M._clips(T):
        if not c["muted"] and not (c.get("name") or "").startswith("build kick"):
            L = c["end"] - c["start"]
            notes = client.call("get_notes", {"track": T, "clip": {"at": c["start"]}})
            C("delete_clip", track=T, clip={"at": c["start"]})
            C("create_midi_clip", track=T, beat=c["start"], length=L, notes=notes,
              name=c.get("name"), envelopes=[{"param": "1 Frequency A", "device": "EQ Eight",
                                              "unit": "display", "points": [[0, 180], [L, 180]]}])
    v = client.call("get_track", {"track": M.SUB})["vol_db"]
    C("set_track", track=M.SUB, volume_db=round(v - 2, 1))
    for c in M._clips("HAT OFF - imite"):
        if 57 <= c["start"] / 4 + 1 < 65 and not c["muted"]:
            C("set_clip", track="HAT OFF - imite", clip={"at": c["start"]}, muted=True)
    for c in M._clips("VOX MURDER - theme calls"):
        if 60 <= c["start"] / 4 + 1 < 64:
            C("set_clip", track="VOX MURDER - theme calls", clip={"at": c["start"]},
              gain_db=round((c.get("gain_db") or 0) - 2, 2))
    for c in M._clips(M.SINE):
        if 113 <= c["start"] / 4 + 1 < 121:
            C("delete_clip", track=M.SINE, clip={"at": c["start"]})
    C("re_enable_automation")


# ---------------------------------------------------------------- breath2
KEEP_BREATH = {"FX - transitions", "FX - glitches", "FX - sub boom", "CRASH 909",
               "VOX MURDER - theme calls", "LOW END", "DRUMS", "MUSIC BUS", "VOX BUS", "FX BUS"}


def breath2(a_bar=120.5, b_bar=121):
    a, b = beat(a_bar), beat(b_bar)
    for t in client.call("get_song")["tracks"]:
        n = t["name"]
        if n in KEEP_BREATH or n.startswith("REF"):
            continue
        info = client.call("get_track", {"track": t["i"]})
        if not info.get("clips"):
            continue
        if info["kind"] == "midi":
            V30._filter_notes(n, lambda x: a - 1e-3 <= x < b - 1e-3)
            continue
        for c in info["clips"]:
            if c["muted"]:
                continue
            if c["start"] < a - 1e-3 < c["end"] - 1e-3:
                if c["end"] <= b + 1e-3:
                    C("trim_clip", track=n, clip={"at": c["start"]}, end_beat=a)
                else:
                    print("spans the breath, left:", n, c["start"] / 4 + 1)
            elif a - 1e-3 <= c["start"] < b - 1e-3:
                C("set_clip", track=n, clip={"at": c["start"]}, muted=True)
    C("re_enable_automation")


def build_up():
    """v31 render: the breaks -12 (3.9 LU under the drops, right), but each build opened at
    -12.7 under its break and lost 2-3 dB of highs as it climbed (the drop hats muted there).
    The riff ramp 0 -> +4.5 dB, the HP kick 2.3 dB up, the imite hats back in the climbs
    (the drop keeps its snare, ride, sub and kick as the release)."""
    _riff_clips()
    v = client.call("get_track", {"track": "KICK - build (HP)"})["vol_db"]
    C("set_track", track="KICK - build (HP)", volume_db=round(v + 2.3, 1))
    for c in M._clips("HAT OFF - imite"):
        bar = c["start"] / 4 + 1
        if c["muted"] and (57 <= bar < 65 or 113 <= bar < 121):
            C("set_clip", track="HAT OFF - imite", clip={"at": c["start"]}, muted=False)
    C("re_enable_automation")


# ---------------------------------------------------------------- gain staging
# He (2026-10-28): "vamos fazer a mix sempre com o kick em -10 e o resto em cima disso,
# lembrando o kick ser o elemento mais alto da track; depois esse espaço que vai sobrar
# puxamos com a master, pra ter algo com mais qualidade e mais colado". Measured with the
# master chain off (drop 89-96): the kick peaked -8.5 dBFS on its channel and -8.6 into the
# master, the mix -3.2 dBFS / -16.1 LUFS. Every channel 1.5 dB down (the kick's channel and
# its share of the master input at -10); whatever reacts to level is moved with it so the
# balance and the dynamics stay as they were: bus compressors' thresholds, compressors keyed
# by the kick (post mixer) or the vocal bus, bus saturators (drive up, output down), the drum
# bus limiter's ceiling (the same gain reduction, 1.5 dB lower).
STAGE_DB = -1.5
BUSES = ("LOW END", "DRUMS", "MUSIC BUS", "VOX BUS", "FX BUS")


def _db(track, device, param):
    p = client.call("get_device", {"track": track, "device": device})["params"]
    d = {q["name"]: q["display"] for q in p}
    return float(d[param].split()[0])


def _shift(track, device, param, delta):
    C("set_param", track=track, device=device, param=param,
      db=round(_db(track, device, param) + delta, 2))


def gainstage(d=STAGE_DB):
    for t in client.call("get_song")["tracks"]:
        n = t["name"]
        if n.startswith("REF") or n in BUSES:
            continue
        C("set_track", track=n, volume_db=round(t["vol_db"] + d, 1))
    for tr in ("BASS (clean)", M.SUB, "MUSIC BUS", V30.LOOP_TRACK, V30.RIFF_TRACK, "VOX BUS"):
        _shift(tr, "Compressor", "Threshold", d)          # keyed by KICK / VOX BUS, or its input
    for tr in ("LOW END", "DRUMS"):
        _shift(tr, "Glue Compressor", "Threshold", d)
    for tr in ("LOW END", "DRUMS", "MUSIC BUS", "VOX BUS"):
        _shift(tr, "Saturator", "Drive", -d)
        _shift(tr, "Saturator", "Output", d)
    _shift("DRUMS", "Limiter", "Ceiling", d)
    C("re_enable_automation")


if __name__ == "__main__":
    stage = sys.argv[1]
    if stage == "timbre":
        print(json.dumps(timbre()))
    elif stage == "choir":
        choir(sys.argv[2])
    else:
        {"mix": mix, "arc": arc, "breath2": breath2, "build_up": build_up, "gainstage": gainstage}[stage]()
    Path(M.ROOT / f"v31_{stage}.json").write_text(json.dumps(M.LOG, default=str))
