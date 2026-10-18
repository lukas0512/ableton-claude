"""An additive 130 BPM live test, using discovered user-pack samples and club MIDI.

Refuses an occupied set. Original samples are read only; rendered sections and source
provenance stay in the User Library. Live is controlled only through ClaudeBridge.
"""
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.music import club, groove
from ableton_claude.ear import midi

BPM, SR, BARS = 130, 44100, 32
BEAT = 60 / BPM
OUT = Path.home() / 'Music/Ableton/User Library/Samples/Codex/TH130 Pista 2026-10-16'
INDEX = Path(__file__).resolve().parents[1] / 'knowledge/samples_index.json'
SOURCES, EVENTS = {}, []


def C(cmd, **args):
    result = server._journaled(cmd, args)
    EVENTS.append({'cmd': cmd, 'args': args, 'result': result})
    (OUT / 'live-commands.json').write_text(json.dumps(EVENTS, ensure_ascii=False, indent=1))
    print(cmd, str(result)[:140], flush=True)
    return result


def source(name):
    paths = [r['path'] for r in json.loads(INDEX.read_text())['items']
             if os.path.basename(r['path']) == name and os.path.isfile(r['path'])]
    if not paths:
        raise FileNotFoundError(name)
    SOURCES[name] = paths[0]
    return loops.read(paths[0], SR).astype(np.float32)


def put(y, x, at, gain=1.):
    a = round(at * BEAT * SR)
    n = min(len(x), len(y) - a)
    if a >= 0 and n > 0:
        y[a:a+n] += x[:n] * gain


