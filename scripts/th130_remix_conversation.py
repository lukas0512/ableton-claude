"""Develop the approved keys/stabs while the user supplies the remix vocal.

No retrieved or provisional vocal is used. Archive the three replaced roles;
leave named spaces for a sung vocal and a different short call from the user's file.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.ear import midi
import th130_house_fit as hf
import th130_string_signature as ss
from th130_arrangement_motion import CHAPTERS, edges, put, sample, silence

SR, BPM, BEAT = 44100, 130, 60 / 130
OUT = Path.home() / 'Music/Ableton/User Library/Samples/Codex/TH130 Remix Conversation 2026-10-16'
LOG, EVENTS, ASSETS = [], [], []


def C(cmd, **args):
    result = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=result))
    (OUT / 'live-changes.json').write_text(json.dumps(LOG, ensure_ascii=False, indent=2))
    return result


def assemble(track, n):
    y = np.zeros((n, 2), np.float32)
    for c in track['clips']:
        if c['muted']:
            continue
        assert not c['warping'] and c['pitch'] == 0 and c['detune'] == 0
        put(y, loops.read(c['file']).astype(np.float32)[:sample(c['length'])],
            c['start'], 10 ** (c['gain_db'] / 20))
    return y


def main():
    song = client.call('get_song')
    assert song['tempo'] == BPM
    assert not any(t['name'].startswith('TH130 Remix ') for t in song['tracks'])
    assert not any(t['name'].startswith('VAMPIRO ') for t in song['tracks'])
    OUT.mkdir(parents=True, exist_ok=True)
    names = ['TH130 ARR Keys', 'TH130 Signature Call', 'TH130 ARR Vocal', 'TH130 V2 FX']
    before = {t: client.call('get_track', dict(track=t, clips=True)) for t in names}
    (OUT / 'before.json').write_text(json.dumps(dict(song=song, tracks=before), indent=2))
    assert not before[names[0]]['mute'] and not before[names[1]]['mute']
    n = sample(512)
    keys = assemble(before[names[0]], n)
    call = assemble(before[names[1]], n)
    stabs = np.zeros_like(keys)

    # Reproduce the exact approved Bm9 key colour, with only phrase-end ornaments.
    source = hf.filt(hf.source('wasc_key_housey_Bmin9.wav', '/resampled & effected/'), 200, 'highpass')
    upper = signal.resample_poly(source, 1, 2, axis=0).astype(np.float32)
    bright = hf.filt(.55 * source[:len(upper)] + .60 * upper, 6800)
    bright /= np.max(abs(bright))
    mid = bright.mean(axis=1)
    side = (bright[:, 0] - bright[:, 1]) * .5
    side -= hf.filt(side[:, None], 300)[:, 0]
    bright = np.column_stack([mid + side * 1.08, mid - side * 1.08]).astype(np.float32)
    bright /= np.max(abs(bright))

    # Two coherent options: constant denser syncopation, or the existing answer
    # with a short turn at chosen phrase ends. Use the latter to retain vocal space.
    for bar, offset, dur, gain in [
        (27, 1.5, .20, .13), (27, 2.275, .11, .075),
        (35, 1.5, .23, .14), (47, 1.5, .28, .12),
        (63, 1.5, .19, .15), (63, 2.275, .11, .085),
        (75, 1.5, .23, .14), (87, 1.5, .26, .11),
        (99, 1.5, .20, .16), (99, 2.275, .11, .09),
        (108, 1.5, .17, .105), (115, 1.5, .23, .16),
    ]:
        at = (bar - 1) * 4 + offset
        shot = hf.edge(bright[:round(dur * SR)], .010, .045 if dur > .15 else .035)
        # Same kick clearance as the approved keys; no random humanisation.
        phase = (np.arange(len(shot)) / SR + offset * BEAT) % BEAT
        recover = np.clip(phase / .09, 0, 1)
        shot *= (.85 + .15 * (.5 - .5 * np.cos(np.pi * recover)))[:, None]
        put(keys, shot, at, gain)
        EVENTS.append(dict(role='Keys', bar=bar, beat=offset, duration_s=dur, gain=gain, midi=71))

    # The existing sample-pack Chicago minor chord has measured G root -15 cents.
    # Keep it on tonic B, filtering below the upper keys to give it a separate role.
    stab = hf.filt(ss.read('PL_DTP2_Reveal_Sample_ChicagoKey_G3.wav'), 210, 'highpass')
    stab = ss.pitch(stab, 67 - .15, 71, .60, .007, .060)
    stab = hf.filt(stab, 5700)
    stab /= np.max(abs(stab))
    mid = stab.mean(axis=1)
    stab = np.column_stack([mid, mid]) * .70 + stab * .30

    def stab_hit(bar, beat, duration, gain, echo=False):
        at = (bar - 1) * 4 + beat
        shot = hf.edge(stab[:round(duration * SR)], .007, .055)
        # Hand the foreground to the stab, rather than summing two chord attacks.
        silence(keys, max(0, at - .03), at + duration / BEAT + .10, .012)
        put(stabs, shot, at, gain)
        if echo:
            put(stabs, hf.filt(shot, 2300), at + .75, gain * .12)
        EVENTS.append(dict(role='Stabs', bar=bar, beat=beat, duration_s=duration,
                           gain=gain, midi=71, echo=echo))

    for bar, gain in [(26, .135), (34, .14), (62, .165), (74, .16),
                      (98, .18), (106, .17), (114, .18)]:
        stab_hit(bar, 2.5, .19, gain)
        stab_hit(bar, 3.275, .12, gain * .61, echo=True)
    # A dry tonic arrival, then room for the sung phrase. A tiny off-beat answer
    # before the final return supplies a playful interruption without a new riff.
    stab_hit(41, 0, .42, .15)
    stab_hit(45, 2.5, .22, .13, echo=True)
    stab_hit(81, 0, .38, .12)
    stab_hit(112, .5, .15, .13)
    stab_hit(112, 1.275, .10, .07)

    # Sung sections are reservations, not generated vocals or guessed lyrics.
    for first, last in [(41, 45), (81, 85)]:
        for y in (keys, call):
            silence(y, (first - 1) * 4, (last - 1) * 4, .035)
    # Short vocal calls will lead the drop; keys/stabs answer in bars 3-4.
    # Leave the already-established melody for the later signature chapter.
    for first, last in [(25, 27), (33, 35), (57, 61), (97, 99), (113, 115)]:
        silence(call, (first - 1) * 4, (last - 1) * 4)
    # Preserve the deliberate empty groove phrases and gaps before both drops.
    for first, last in [(69, 73), (109, 111)]:
        for y in (keys, stabs, call):
            silence(y, (first - 1) * 4, (last - 1) * 4)
    for bar in (56, 96):
        for y in (keys, stabs, call):
            silence(y, (bar - 1) * 4 + 3, bar * 4)

    audio = dict(Keys=keys, Stabs=stabs, Call=call)
    for role, y in audio.items():
        assert np.isfinite(y).all() and np.max(abs(y)) < .80
        for bar, label in CHAPTERS.items():
            chunk = edges(y[sample((bar - 1) * 4):sample((bar + 7) * 4)], .001, .002)
            if np.max(abs(chunk)) < 1e-7:
                continue
            path = OUT / f'{bar:03d}_{role}.wav'
            sf.write(path, chunk, SR, subtype='PCM_24')
            ASSETS.append(dict(role=role, path=str(path), bar=bar, beats=32, label=label))
    plan = dict(bpm=BPM, provisional_key='B minor; recheck against supplied vocal',
                vocal_status='Awaiting user-provided original; no outside recording used',
                sources=dict(hf.SOURCES, **ss.SOURCES), events=EVENTS, assets=ASSETS,
                vocal_reservations=[dict(start_bar=41, end_bar=45, role='sung A'),
                                    dict(start_bar=81, end_bar=85, role='sung B')],
                short_call_reservations=[25, 33, 57, 97, 113])
    (OUT / 'arrangement.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    midi.write(str(OUT / 'Keys and tonic stab ornaments.mid'),
               [(role, i, [[e['midi'], (e['bar'] - 1) * 4 + e['beat'],
                            e['duration_s'] / BEAT, round(e['gain'] / .18 * 100)]
                           for e in EVENTS if e['role'] == role])
                for i, role in enumerate(('Keys', 'Stabs'))], BPM)
    print('PREPARED', len(ASSETS), 'clips;', len(EVENTS), 'new attacks', flush=True)
    C('transport', action='stop')
    C('set_loop', on=False)
    for role in audio:
        name = 'TH130 Remix ' + role
        source_track = before['TH130 Signature Call' if role == 'Call' else 'TH130 ARR Keys']
        volume = source_track['vol_db'] if role != 'Stabs' else -1.
        C('create_track', kind='audio', name=name)
        C('set_track', track=name, volume_db=volume, pan=0, monitoring='off', arm=False)
        C('set_send', track=name, send=0, db={'Keys': -27., 'Stabs': -30., 'Call': -23.}[role])
        for asset in ASSETS:
            if asset['role'] == role:
                C('create_audio_clip', track=name, path=asset['path'], bar=asset['bar'],
                  name=role + ' | ' + asset['label'], warp=False, gain_db=0)
        C('set_track', track=name, mute=False)
        print('LIVE', name, flush=True)
    for name in ('TH130 ARR Keys', 'TH130 Signature Call', 'TH130 ARR Vocal'):
        C('set_track', track=name, mute=True)
    # These two pre-existing FX clips contain reversed provisional Grid vocals.
    for bar in (49, 89):
        C('set_clip', track='TH130 V2 FX', clip={'at': (bar - 1) * 4}, muted=True)
    for bar, name in [(25, 'REMIX chamada pendente - keys respondem'),
                      (41, 'REMIX break - reservado para vocal cantado A'),
                      (57, 'REMIX drop I - sub e resposta Chicago'),
                      (81, 'REMIX respiro - reservado para vocal cantado B'),
                      (97, 'REMIX drop II - resposta ampliada')]:
        C('set_cue', bar=bar, name=name)

    for role in audio:
        t = client.call('get_track', dict(track='TH130 Remix ' + role, clips=True))
        expected = [a for a in ASSETS if a['role'] == role]
        assert not t['mute'] and t['n_clips'] == len(expected)
        for c in t['clips']:
            assert abs(c['length'] - 32) < .01 and Path(c['file']).is_file()
    after = client.call('get_song')
    assert not any(t['name'].startswith('VAMPIRO ') for t in after['tracks'])
    (OUT / 'after.json').write_text(json.dumps(after, ensure_ascii=False, indent=2))
    (OUT / 'Production notes.md').write_text(
        '130 BPM. Instrumental development only; supplied vocal still pending.\n\n'
        'Approved Bm9 keys colour retained. Twelve short ornaments extend selected answers; '
        'fixed-tonic Chicago stabs alternate with keys instead of doubling attacks. '
        'Dry/wet contrast, two short off-beat replies and empty groove phrases support a playful delivery.\n\n'
        '41–45 and 81–85 reserved for sung excerpts. The short call must come from a different '
        'phrase selected in the user-provided original, with a second phrase as a reply; '
        'do not assume the previous download is the same recording. Keep semantic context '
        'and natural intonation; do not reduce every sung phrase to chopped syllables. '
        'Satirical effect requires choosing and auditioning actual words with the user.\n\n'
        'Existing kick, sub bounce, tops, strings and master processing retained. '
        'Prior keys/call/provisional vocal tracks retained muted; reversed provisional vocal FX muted. '
        'No downloaded vocal is active. Native .als save requires the user to save Live.\n')
    print('READY', OUT, flush=True)


if __name__ == '__main__':
    main()
