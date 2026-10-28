"""Murder v30 (2026-10-26): his notes on the upgrades copy ("Murder pista - teste
upgrades.als"):
- "você mudou esse baixo, ele tinha um mais interessante": V1's bass (Murder's riff off
  the kick, `dub_riff`) back on every bass layer, with today's cleaner two-layer timbres.
- "o loop de Murder tá bem sujo; pode ser refeito em MIDI o baixinho que ele faz": the riff
  loop (htdemucs_6s piano stem) is 84 % 70-300 Hz and tags as brass/foghorn (separation
  smear); its line is Murder's riff an octave over the bass (E2 E2 E2 G2 | D2 D#2). It is
  played again in MIDI on the preset whose spectrum is nearest the loop's, the loop kept
  under it as grit.
- "o compasso antes do drop 1 ainda tá estranho": bar 64 kept clap, hats, the bass teaser
  and half the riff under two vocal phrases. Now his pre-drop formula: the whole track
  stops one bar, the "Murder" call a cappella, its last word into the delay, the reversed
  crash, then the drop.
- "use as coisas novas": the record's own DJ scratch (src 0:08.0-0:09.5, found by the new
  AudioSet tags at p 0.75 in the drums + other stems) as ear candy at the turn from break 2
  into build 2 (the chops there end a bar early to make room).

Stages: python murder_v30.py timbre | bass | riff | predrop | scratch
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_murder as M  # noqa: E402
from build_murder import C, beat, client  # noqa: E402

LOOP_TRACK = "LOOP MURDER - riff (keys)"
LOOP_FILE = M.LOOPS / "Murder riff keys (6s, pocket 0.050).wav"
RIFF_TRACK = "RIFF MURDER - keys (MIDI)"
CANDIDATES = ["sounds/Piano & Keys/Grand Piano.adg", "sounds/Piano & Keys/Ac Piano Upright.adg",
              "sounds/Piano & Keys/E-Piano MKII Hollow.adv", "sounds/Piano & Keys/Clav Electric.adv"]
SCRATCH = M.ROOT / "loops" / "Murder scratch (src 0-08).wav"
ELEMENTS = M.ROOT / "Murder original - elements"
SW = M.V4_SWING                       # the set's 60 % pocket


def riff_notes(bars, low=40):
    """The loop's line, transcribed (onsets in the 40-330 Hz band, pitch per note):
    bar A E E E G . . D D# ; bar B E E E . G G G G D (held), swung like the set."""
    a = [(0, 0, .45, 112), (0, .5, .4, 92), (0, 1.0, .4, 92), (3, 1.5, 1.35, 116),
         (-2, 3.0, .45, 118), (-1, 3.5, .45, 108)]
    b = [(0, 0, .25, 112), (0, .25, .45, 100), (0, .75, .2, 88), (3, 1.5, .15, 112),
         (3, 1.75, .45, 112), (3, 2.25, .2, 100), (3, 2.5, .15, 100), (3, 2.75, .25, 100),
         (-2, 3.0, .95, 118)]
    out = []
    for k in range(bars):
        for iv, t, d, v in (a if k % 2 == 0 else b):
            late = SW if round(t * 4) % 2 else 0
            out.append([low + iv, k * 4 + t + late, d, v])
    return out


def _bands(path):
    from ableton_claude.solo_pass import third_octave_abs_db
    x, sr = sf.read(str(path), dtype="float64")
    m = x.mean(axis=1) if x.ndim == 2 else x
    v = np.array(third_octave_abs_db(m, sr))
    return v - v.max()


