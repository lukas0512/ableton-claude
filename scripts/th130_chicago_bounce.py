"""Reversible Chicago-stab/sub-bounce pass for the inspected TH130 arrangement.

Extends the user's GRID bass timbre by fitting its stable harmonic cycle, rather
than repeating its decaying attack. Keeps the complete 128-bar arrangement.
"""
import json
import os
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.ear import midi
from develop_th130_track import SECTIONS

SR, BPM = 44100, 130
BEAT = 60 / BPM
OUT = Path.home() / 'Music/Ableton/User Library/Samples/Codex/TH130 Chicago Bounce 2026-10-16'
OLD = OUT.parent / 'TH130 Pista V2 2026-10-16'
INDEX = json.loads((Path(__file__).resolve().parents[1] / 'knowledge/samples_index.json').read_text())['items']
ASSETS, NOTES, LOG, SOURCES = [], [], [], {}
# The same two-bar identity returns throughout. Long notes create weight; short
# notes and the ends of the long notes supply the bounce. Times are beats.
PATTERN = [(23, .5, 1.43, 108), (23, 2.775, .20, 84), (30, 3.5, .28, 90),
           (23, 4.275, 1.52, 104), (23, 6.5, .94, 100), (23, 7.775, .17, 79)]


def read(name):
    p = next(r['path'] for r in INDEX if os.path.basename(r['path']) == name and os.path.isfile(r['path']))
    SOURCES[name] = p
    return loops.read(p).astype(np.float32)


def filter_audio(x, hz, kind):
    return signal.sosfilt(signal.butter(2, hz, kind, fs=SR, output='sos'), x, axis=0).astype(np.float32)


def edge(x, attack=.004, release=.025):
    x = x.copy()
    a, b = min(len(x), round(attack * SR)), min(len(x), round(release * SR))
    x[:a] *= np.linspace(0, 1, a)[:, None]
    x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def put(y, x, beat, gain=1):
    i = round(beat * BEAT * SR)
    n = min(len(x), len(y) - i)
    if n > 0:
        y[i:i+n] += x[:n] * gain


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    (OUT / 'live-changes.json').write_text(json.dumps(LOG, ensure_ascii=False, indent=2))
    return r


