"""Let The Rhythm v8: ear candies for the builds and drops, made from the track's own material.

prepare: renders the WAVs (reversed vocal swells, reverse cymbals, F# sub booms, vocal
throws with a baked 3/16 ping-pong echo) into the project's Samples/Claude folder.
apply: two new audio tracks (FX - transitions, VOX - throws) and the build-1 stab
acceleration, all through the journaled bridge.
"""
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import server

SR, BPM = 44100, 127
BEAT = 60 / BPM
BAR = 4 * BEAT
PROJECT = Path.home() / 'Desktop/Projects 26:27/Let The Rhythm Project'
OUT = PROJECT / 'Samples/Claude/LTR v8 earcandy'
VOX = PROJECT / 'Samples/Imported/T_TSMK7_124_vocal_phrase_loop_female_lift_your_hands_wet_Fm.wav'
PACKS = Path.home() / 'Documents/Documents - Lukas’s MacBook Pro/SAMPÇE Packs'
REVCYM = PACKS / 'Loopmasters - Ultimate Deep House/SOUNDS_&_FX/FX/TG_ReverseCymbal1.wav'
LOG = []


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    (OUT / 'changes.json').write_text(json.dumps(LOG, indent=2, default=str))
    print(cmd, str(r)[:150], flush=True)
    return r


