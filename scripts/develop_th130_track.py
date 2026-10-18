"""Develop TH130 into a 128-bar track; archive the original as muted tracks.

All source audio is from the user's discovered packs. Decisions are rendered into
section stems; melodic MIDI, sources, section levels and every Live change are kept.
"""
import gc
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.ear import midi
from ableton_claude.music import club, groove

SR, BPM = 44100, 130
BEAT = 60 / BPM
OUT = Path.home() / 'Music/Ableton/User Library/Samples/Codex/TH130 Pista V2 2026-10-16'
INDEX = json.loads((Path(__file__).resolve().parents[1] / 'knowledge/samples_index.json').read_text())
NAMES = ['Kick', 'Clap', 'Hats', 'Perc', 'Bass', 'Vocal', 'Lead', 'Chords', 'Atmos', 'Build', 'FX']
SECTIONS = [
    (0, 8, 'INTRO - hint and pulse', 'intro'),
    (8, 24, 'GROOVE - establish bass identity', 'groove'),
    (24, 40, 'HOOK - voice calls synth answers', 'hook'),
    (40, 48, 'BREAK - voice space and harmony', 'break'),
    (48, 56, 'BUILD I - open and withhold', 'build'),
    (56, 80, 'DROP I - weight and response', 'drop'),
    (80, 88, 'AIR - keep the thread', 'air'),
    (88, 96, 'BUILD II - vocal anticipation', 'build2'),
    (96, 120, 'DROP II - expanded final answer', 'final'),
    (120, 128, 'OUTRO - hand back to the DJ', 'outro'),
]
SOURCES, ASSETS, LOG, LEAD_MIDI = {}, [], [], []


def C(cmd, **args):
    result = server._journaled(cmd, args)
    LOG.append({'cmd': cmd, 'args': args, 'result': result})
    (OUT / 'live-changes.json').write_text(json.dumps(LOG, ensure_ascii=False, indent=1))
    return result


def read(name):
    p = next(r['path'] for r in INDEX['items'] if os.path.basename(r['path']) == name and os.path.isfile(r['path']))
    SOURCES[name] = p
    return loops.read(p).astype(np.float32)


def edge(x, attack=.002, release=.02):
    x = np.asarray(x, np.float32).copy()
    for n, sl, ramp in [(min(len(x), round(attack * SR)), 'a', True),
                        (min(len(x), round(release * SR)), 'b', False)]:
        if n:
            x[:n] *= np.linspace(0, 1, n)[:, None] if ramp else 1
            if not ramp:
                x[-n:] *= np.linspace(1, 0, n)[:, None]
    return x


def put(y, x, beat, gain=1., pan=0.):
    a = round(beat * BEAT * SR)
    if a < 0 or a >= len(y):
        return
    n = min(len(x), len(y) - a)
    y[a:a+n] += x[:n] * gain * np.array([min(1., 1-pan), min(1., 1+pan)], np.float32)


def filt(x, hz, kind='lowpass'):
    return signal.sosfilt(signal.butter(2, hz, kind, fs=SR, output='sos'), x, axis=0).astype(np.float32)


PITCHED = {}
def pitched(x, source_pitch, pitch, seconds):
    key = (id(x), source_pitch, pitch)
    if key not in PITCHED:
        ratio = 2 ** ((pitch - source_pitch) / 12)
        PITCHED[key] = signal.resample_poly(x, 1000, round(1000 * ratio), axis=0).astype(np.float32)
    return edge(PITCHED[key][:round(seconds * SR)], .003, .025)


def echo_into(y, x, beat, gain, pan=0.):
    put(y, x, beat, gain, pan)
    for n in range(1, 5):
        put(y, filt(x, 2600), beat + n * .75, gain * .27 ** n, (-1 if n % 2 else 1) * .28)


