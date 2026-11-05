"""Where the vocals actually sound, per 16th of the song: each vocal clip's file read through its warp markers.

Clip spans are not enough (the hooks are 8-bar clips with breaths and gaps inside). For every unmuted clip on the
vocal tracks: RMS per 16th of the clip's own beat grid (warp markers map beats to file seconds), a slot is 'voiced'
when it sits within 30 dB of that clip's loudest 16th and above -50 dBFS. Saved as {slot: track} to vocal_map.json.
"""
from pathlib import Path
import json
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
VOX = ['VOX CITY - calls', 'VOX CITY - hooks', 'VOX CITY - radio', 'VOX MURDER', 'VOX MURDER - trades',
       'VOX - throws', 'MURDER VOX+SCRATCH (drop 2)']
OUT = Path(__file__).resolve().parent / 'vocal_map.json'


def clip_slots(track, c):
    y, sr = sf.read(c['file'], always_2d=True)
    m = y.mean(1)
    ms = c.get('markers') or []
    if not c.get('warping') or len(ms) < 2:
        return {}
    mb = np.array([x['beat'] for x in ms])
    mt = np.array([x['sample_s'] for x in ms])
    sm = c.get('start_marker') or 0.0
    length = c['end'] - c['start']
    out = {}
    levels = []
    for k in range(int(round(length * 4))):
        b0 = sm + k / 4
        t0, t1 = np.interp([b0, b0 + 0.25], mb, mt, left=np.nan, right=np.nan)
        if np.isnan(t0) or np.isnan(t1) or t1 <= t0:
            continue
        seg = m[int(t0 * sr):int(t1 * sr)]
        if len(seg):
            levels.append((k, 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)))
    if not levels:
        return {}
    top = max(l for _, l in levels)
    gain = c.get('gain_db') or 0.0
    for k, l in levels:
        if l > top - 30 and l + gain > -50:
            out[int(round(c['start'] * 4)) + k] = track
    return out


def build():
    voiced = {}
    for t in VOX:
        tr = C('get_track', {'track': t, 'clips': True})
        if tr.get('mute'):
            continue
        for c in tr.get('clips', []):
            if c.get('muted') or c.get('type') != 'audio':
                continue
            info = C('set_clip', {'track': t, 'clip': {'at': c['start']}, 'name': c['name']})
            c = {**c, **{k: info.get(k) for k in ('start_marker',)}}
            if c.get('warping'):
                c['markers'] = C('warp_markers', {'track': t, 'clip': {'at': c['start']}})['markers']
            voiced.update(clip_slots(t, c))
    OUT.write_text(json.dumps({str(k): v for k, v in sorted(voiced.items())}))
    return voiced


if __name__ == '__main__':
    v = build()
    for a, z in ((65, 97), (121, 169)):
        slots = [k for k in v if (a - 1) * 16 <= k < (z - 1) * 16]
        print(f'bars {a}-{z - 1}: voiced {len(slots)} of {(z - a) * 16} 16ths ({100 * len(slots) / ((z - a) * 16):.0f} %)')
    line = ''.join('#' if k in v else '.' for k in range(64 * 16, 80 * 16))
    for b in range(16):
        print(65 + b, line[b * 16:(b + 1) * 16])