def fade(x, attack=.002, release=.012):
    x = x.copy()
    a, b = min(len(x), round(attack * SR)), min(len(x), round(release * SR))
    if a:
        x[:a] *= np.linspace(0, 1, a)[:, None]
    if b:
        x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def main():
    song = client.call('get_song')
    if any(t['clips'] or t['devices'] for t in song['tracks']) or song['is_playing']:
        raise RuntimeError('This builder requires the inspected empty, stopped set.')
    if any(t['name'].startswith('TH130 ') for t in song['tracks']):
        raise RuntimeError('TH130 already exists; inspect instead of rebuilding.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'before-live.json').write_text(json.dumps(song, indent=2))
    kick = source('3Q_TT2_Kick_09.wav')
    clap = source('3Q_TT2_Clap_02.wav')
    closed = source('3Q_TT2_Hat_14.wav')
    opened = source('3Q_TT2_Hat_01.wav')
    perc = source('3Q_TT2_Perc_09.wav')
    bass = source('Odd Frequency - Grid Vol 2 - Bass Shot 2 - B.wav')
    hook = source('Odd Frequency - Grid Vol 2 - Synth Loop 15 - Bmin - 130 BPM.wav')
    vox = source('Odd Frequency - Grid Vol 2 - Vocal Phrase Dry 1 - 130 BPM.wav')
    names = ['Kick', 'Clap', 'Hats', 'Perc', 'Bass', 'Hook', 'Vox', 'Turnaround']
    stems = {name: np.zeros((round(BARS * 4 * BEAT * SR), 2), np.float32) for name in names}
    drum_notes = groove.pattern('tech_house', 8, 55., seed=17)
    motif = club.motif(tonic='B', bars=8, swing=55., seed=17,
                       articulation='sustained', development='evolving')
    for block in range(4):
        for part, shot, track, gain in [('kick', kick, 'Kick', .63), ('clap', clap, 'Clap', .48),
                                       ('closed_hat', closed, 'Hats', .20), ('open_hat', opened, 'Hats', .19),
                                       ('rim', perc, 'Perc', .32)]:
            for _, onset, duration, velocity in drum_notes[part]:
                t = block * 32 + onset
                bar = int(t // 4)
                if part == 'kick':
                    t = round(t)
                    if 16 <= bar < 24 or (bar in (15, 23, 31) and t % 4 >= 3):
                        continue
                if bar == 23 and t % 4 >= 3:
                    continue
                local_gain = .62 if 16 <= bar < 24 else 1.
                if part == 'clap':
                    t += .009
                put(stems[track], shot, t, gain * local_gain * velocity / 110)
        if block == 2:
            continue
        for pitch, onset, duration, velocity in motif['notes']:
            t = block * 32 + onset
            if int(t // 4) in (15, 31) and t % 4 > 2.5:
                continue
            # The pack shot was measured at MIDI 35 (B1). Resampling makes a sampler
            # transposition; a short fade controls the gate without clicks.
            ratio = 2 ** ((pitch - 35) / 12)
            shifted = signal.resample_poly(bass, 1000, round(1000 * ratio), axis=0)
            n = min(len(shifted), round(duration * BEAT * SR))
            note = fade(shifted[:n], .003, .018)
            note = signal.sosfilt(signal.butter(2, 1500 if block == 3 else 950, fs=SR, output='sos'), note, axis=0)
            put(stems['Bass'], note, t, .68 * velocity / 100)
    # The hook answers, leaving four-bar spaces; its final eight bars open the drop.
    four = round(16 * BEAT * SR)
    for bar in (4, 12, 24, 28):
        part = hook[:four] if bar != 28 else hook[four:four * 2]
        put(stems['Hook'], fade(part, .004, .06), bar * 4, .32 if bar < 24 else .40)
    filtered = signal.sosfilt(signal.butter(2, 1000, fs=SR, output='sos'), hook[:four], axis=0)
    put(stems['Hook'], fade(filtered, .02, .08), 16 * 4, .22)
    for bar in (8, 20):
        put(stems['Vox'], fade(vox, .003, .06), bar * 4, .38)
    # Transitions use this palette: clap acceleration, a reversed clap and space.
    roll = groove.build_roll(bars=2, vel_from=42, vel_to=100)
    for _, t, _, v in roll:
        put(stems['Turnaround'], clap, 22 * 4 + t, .18 * v / 127)
    reverse = fade(clap[::-1], .008, .002)
    put(stems['Turnaround'], reverse, 24 * 4 - len(reverse) / SR / BEAT - .03, .20)
    for name in stems:
        stems[name] = fade(stems[name], .003, .04)
    mix = sum(stems.values())
    peak = float(np.abs(mix).max())
    trim = min(1., 10 ** (-3.0 / 20) / max(peak, 1e-10))
    for name in stems:
        stems[name] *= trim
    (OUT / 'sources.json').write_text(json.dumps(SOURCES, ensure_ascii=False, indent=2))
    (OUT / 'bass-notes.json').write_text(json.dumps(motif, indent=1))
    midi.write(str(OUT / 'Bass B minor 130.mid'), [('TH130 Bass', 0, motif['notes'])], BPM)
    sf.write(OUT / 'TH130-premaster.wav', sum(stems.values()), SR, subtype='PCM_24')
    C('set_tempo', bpm=BPM)
    boundaries = [(0, 8, 'Pocket A'), (8, 16, 'Pocket B - voice'), (16, 20, 'Break - keep motion'),
                  (20, 24, 'Tension - withhold bass'), (24, 32, 'Drop - return')]
    for name, y in stems.items():
        track = 'TH130 ' + name
        C('create_track', kind='audio', name=track)
        C('set_track', track=track, volume_db=0, pan=0, monitoring='off', arm=False)
        for start, end, label in boundaries:
            seg = y[round(start * 4 * BEAT * SR):round(end * 4 * BEAT * SR)]
            if float(np.max(np.abs(seg))) < 1e-8:
                continue
            p = OUT / f'{name}_{start+1:02d}-{end:02d}.wav'
            sf.write(p, seg, SR, subtype='PCM_24')
            C('create_audio_clip', track=track, path=str(p), bar=start + 1,
              name=f'{name} | {label}', warp=False, gain_db=0)
    for bar, label in [(1, 'TH130 - POCKET'), (9, 'TH130 - VOICE ANSWERS'),
                       (17, 'TH130 - BREAK'), (21, 'TH130 - TENSION'), (25, 'TH130 - DROP')]:
        C('set_cue', name=label, bar=bar)
    C('load_device', track='master', path='audio_effects/Limiter')
    print('LIMITER_PARAMETERS', json.dumps(client.call('get_device', {'track': 'master', 'device': 0}), ensure_ascii=False), flush=True)
    print('OFFLINE_PEAK_DB', round(20 * math.log10(np.abs(sum(stems.values())).max()), 2), flush=True)
    (OUT / 'after-live.json').write_text(json.dumps(client.call('get_song'), indent=2))


if __name__ == '__main__':
    main()
