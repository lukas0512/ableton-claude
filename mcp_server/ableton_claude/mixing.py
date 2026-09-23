"""Turn a comparison with a genre profile into a few broad, bounded mix moves.

A profile says where a mix sits outside the references' middle half. Chasing every
1/3-octave band would be worse than a human engineer would do, so moves are grouped into
at most four wide regions (low shelf, low bell, mid bell, high shelf) and capped. The
point is to bring a mix into the genre's range, not to clone a curve.
"""
import math

REGIONS = [  # name, low Hz, high Hz, filter type in EQ Eight
    ("sub", 20, 90, "Low Shelf"),
    ("low_mid", 90, 400, "Bell"),
    ("mid", 400, 3000, "Bell"),
    ("air", 3000, 20000, "High Shelf"),
]


def eq_plan(eq_moves, max_gain=3.0, min_gain=0.75, coherence=0.7):
    """eq_moves: [{"hz", "move_db"}, ...] from references.compare_to_profile.
    Returns EQ bands [{"type", "hz", "gain_db", "q", "region", "bands"}].

    Within a region only the dominant direction is acted on (a 400 Hz excess next to an
    800-1600 Hz dip must not become one bell that lifts both), and a region whose bands
    point both ways without a clear majority (`coherence` of the total move) is left
    alone: that pattern is an instrument's signature, not a tilt to correct."""
    plan = []
    for name, lo, hi, ftype in REGIONS:
        sel = [{"hz": float(m["hz"]), "move_db": float(m["move_db"])} for m in eq_moves
               if lo <= m["hz"] < hi]
        if not sel:
            continue
        up = sum(m["move_db"] for m in sel if m["move_db"] > 0)
        down = -sum(m["move_db"] for m in sel if m["move_db"] < 0)
        if max(up, down) < coherence * (up + down):
            continue
        sel = [m for m in sel if (m["move_db"] > 0) == (up >= down)]
        gain = sum(m["move_db"] for m in sel) / len(sel)
        if abs(gain) < min_gain:
            continue
        gain = max(-max_gain, min(max_gain, gain))
        if ftype == "Low Shelf":
            hz = max(m["hz"] for m in sel) * 1.26
        elif ftype == "High Shelf":
            hz = min(m["hz"] for m in sel) / 1.26
        else:
            hz = math.exp(sum(math.log(m["hz"]) for m in sel) / len(sel))
        octaves = math.log2(max(m["hz"] for m in sel) / min(m["hz"] for m in sel)) + 1 / 3.0
        q = 0.71 if ftype.endswith("Shelf") else max(0.4, min(2.0, 1.4 / octaves))
        plan.append({"region": name, "type": ftype, "hz": round(hz, 1),
                     "gain_db": round(gain, 1), "q": round(q, 2),
                     "bands": [m["hz"] for m in sel]})
    return plan


def loudness_move(current_lufs, current_crest, profile, max_step=4.0):
    """dB of extra limiter drive toward the profile's median loudness, held back so the
    crest factor does not drop below the references' lower quartile."""
    L = profile["loudness"]
    target = L["integrated_lufs"]["median"]
    move = target - current_lufs
    crest_floor = L["crest_db"]["p25"] if L.get("crest_db") else None
    if crest_floor is not None and move > 0:
        # roughly one dB of crest is lost per dB of extra limiting
        move = min(move, max(0.0, current_crest - crest_floor))
    return round(max(-max_step, min(max_step, move)), 1)


def eq_eight_commands(track, device, plan):
    """Bridge commands that set EQ Eight bands 2-7 to the plan and switch every other
    band off, band 1 included: a user's default EQ Eight preset often carries a
    high-pass there, and the EQ should do exactly what the plan says."""
    cmds = [{"cmd": "set_param", "args": {"track": track, "device": device,
                                          "param": "1 Filter On A", "value": 0}}]
    for i, band in enumerate(plan[:6]):
        n = i + 2
        cmds += [
            {"cmd": "set_param", "args": {"track": track, "device": device,
                                          "param": "%d Filter On A" % n, "value": 1}},
            {"cmd": "set_param", "args": {"track": track, "device": device,
                                          "param": "%d Filter Type A" % n, "item": band["type"]}},
            {"cmd": "set_param", "args": {"track": track, "device": device,
                                          "param": "%d Frequency A" % n, "display": band["hz"]}},
            {"cmd": "set_param", "args": {"track": track, "device": device,
                                          "param": "%d Gain A" % n, "display": band["gain_db"]}},
            {"cmd": "set_param", "args": {"track": track, "device": device,
                                          "param": "%d Q A" % n, "display": band["q"]}},
        ]
    for n in range(2 + len(plan[:6]), 9):
        cmds.append({"cmd": "set_param", "args": {"track": track, "device": device,
                                                  "param": "%d Filter On A" % n, "value": 0}})
    return cmds


def toward_profile(path, genre, apply=False, ceiling=-1.5, call=None):
    """Compare a rendered mix with a genre profile and, with apply=True, move the Live
    master toward it: an EQ Eight right after the master's first device (before the bus
    compressor and limiter) with the planned bands, Pro-L 2 Gain by the loudness move,
    and the limiter ceiling."""
    from . import client, knowledge, references
    call = call or client.call
    prof = knowledge.load_profile(genre)
    if not prof:
        raise ValueError("no profile for %r; build it with scripts/build_profile.py" % genre)
    cmp_ = references.compare_to_profile(path, prof)
    plan = eq_plan(cmp_["eq_moves"])
    L = cmp_["loudness"]
    move = loudness_move(L["integrated_lufs"], L["crest_db"], prof)
    report = {"notes": cmp_["notes"], "eq_moves": cmp_["eq_moves"], "eq_plan": plan,
              "loudness_now": L, "limiter_move_db": move,
              "profile_lufs": prof["loudness"]["integrated_lufs"],
              "profile_crest": prof["loudness"]["crest_db"], "applied": False}
    if not apply:
        return report
    names = lambda: [d["name"] for d in call("get_track", {"track": "master",
                                                            "clips": False})["devices"]]
    if "EQ Eight" not in names():
        call("load_device", {"track": "master", "path": "audio_effects/EQ Eight"})
    call("move_device", {"track": "master", "device": names().index("EQ Eight"), "position": 1})
    res = call("batch", {"commands": eq_eight_commands("master", "EQ Eight", plan)})
    report["eq_errors"] = [r for r in res if not r["ok"]][:3]
    params = call("get_device", {"track": "master", "device": "Pro-L 2"})["params"]
    cur = next(p for p in params if p["name"] == "Gain")
    cur_db = float(cur["display"].replace("dB", "").replace("+", "").strip())
    call("set_param", {"track": "master", "device": "Pro-L 2", "param": "Gain",
                       "display": round(cur_db + move, 2)})
    call("set_param", {"track": "master", "device": "Pro-L 2", "param": "Output Level",
                       "display": ceiling})
    report.update({"applied": True, "master_chain": names(),
                   "limiter_gain_db": [cur_db, round(cur_db + move, 2)], "ceiling_db": ceiling})
    return report