def main():
    song = client.call('get_song')
    assert song['tempo'] == BPM and any(t['name'] == 'TH130 V2 Bass' for t in song['tracks'])
    assert not any(t['name'].startswith('TH130 Chicago ') for t in song['tracks']), 'Inspect existing pass before editing.'
    OUT.mkdir(parents=True, exist_ok=True)
    before = {name: client.call('get_track', dict(track=name, clips=True)) for name in
              ['TH130 V2 Bass', 'TH130 V2 Lead', 'TH130 V2 Chords', 'TH130 V2 Vocal']}
    (OUT / 'before.json').write_text(json.dumps(dict(song=song, tracks=before), ensure_ascii=False, indent=2))
    bass = read('Odd Frequency - Grid Vol 2 - Bass Shot 2 - B.wav').mean(axis=1)
    # Estimate complex amplitudes from the stable body; lowering an octave makes
    # B0 the sub root. A parallel octave from the same cycle preserves audibility.
    t = np.arange(round(.035 * SR), round(.12 * SR)) / SR
    f = 440 * 2 ** ((35 - 69) / 12)
    basis = np.column_stack([fn(2*np.pi*f*h*t) for h in range(1, 9) for fn in (np.sin, np.cos)])
    coeff = np.linalg.lstsq(basis, bass[round(.035*SR):round(.12*SR)], rcond=None)[0]

    def held(pitch, duration):
        time = np.arange(round(duration * BEAT * SR)) / SR
        freq = 440 * 2 ** ((pitch - 69) / 12)
        y = np.zeros(len(time))
        for h in range(1, 9):
            y += (coeff[2*(h-1)]*np.sin(2*np.pi*freq*h*time) + coeff[2*(h-1)+1]*np.cos(2*np.pi*freq*h*time))
        # Same timbre one octave up, quiet enough to leave the sub in charge.
        for h in range(1, 5):
            y += .42 * (coeff[2*(h-1)]*np.sin(2*np.pi*freq*2*h*time) + coeff[2*(h-1)+1]*np.cos(2*np.pi*freq*2*h*time))
        y /= max(abs(y).max(), 1e-9)
        y *= .84 + .16*np.exp(-time/.07)
        return edge(np.repeat(y[:, None], 2, axis=1).astype(np.float32), .008, .045 if duration > .5 else .018)

    stab = read('PL_DTP2_Reveal_Sample_ChicagoKey_G3.wav')
    stab = filter_audio(stab, 160, 'highpass')
    # Spectral inspection: G/Bb/D source chord, slightly flat. G minor -> B minor.
    ratio = 2 ** ((4 + .15) / 12)
    stab = signal.resample_poly(stab, 10000, round(10000 * ratio), axis=0).astype(np.float32)
    stab = filter_audio(stab, 5100, 'lowpass')
    stab /= max(float(abs(stab).max()), 1e-9)

    for start, end, label, kind in SECTIONS:
        bars = end-start
        n = round(bars*4*BEAT*SR)
        strong = kind in ('drop', 'final')
        audio = {role: np.zeros((n, 2), np.float32) for role in ('Sub Bounce', 'Stabs')}
        if kind in ('groove', 'hook', 'drop', 'final', 'outro'):
            for block in range(bars//2):
                for pitch, onset, length, vel in PATTERN:
                    at = block*8+onset
                    if kind == 'outro' and at >= 16:
                        continue
                    if kind not in ('drop', 'final') and at+length > bars*4-1:
                        continue
                    # Last phrase breathes without changing the remembered motif.
                    if block % 4 == 3 and onset >= 6.5:
                        continue
                    put(audio['Sub Bounce'], held(pitch, length), at, (.19 if strong else .175)*vel/108)
                    NOTES.append([pitch, start*4+at, length, vel])
            # Pocket around the actual quarter-note kick: fast clearance followed
            # by a smooth recovery, instead of a long wash of pumping.
            phase = (np.arange(n)/SR) % BEAT
            recovery = np.clip((phase-.025)/.145, 0, 1)
            duck = .28+.72*recovery**.7
            # Start the attenuation six milliseconds before each kick so that
            # the envelope is continuous across the beat boundary.
            pre = np.clip((phase-(BEAT-.006))/.006, 0, 1)
            duck *= 1-.72*(.5-.5*np.cos(np.pi*pre))
            audio['Sub Bounce'] *= duck[:, None]
        if kind in ('intro', 'groove', 'hook', 'drop', 'final', 'break', 'build', 'build2', 'air'):
            for pair in range(bars//2):
                at = pair*8
                if kind == 'intro' and pair != 3:
                    continue
                if kind == 'groove' and pair % 4 != 3:
                    continue
                if kind in ('hook', 'drop', 'final') and pair % 4 in (0, 2):
                    continue  # first two bars are for the vocal call
                if kind in ('break', 'air') and pair not in (1,):
                    continue
                hits = [(1.5, .82), (4.275, 1.), (6.5, .88)]
                if kind in ('build', 'build2'):
                    hits = [(1.5, .65), (6.5, .76)] if pair < 2 else [(1.5, .8), (4.275, .88), (5.5, .83), (6.5, .95)]
                for onset, vel in hits:
                    if at+onset >= bars*4-1:
                        continue
                    dur = .19 if strong else .15
                    shot = edge(stab[:round(dur*SR)], .002, .035)
                    if kind in ('build', 'build2'):
                        shot = filter_audio(shot, 1100+pair*950, 'lowpass')
                    g = .17 if strong else .12 if kind in ('hook', 'groove') else .09
                    put(audio['Stabs'], shot, at+onset, g*vel)
                    # Small filtered room/delay answer; dry attack stays forward.
                    put(audio['Stabs'], filter_audio(shot, 2400, 'lowpass'), at+onset+.75, g*vel*.14)
        for role, x in audio.items():
            if abs(x).max() < 1e-8:
                continue
            p = OUT / f'{start+1:03d}_{role.replace(" ", "_")}_{kind}.wav'
            sf.write(p, edge(x, .001, .008), SR, subtype='PCM_24')
            ASSETS.append(dict(role=role, path=str(p), bar=start+1, kind=kind, bars=bars,
                               peak_db=float(20*np.log10(abs(x).max())), rms_db=float(20*np.log10(np.sqrt(np.mean(x*x))))))
    midi.write(str(OUT/'Sub Bounce - B minor 130.mid'), [('Sub Bounce', 0, NOTES)], BPM)
    (OUT/'arrangement.json').write_text(json.dumps(dict(bpm=BPM, key='B minor', pattern=PATTERN, sources=SOURCES, assets=ASSETS), ensure_ascii=False, indent=2))
    print('PREPARED', [(a['bar'], a['role'], round(a['rms_db'],1)) for a in ASSETS], flush=True)
    C('transport', action='stop')
    C('set_loop', on=False)
    for role in ('Sub Bounce', 'Stabs'):
        name = 'TH130 Chicago '+role
        C('create_track', kind='audio', name=name)
        C('set_track', track=name, monitoring='off', arm=False, volume_db=0, pan=0)
        if role == 'Sub Bounce':
            C('set_param', track=name, device=0, param='1 Frequency A', display='20 Hz')
        else:
            C('set_send', track=name, send=0, db=-27)
        for a in ASSETS:
            if a['role'] == role:
                C('create_audio_clip', track=name, path=a['path'], bar=a['bar'], warp=False, gain_db=0,
                  name=role+' | '+a['kind'])
    for name in ('TH130 V2 Bass', 'TH130 V2 Lead', 'TH130 V2 Chords'):
        C('set_track', track=name, mute=True)
    # Existing vocal stays as the call; reduced room places it closer to the groove.
    C('set_send', track='TH130 V2 Vocal', send=0, db=-22)
    (OUT/'after.json').write_text(json.dumps(client.call('get_song'), ensure_ascii=False, indent=2))
    (OUT/'Production notes.md').write_text('130 BPM, B minor, complete 128-bar arrangement preserved.\n\n'
        'Bass: GRID II bass-shot harmonic body, lowered to B0 with a quiet octave for translation; '
        'mono, 8 ms attack, long 1.43/1.52/0.94 beat notes and short 0.17–0.28 beat answers. '
        'Six-note two-bar identity, one phrase ending removed every eight bars. Kick recovery 170 ms.\n\n'
        'Stabs: user pack Reveal ChicagoKey G minor one-shot transposed +4.15 semitones, '
        'short gates and sparse two-bar answers. Old Bass/Lead/Chords retained muted. '
        'Vocal room send reduced from -15 to -22 dB. Master left as inspected.\n')
    print('READY', str(OUT), flush=True)


if __name__ == '__main__':
    main()