def prepare():
    kick = read('3Q_TT2_Kick_09.wav')
    clap = read('3Q_TT2_Clap_02.wav')
    hats = read('3Q_TT2_Hat_14.wav')
    openhat = read('3Q_TT2_Hat_01.wav')
    perc = read('3Q_TT2_Perc_09.wav')
    snare = read('Odd Frequency - Grid Vol 2 - Clap_Snare 20.wav')
    bass = read('Odd Frequency - Grid Vol 2 - Bass Shot 2 - B.wav')
    synth = read('Odd Frequency - Grid Vol 2 - Synth Shot 15 - B.wav')  # measured B3
    vox = filt(read('Odd Frequency - Grid Vol 2 - Vocal Phrase Dry 1 - 130 BPM.wav'), 150, 'highpass')
    vox_alt = filt(read('Odd Frequency - Grid Vol 2 - Vocal Phrase Dry 4 - 130 BPM.wav'), 160, 'highpass')
    texture = filt(read('Odd Frequency - Grid Vol 2 - Texture 1 - 130 BPM.wav'), 450, 'highpass')
    sweep = filt(read('Odd Frequency - Grid Vol 2 - Short Sweep 3.wav'), 400, 'highpass')
    down = filt(read('Odd Frequency - Grid Vol 2 - Downlifter 9 - 129BPM.wav'), 350, 'highpass')
    call = edge(vox[:round(8 * BEAT * SR)], .003, .04)
    short_call = edge(vox_alt[:round(4 * BEAT * SR)], .003, .04)
    # A repeatable answer: descending F#-D-B, a short question, then tonic closure.
    answer = [(66, 8.25, .35, 103), (62, 9., .5, 96), (59, 10., .65, 108),
              (62, 11.25, .25, 84), (61, 12.5, .45, 94), (59, 13.5, .9, 106)]
    last_answer = [(66, 8.25, .35, 104), (69, 9., .4, 96), (66, 9.75, .4, 99),
                   (64, 10.5, .45, 95), (62, 12., .5, 94), (59, 13.5, 1., 110)]
    bass_motif = club.motif(tonic='B', bars=8, swing=55, seed=17, articulation='sustained', development='evolving')['notes']
    kit = groove.pattern('tech_house', bars=8, swing=55, seed=17)
    section_rows = []
    for start, end, label, kind in SECTIONS:
        bars = end - start
        n = round(bars * 4 * BEAT * SR)
        s = {name: np.zeros((n, 2), np.float32) for name in NAMES}
        strong = kind in ('drop', 'final')
        no_low = kind in ('break', 'build', 'build2', 'air')
        for b in range(bars):
            for part, shot, dest, level in [('kick', kick, 'Kick', .64), ('clap', clap, 'Clap', .57),
                                            ('closed_hat', hats, 'Hats', .27), ('open_hat', openhat, 'Hats', .24),
                                            ('rim', perc, 'Perc', .39)]:
                for _, onset, _, vel in kit[part]:
                    if int(onset // 4) != b % 8:
                        continue
                    t = b * 4 + onset % 4
                    if part == 'kick':
                        t = b * 4 + round(onset % 4)
                        if no_low or (kind == 'intro' and b < 4) or (b == bars - 1 and kind not in ('drop', 'final') and t % 4 >= 3):
                            continue
                    if kind == 'intro' and part in ('rim', 'open_hat') and b < 4:
                        continue
                    if kind in ('build', 'build2') and b == bars - 1 and t % 4 >= 3:
                        continue
                    if kind == 'outro' and b >= 6 and part in ('rim', 'open_hat'):
                        continue
                    g = .55 if no_low else .78 if kind == 'intro' else 1.
                    if strong and b >= 8 and part == 'open_hat':
                        g *= 1.18
                    if part == 'clap':
                        t += .009
                    put(s[dest], shot, t, level * g * vel / 110, .1 if part == 'rim' else 0)
            if strong and b % 8 == 7:
                for step, v in [(13, .20), (14, .26), (15, .34)]:
                    put(s['Perc'], perc, b * 4 + step / 4 + groove.swing_offset(step, 55), v, -.18)
        if not no_low and kind != 'intro':
            for block in range((bars + 7) // 8):
                for pitch, t, dur, vel in bass_motif:
                    t += block * 32
                    if t >= bars * 4 or (kind == 'outro' and t >= 16):
                        continue
                    if kind not in ('drop', 'final') and t > bars * 4 - 1.5:
                        continue
                    note = pitched(bass, 35, pitch, dur * BEAT)
                    note = filt(note.mean(axis=1, keepdims=True).repeat(2, axis=1), 1700 if strong else 1100)
                    body = filt(filt(np.tanh(note * 2.2), 140, 'highpass'), 1800)
                    note = note + body * (.13 if strong else .07)
                    put(s['Bass'], note, t, (.74 if strong else .68) * vel / 100)
        # Vocal calls occupy the first half of a four-bar phrase. Melody answers in
        # the second half; neither is a continuous competing loop.
        if kind in ('hook', 'drop', 'final', 'break', 'air'):
            for phrase in range(bars // 4):
                at = phrase * 16
                if kind in ('drop', 'final') and phrase % 3 == 2:
                    continue  # one phrase of pure groove makes the hook's return matter
                voice = short_call if phrase % 2 else call
                echo_into(s['Vocal'], voice, at, .76 if kind in ('break', 'air') else .72, -.025)
                seq = last_answer if kind == 'final' and phrase % 2 else answer
                for p, t, dur, vel in seq:
                    note = pitched(synth, 59, p, dur * BEAT)
                    echo_into(s['Lead'], note, at + t, .79 * vel / 110, .04)
                    LEAD_MIDI.append([p, start * 4 + at + t, dur, vel])
        elif kind == 'groove':
            for phrase in (0, 2):
                echo_into(s['Vocal'], short_call, phrase * 16, .55)
                for p, t, dur, vel in answer[:3]:
                    echo_into(s['Lead'], pitched(synth, 59, p, dur * BEAT), phrase * 16 + t, .53 * vel / 110)
        elif kind == 'intro':
            echo_into(s['Vocal'], short_call, 24, .30)
        if kind in ('build', 'build2'):
            for bar in (0, 2, 4):
                echo_into(s['Vocal'], short_call, bar * 4, .66 + bar * .025)
            # One complete short call before the last beat's gap.
            echo_into(s['Vocal'], short_call, 24, .84)
            roll = groove.build_roll(bars=bars, vel_from=36, vel_to=110, gap_last_beat=True)
            for _, t, _, vel in roll:
                note = snare[:round(min(.18, BEAT * .4) * SR)]
                put(s['Build'], edge(note, .002, .015), t, .29 * vel / 127)
            for b in range(bars):
                start_at = round(b * 4 * BEAT * SR)
                ns = round(4 * BEAT * SR)
                raw = np.tile(texture, (3, 1))[:ns]
                bright = filt(raw, 900 + (b / max(1, bars - 1)) * 6500)
                put(s['Build'], bright, b * 4, .10 + .025 * b)
                for k in range(4 if b < 4 else 8):
                    t = b * 4 + k * (1 if b < 4 else .5)
                    if t >= bars * 4 - 1:
                        continue
                    note = filt(pitched(synth, 59, 66, .13), 1100 + b * 650)
                    put(s['Build'], note, t, .12 + b * .018)
            stop = round((bars * 4 - 1) * BEAT * SR)
            for name in ('Hats', 'Clap', 'Perc', 'Build', 'Vocal', 'Atmos'):
                s[name][:stop] = edge(s[name][:stop], .002, .03)
                s[name][stop:] = 0
            reverse = edge(short_call[::-1], .03, .01)
            put(s['FX'], reverse, bars * 4 - 5, .23)
        # Upper chord shells add body without doubling the sub. Harmonic motion is
        # disclosed in the break; dominant sus before the downbeat resolves to B minor.
        if kind not in ('intro', 'outro'):
            for b in range(0, bars, 2):
                chord = [62, 66, 69]  # rootless Bm7
                if kind in ('break', 'air') and b >= bars // 2:
                    chord = [62, 66, 67, 71]  # Gmaj7 colour
                if kind in ('build', 'build2') and b >= 4:
                    chord = [61, 64, 66, 71]  # F#7sus4 upper structure
                for p in chord:
                    note = pitched(synth, 59, p, .85)
                    note = filt(note, 1800 if strong else 1100)
                    put(s['Chords'], note, b * 4 + 2.5, .16 if strong else .22, .12 * ((p % 3) - 1))
        for b in range(0, bars, 8):
            amp = .26 if no_low else .08 if strong else .13
            put(s['Atmos'], edge(texture, .6, 1.), b * 4, amp)
        if strong:
            put(s['FX'], edge(down[:round(8 * BEAT * SR)], .002, .35), 0, .20)
            put(s['FX'], sweep, 0, .17)
        elif kind in ('break', 'air'):
            put(s['FX'], sweep, 0, .14)
        elif kind in ('intro', 'outro'):
            put(s['FX'], edge(sweep[::-1], .02, .02), max(0, bars * 4 - 3), .12)
        if kind == 'outro':
            for name in s:
                s[name][-round(2 * BEAT * SR):] *= np.linspace(1, 0, round(2 * BEAT * SR))[:, None]
        mix = np.zeros((n, 2), np.float32)
        for name, audio in s.items():
            if np.max(np.abs(audio)) < 1e-8:
                continue
            p = OUT / f'{start+1:03d}_{name}_{kind}.wav'
            sf.write(p, edge(audio, .001, .008), SR, subtype='FLOAT')
            ASSETS.append({'name': name, 'path': str(p), 'start': start + 1, 'end': end + 1, 'label': label})
            mix += audio
        p = OUT / f'mix_{start+1:03d}.wav'
        sf.write(p, mix, SR, subtype='FLOAT')
        section_rows.append({'name': label, 'start_bar': start + 1, 'end_bar': end + 1,
                             'lufs_untrimmed': round(float(pyln.Meter(SR).integrated_loudness(mix)), 2),
                             'peak': float(np.max(np.abs(mix))), 'path': str(p)})
        print('PREPARED', label, section_rows[-1]['lufs_untrimmed'], flush=True)
        del s, mix
        gc.collect()
    peak = max(r['peak'] for r in section_rows)
    trim = min(1., 10 ** (-3 / 20) / peak)
    for asset in ASSETS:
        audio, sr = sf.read(asset['path'], always_2d=True, dtype='float32')
        sf.write(asset['path'], audio * trim, sr, subtype='PCM_24')
    with sf.SoundFile(OUT / 'TH130 V2 Premaster.wav', mode='w', samplerate=SR, channels=2, subtype='PCM_24') as f:
        for r in section_rows:
            audio, _ = sf.read(r['path'], always_2d=True, dtype='float32')
            f.write(audio * trim)
            r['lufs_trimmed'] = round(r['lufs_untrimmed'] + 20 * math.log10(trim), 2)
    midi.write(str(OUT / 'Lead - vocal response B minor.mid'), [('Lead response', 0, LEAD_MIDI)], BPM)
    (OUT / 'sources.json').write_text(json.dumps(SOURCES, ensure_ascii=False, indent=2))
    (OUT / 'arrangement.json').write_text(json.dumps({'sections': section_rows, 'trim_db': 20 * math.log10(trim), 'assets': ASSETS}, ensure_ascii=False, indent=2))
    print('SECTION_LEVELS', json.dumps([{k:r[k] for k in ('name','lufs_trimmed')} for r in section_rows]), flush=True)


def main():
    song = client.call('get_song')
    if song['tempo'] != BPM or not any(t['name'] == 'TH130 Bass' for t in song['tracks']):
        raise RuntimeError('Expected the inspected TH130 project at 130 BPM.')
    if any(t['name'].startswith('TH130 V2 ') for t in song['tracks']):
        raise RuntimeError('V2 already exists: inspect rather than duplicate.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'before-song.json').write_text(json.dumps(song, ensure_ascii=False, indent=2))
    prepare()
    C('transport', action='stop')
    C('set_loop', on=False)
    for t in song['tracks']:
        if t['name'].startswith('TH130 '):
            C('set_track', track=t['name'], mute=True)
    for cue in song['cues']:
        if cue['name'].startswith('TH130 - '):
            C('delete_cue', name=cue['name'])
    for name in NAMES:
        track = 'TH130 V2 ' + name
        C('create_track', kind='audio', name=track)
        C('set_track', track=track, volume_db=0, monitoring='off', arm=False, pan=0)
        send = {'Vocal': -15, 'Lead': -18, 'Chords': -21, 'Atmos': -17}.get(name)
        if send is not None:
            C('set_send', track=track, send=0, db=send)
        for asset in [a for a in ASSETS if a['name'] == name]:
            C('create_audio_clip', track=track, path=asset['path'], bar=asset['start'],
              warp=False, gain_db=0, name=name + ' | ' + asset['label'])
        print('LIVE_TRACK', track, 'ready', flush=True)
    for start, end, label, kind in SECTIONS:
        C('set_cue', name='V2 ' + label, bar=start + 1)
    # Preserve the existing limiter, then inspect its readback and render the result.
    print('MASTER', json.dumps(client.call('get_device', {'track':'master','device':0})), flush=True)
    (OUT / 'after-song.json').write_text(json.dumps(client.call('get_song'), ensure_ascii=False, indent=2))
    print('READY_FOR_RENDER', str(OUT), flush=True)


if __name__ == '__main__':
    main()