def read(p):
    x, sr = sf.read(p, always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    if sr != SR:
        x = signal.resample_poly(x, SR, sr, axis=0)
    return x


def filt(x, hz, kind):
    return signal.sosfilt(signal.butter(2, hz, kind, fs=SR, output='sos'), x, axis=0)


def fade(x, a=.003, b=.02):
    x = x.copy()
    na, nb = min(len(x), round(a * SR)), min(len(x), round(b * SR))
    if na: x[:na] *= np.linspace(0, 1, na)[:, None]
    if nb: x[-nb:] *= np.linspace(1, 0, nb)[:, None]
    return x


def peak(x, db):
    return x * 10 ** (db / 20) / max(float(np.abs(x).max()), 1e-9)


def vocal():
    """The loop up a semitone (the set plays it at +1 st), by repitch."""
    x = read(VOX)
    return signal.resample_poly(x, 1000, round(1000 * 2 ** (1 / 12)), axis=0)


def reverb(x, secs=2.4, seed=1):
    rng = np.random.default_rng(seed)
    n = round(secs * SR)
    ir = rng.standard_normal((n, 2)) * np.exp(-np.arange(n) / (secs * SR / 6.9))[:, None]
    ir = filt(filt(ir, 300, 'highpass'), 7000, 'lowpass')
    return np.stack([signal.fftconvolve(x[:, c], ir[:, c]) for c in range(2)], 1)


def canvas(bars):
    return np.zeros((round(bars * BAR * SR), 2))


def put(y, x, t, g=1.0):
    a = round(t * SR)
    if a < 0:
        x, a = x[-a:], 0
    n = min(len(x), len(y) - a)
    if n > 0:
        y[a:a + n] += x[:n] * g


def rev_cymbal(db):
    x = read(REVCYM)
    env = np.abs(x).mean(1)
    pk = int(np.argmax(signal.lfilter(np.ones(441) / 441, 1, env)))
    return peak(fade(x[:pk + round(.01 * SR)], .05, .008), db)


def rev_vocal(v):
    st = v[round(.12 * SR / 2 ** (1 / 12)):round(1.98 * SR / 2 ** (1 / 12))]
    wet = reverb(fade(st, .005, .03))
    y = filt(wet, 250, 'highpass')[::-1]
    y = y[-round(2 * BAR * SR):]
    return peak(fade(y, .4, .03), -13)


def boom():
    t = np.arange(round(2.2 * SR)) / SR
    f = 36 + (46.25 - 36) * np.exp(-t / .35)          # F#1 sliding down
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    s = np.tanh(1.8 * s) * np.exp(-t / .75)
    s[:round(.004 * SR)] *= np.linspace(0, 1, round(.004 * SR))
    return peak(np.repeat(s[:, None], 2, 1), -9)


def throw(v):
    """The phrase's last syllable with a baked 3/16 ping-pong echo, darker each repeat."""
    r = 2 ** (1 / 12)
    w = fade(v[round(1.56 * SR / r):round(1.98 * SR / r)], .004, .03)
    y = canvas(2)
    put(y, w, 0)
    d, g, rep = .75 * BEAT, .55, w.copy()
    for k in range(1, 7):
        rep = filt(filt(rep, 3800 - 380 * k, 'lowpass'), 250 + 40 * k, 'highpass')
        side = np.array([1, .35]) if k % 2 else np.array([.35, 1])
        put(y, rep * side, k * d, g ** k)
    y += .18 * reverb(y, 1.6, 3)[:len(y)]
    return peak(fade(y, .002, .2), -10)


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    v = vocal()
    files = {}
    # into a drop: 2 bars before + 2 bars after the downbeat (file starts 2 bars early)
    for name, with_vox, with_boom in [('into drop 81', True, True), ('into drop 117', True, True),
                                      ('into 137', False, False), ('into 157', False, False)]:
        y = canvas(4)
        cym = rev_cymbal(-16)
        put(y, cym, 2 * BAR - len(cym) / SR)
        if with_vox:
            rv = rev_vocal(v)
            put(y, rv, 2 * BAR - len(rv) / SR - .012)
        if with_boom:
            put(y, boom(), 2 * BAR)
        files[name] = OUT / f'LTR {name}.wav'
        sf.write(files[name], y, SR, subtype='PCM_24')
    y = canvas(2)
    cym = rev_cymbal(-22)
    put(y, cym, 2 * BAR - len(cym) / SR)
    sf.write(OUT / 'LTR mid-drop rev cymbal.wav', y, SR, subtype='PCM_24')
    sf.write(OUT / 'LTR vox throw.wav', throw(v), SR, subtype='PCM_24')
    print('written', sorted(p.name for p in OUT.glob('*.wav')))


def stab_build():  # unused while SYNTH STAB stays frozen
    """Build 1 (bars 77-80.5): the stab's own F#m cell accelerating into its 16th pickup."""
    chord = [42, 54, 57, 61, 73]
    hits = [0, 2, 4, 5, 6, 7] + [8 + i * .5 for i in range(8)] + [12 + i * .5 for i in range(4)]
    notes = []
    for k, b in enumerate(hits):
        vel = round(58 + 18 * k / (len(hits) - 1))
        notes += [[p, b, .1348, vel] for p in chord]
    return notes


def apply():
    assert not (OUT / 'changes.json').exists(), 'inspect the partial receipt before a retry'
    st = server.ableton_status()
    idx = next(t['i'] for t in st['tracks'] if t['name'] == 'AMBIENCE - crowd far') + 1
    C('create_track', kind='audio', name='FX - transitions', index=idx)
    C('create_track', kind='audio', name='VOX - throws', index=idx + 1)
    for t in ('FX - transitions', 'VOX - throws'):
        C('set_track_input', track=t, source='No Input')
    C('set_track', track='FX - transitions', volume_db=-3.0)
    C('set_track', track='VOX - throws', volume_db=-14.0)
    for name, bar in [('into drop 81', 81), ('into drop 117', 117), ('into 137', 137), ('into 157', 157)]:
        C('create_audio_clip', track='FX - transitions', path=str(OUT / f'LTR {name}.wav'),
          bar=bar - 2, name=name, warp=True, beats=16)
    for bar in (41, 89, 125, 145):
        C('create_audio_clip', track='FX - transitions', path=str(OUT / 'LTR mid-drop rev cymbal.wav'),
          bar=bar - 2, name=f'rev cymbal mid-drop {bar}', warp=True, beats=8)
    # the last word of a statement, into the echo: phrase ends and the a cappellas before drops
    for beat in (190, 318, 382, 462, 526):
        C('create_audio_clip', track='VOX - throws', path=str(OUT / 'LTR vox throw.wav'),
          beat=beat, name=f'throw {beat / 4 + 1:g}', warp=True, beats=8)
    # SYNTH STAB is frozen (no new MIDI clips): its own 16th pickup cell doubled into bar 80
    C('duplicate_clip', track='SYNTH STAB', clip={'at': 126}, beat=316)


if __name__ == '__main__':
    {'prepare': prepare, 'apply': apply}[sys.argv[1]]()