def timbre():
    """Each candidate plays 2 bars of the riff past the song's end; its 1/3-octave shape
    against the loop's (both normalised to their loudest band), 63 Hz-5 kHz."""
    song = client.call("get_song")
    at = (int(song["song_length_beats"] // 16) + 4) * 16
    names = [t["name"] for t in song["tracks"]]
    if "timbre probe" not in names:
        C("create_track", kind="midi", name="timbre probe")
    ref = _bands(LOOP_FILE)
    from ableton_claude.solo_pass import THIRD_OCTAVES, render_taps
    sel = [i for i, hz in enumerate(THIRD_OCTAVES) if 63 <= hz <= 5000]
    out = {}
    try:
        for path in CANDIDATES:
            devs = client.call("get_track", {"track": "timbre probe"})["devices"]
            for _ in devs:
                C("delete_device", track="timbre probe", device=0)
            C("load_device", track="timbre probe", path=path)
            for c in M._clips("timbre probe"):
                C("delete_clip", track="timbre probe", clip={"at": c["start"]})
            C("create_midi_clip", track="timbre probe", beat=at, length=8, notes=riff_notes(2))
            f = render_taps(client.call, ["timbre probe"], at / 4 + 1, at / 4 + 3, 60)["timbre probe"]
            d = _bands(f) - ref
            out[path] = round(float(np.sqrt(np.mean(d[sel] ** 2))), 2)
            print(path, out[path], flush=True)
    finally:
        C("delete_track", track="timbre probe")
    best = min(out, key=out.get)
    print("nearest:", best)
    return best, out


def bass():
    """V1's riff on every layer (BASS (clean) mid bass, the sine sub, the breaks sub, the
    teaser), at the set's 60 % swing; the sine's notes stay short so the sub breathes."""
    M.DUB_SWING = SW
    for tr, e in (("BASS (clean)", 64), (M.SINE, 28), (M.SUB, 64), ("BASS - teaser (HP)", 76)):
        for c in M._clips(tr):
            bars = int(round((c["end"] - c["start"]) / 4 + .49))
            ramp = (lambda b, k, n=bars: int(70 + 20 * (b * 6 + k) / max(1, n * 6 - 1))) \
                if "teaser" in tr else None
            notes = [n for n in M.dub_riff(bars, e, ramp) if n[1] < c["end"] - c["start"] - .01]
            if tr == M.SINE:
                notes = [[p, t, min(d, .32), v] for p, t, d, v in notes]
            C("add_notes", track=tr, clip={"at": c["start"]}, notes=notes, replace=True)
            C("set_clip", track=tr, clip={"at": c["start"]}, name="Murder riff bass (V1, off the kick)")


def riff(preset):
    """A MIDI track under the loop plays its line on `preset`, clip for clip, through a
    copy of the loop's chain (EQ, Auto Filter, the compressor that ducks it under the
    vocals, Utility) with the loop's filter map as clip envelopes and its build ramps as
    velocity; the loop stays under it 6 dB down as the record's grit."""
    song = client.call("get_song")
    idx = [t["i"] for t in song["tracks"] if t["name"] == LOOP_TRACK][0]
    info = client.call("get_track", {"track": LOOP_TRACK})
    if RIFF_TRACK not in [t["name"] for t in song["tracks"]]:
        C("create_track", kind="midi", name=RIFF_TRACK, index=idx + 1)
        C("load_device", track=RIFF_TRACK, path=preset)
        C("set_track_output", track=RIFF_TRACK,
          dest=client.call("track_routing", {"track": LOOP_TRACK})["output"])
        for k, db in enumerate(info["sends_db"]):
            if db is not None and db > -60:
                C("set_send", track=RIFF_TRACK, send=k, db=db)
        C("set_track", track=RIFF_TRACK, pan=info["pan"])
    have = [d["name"] for d in client.call("get_track", {"track": RIFF_TRACK})["devices"]]
    for d in info["devices"]:
        if d["name"] not in have:
            C("load_device", track=RIFF_TRACK, path="audio_effects/" + d["name"])
        C("copy_device", src_track=LOOP_TRACK, src_device=d["name"], track=RIFF_TRACK,
          device=d["name"])
    try:
        sc = client.call("device_inputs", {"track": LOOP_TRACK, "device": "Compressor"})
        if sc.get("type") and sc["type"] != "No Input":
            C("set_device_input", track=RIFF_TRACK, device="Compressor", source=sc["type"],
              channel=sc.get("channel") or None)
    except Exception as e:
        print("sidechain not copied:", e)
    for c in M._clips(RIFF_TRACK):
        C("delete_clip", track=RIFF_TRACK, clip={"at": c["start"]})
    for c in [c for c in M._clips(LOOP_TRACK) if not c["muted"]]:
        L, bar = c["end"] - c["start"], c["start"] / 4 + 1
        g = 10 ** (((c.get("gain_db") or 0) - (-1.5 if 17 <= bar < 49 else 0)) / 40)
        notes = [[p, t, d, int(min(127, v * g))] for p, t, d, v in riff_notes(int(np.ceil(L / 4)))
                 if t < L - .01]
        env = {"param": "Frequency", "device": "Auto Filter", "unit": "raw",
               "points": [[0, M.sr.filter_raw(M._bed_hz_v4(bar))],
                          [L, M.sr.filter_raw(M._bed_hz_v4(bar + L / 4))]]}
        C("create_midi_clip", track=RIFF_TRACK, beat=c["start"], length=L, notes=notes,
          name="Murder riff (MIDI)", envelopes=[env])
    C("set_track", track=LOOP_TRACK, volume_db=round(info["vol_db"] - 6, 1))


def _filter_notes(track, drop):
    for c in M._clips(track):
        notes = client.call("get_notes", {"track": track, "clip": {"at": c["start"]}})
        keep = [n for n in notes if not drop(c["start"] + n[1])]
        if len(keep) != len(notes):
            C("add_notes", track=track, clip={"at": c["start"]}, notes=keep, replace=True)


KEEP_PREDROP = {"VOX MURDER - hooks", "FX - transitions", "FX - sub boom", "CRASH 909",
                "LOW END", "DRUMS", "MUSIC BUS", "VOX BUS", "FX BUS"}


def predrop(stop=64, drop=65):
    """Bar `stop`: everything stops but the a cappella call, its last word thrown into
    the delay (send B) and the plate, and the reversed crash into the drop."""
    a, b = beat(stop), beat(drop)
    for t in client.call("get_song")["tracks"]:
        n = t["name"]
        if n in KEEP_PREDROP or n.startswith("REF"):
            continue
        info = client.call("get_track", {"track": t["i"]})
        if not info.get("clips"):
            continue
        if info["kind"] == "midi":
            _filter_notes(n, lambda x: a - 1e-3 <= x < b - 1e-3)
            continue
        for c in info["clips"]:
            if c["muted"]:
                continue
            if c["start"] < a - 1e-3 < c["end"] - 1e-3 and c["end"] <= b + 1e-3:
                C("trim_clip", track=n, clip={"at": c["start"]}, end_beat=a)
            elif a - 1e-3 <= c["start"] < b - M.sr.PREROLL - 1e-3:
                C("set_clip", track=n, clip={"at": c["start"]}, muted=True)
    # the a cappella: re-create the call with a delay throw on its last beat
    vox = "VOX MURDER - hooks"
    c = [x for x in client.call("get_track", {"track": vox, "clips": True, "markers": True})["clips"]
         if a - 1 <= x["start"] < b and not x["muted"]][0]
    mk = client.call("warp_markers", {"track": vox, "clip": {"at": c["start"]}})["markers"]
    L = c["end"] - c["start"]
    env = [{"param": "send:1", "unit": "db",
            "points": [[0, -70], [L - 1.05, -70], [L - 1, -4], [L + 4, -4]]},
           {"param": "send:4", "unit": "db", "points": [[0, -18], [L, -12]]}]
    C("delete_clip", track=vox, clip={"at": c["start"]})
    C("create_audio_clip", track=vox, path=c["file"], beat=c["start"], warp=True,
      warp_mode="complex_pro", envelopes=env, name="PRE-DROP a cappella: Murder call",
      gain_db=(c.get("gain_db") or 0) + 1.5)
    C("set_warp_markers", track=vox, clip={"at": c["start"]},
      markers=[[m["beat"], m["sample_s"]] for m in mk])
    C("set_clip", track=vox, clip={"at": c["start"]}, looping=False,
      start_marker=c["start_marker"], end_marker=c["end_marker"])
    new = [x for x in M._clips(vox) if abs(x["start"] - c["start"]) < 1e-3][0]
    if new["end"] > c["end"] + 1e-3:
        C("trim_clip", track=vox, clip={"at": c["start"]}, end_beat=c["end"])
    C("re_enable_automation")


def scratch(at_bar=113):
    """The record's scratch (drums + other stems, src 8.0-9.6 s), unwarped, ending on the
    downbeat of `at_bar` on FX - glitches; the chops clip under it ends a bar early."""
    if not SCRATCH.exists():
        name = "03 - UGK (Underground Kingz) - Murder"
        x = sum(sf.read(str(ELEMENTS / f"{name} - {s}.wav"), dtype="float32")[0]
                for s in ("drums", "other"))
        sr = sf.info(str(ELEMENTS / f"{name} - drums.wav")).samplerate
        seg = x[int(7.95 * sr):int(9.6 * sr)].copy()
        fade = int(.01 * sr)
        seg[:fade] *= np.linspace(0, 1, fade)[:, None]
        seg[-fade * 4:] *= np.linspace(1, 0, fade * 4)[:, None]
        sf.write(str(SCRATCH), seg, sr, subtype="PCM_24")
    tempo = client.call("get_song")["tempo"]
    L = sf.info(str(SCRATCH)).duration * tempo / 60
    for c in M._clips("CHOPS - Murder"):
        if c["start"] < beat(at_bar - 1) < c["end"] - 1e-3 and c["end"] <= beat(at_bar) + 1e-3:
            C("trim_clip", track="CHOPS - Murder", clip={"at": c["start"]},
              end_beat=beat(at_bar - 1))
    C("create_audio_clip", track="FX - glitches", path=str(SCRATCH), beat=beat(at_bar) - L,
      warp=False, name="Murder scratch (the record's DJ)")


if __name__ == "__main__":
    stage = sys.argv[1]
    if stage == "timbre":
        print(json.dumps(timbre()))
    elif stage == "riff":
        riff(sys.argv[2])
    else:
        {"bass": bass, "predrop": predrop, "scratch": scratch}[stage]()
    Path(M.ROOT / f"v30_{stage}.json").write_text(json.dumps(M.LOG, default=str))
