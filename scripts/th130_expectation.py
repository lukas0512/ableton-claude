"""Replace the rejected question lead with repeating tonic stab/key dialogue.

Rebuild breaks and builds around the approved samples, progressing density,
filter opening and pack uplifters. Preserve the sub groove and archive old parts.
"""
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.ear import midi
from ableton_claude.music import groove
import th130_house_fit as hf
import th130_string_signature as ss
from th130_remix_conversation import assemble
from th130_arrangement_motion import CHAPTERS, edges, put, sample, silence

SR, BPM, BEAT = 44100, 130, 60/130
OUT = Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 Expectation 2026-10-17'
LOG, EVENTS, ASSETS = [], [], []


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    (OUT/'live-changes.json').write_text(json.dumps(LOG, ensure_ascii=False, indent=2))
    return r


def main():
    song = client.call('get_song')
    assert song['tempo'] == BPM
    assert not any(t['name'].startswith('TH130 Expect ') for t in song['tracks'])
    names = ['TH130 Remix Keys', 'TH130 Remix Stabs', 'TH130 Remix Call',
             'TH130 ARR Tops', 'TH130 V2 Build', 'TH130 String Tension']
    state = {t:client.call('get_track', dict(track=t, clips=True)) for t in names}
    assert all(not state[t]['mute'] for t in names)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'before.json').write_text(json.dumps(dict(song=song, tracks=state), indent=2))
    n = sample(512)
    keys = assemble(state[names[0]], n)
    stabs = assemble(state[names[1]], n)
    tops = assemble(state['TH130 ARR Tops'], n)
    rhythm, uplift = np.zeros_like(keys), np.zeros_like(keys)

    raw = hf.filt(hf.source('wasc_key_housey_Bmin9.wav', '/resampled & effected/'), 200, 'highpass')
    upper = signal.resample_poly(raw, 1, 2, axis=0).astype(np.float32)
    key = hf.filt(.55*raw[:len(upper)] + .60*upper, 6800)
    key /= np.max(abs(key))
    mid = key.mean(axis=1); side = (key[:, 0]-key[:, 1])*.5
    side -= hf.filt(side[:, None], 300)[:, 0]
    key = np.column_stack([mid+side*1.08, mid-side*1.08]).astype(np.float32)
    key /= np.max(abs(key))
    stab = hf.filt(ss.read('PL_DTP2_Reveal_Sample_ChicagoKey_G3.wav'), 210, 'highpass')
    stab = ss.pitch(stab, 67-.15, 71, .60, .007, .060)
    stab = hf.filt(stab, 5700); stab /= np.max(abs(stab))
    mid = stab.mean(axis=1)
    stab = np.column_stack([mid, mid])*.70 + stab*.30
    tones = {'Keys':key, 'Stabs':stab}
    audio = {'Keys':keys, 'Stabs':stabs, 'Rhythm':rhythm, 'Uplift':uplift}

    def hit(role, bar, beat, seconds, gain, cutoff=5700, echo=False, hp=210):
        shot = hf.edge(tones[role][:round(seconds*SR)], .010 if role == 'Keys' else .007,
                       min(.045, seconds*.42))
        if cutoff < (6800 if role == 'Keys' else 5700): shot = hf.filt(shot, cutoff)
        if hp > 210: shot = hf.filt(shot, hp, 'highpass')
        at = (bar-1)*4+beat
        put(audio[role], shot, at, gain)
        if echo: put(audio[role], hf.filt(shot, 2400), at+.75, gain*.12)
        EVENTS.append(dict(role=role, bar=bar, beat=beat, duration_s=seconds,
                           gain=gain, cutoff=cutoff, hp=hp, echo=echo))

    def clear(first, last):
        for y in (keys, stabs): silence(y, (first-1)*4, (last-1)*4, .015)

    # An identifiable two-bar cell replaces the rejected lead. Its reply has the
    # same placement each time, with one withheld ending in each longer chapter.
    for first, last, gain in [(29, 33, .14), (33, 37, .145), (61, 69, .17),
                              (73, 77, .16), (101, 109, .18), (113, 117, .18)]:
        clear(first, last)
        for bar in range(first, last, 2):
            hit('Stabs', bar, .5, .19, gain)
            hit('Stabs', bar, 1.275, .11, gain*.61)
            hit('Keys', bar+1, 1.5, .25, gain*1.12, cutoff=6800)
            if bar != last-2:
                hit('Keys', bar+1, 2.275, .12, gain*.67, cutoff=6800, echo=True)

    # Breaks retain a rhythmic thread and a tonic anchor rather than four empty
    # bars awaiting the vocal. The first two bars still leave the singer room.
    for first, level in [(41, .135), (81, .145)]:
        clear(first, first+16)
        hit('Stabs', first, 0, .43, level, cutoff=2400)
        for offset in (2, 4, 6):
            bar = first+offset; opening = 2600+offset*350
            hit('Stabs', bar, .5, .24-offset*.016, level, cutoff=opening)
            hit('Stabs', bar, 1.275, .11, level*.60, cutoff=opening)
            hit('Keys', bar+1, 1.5, .28, level*1.18, cutoff=min(6800, opening+900))
            if offset == 4: hit('Keys', bar+1, 2.275, .13, level*.65, cutoff=opening+900)
        a, b = sample((first-1)*4), sample((first+7)*4)
        segment = tops[a:b].copy()
        dark = hf.filt(segment, 3400)
        opening = np.linspace(.80, .10, len(segment), dtype=np.float32)[:, None]
        segment = segment*(1-opening)+dark*opening
        segment *= np.linspace(.88, 1.07, len(segment), dtype=np.float32)[:, None]
        segment = edges(segment, .015, .04)
        rhythm[a:b] = segment

    # The same question/reply tightens from two bars to one bar, then shorter
    # stabs. Filter and gates evolve; the tonic and the cell stay recognisable.
    for first, extra in [(49, 0.), (89, .01)]:
        for offset in range(8):
            bar = first+offset; progress = offset/7
            cutoff = 1050*(5700/1050)**progress
            gain = .095+.06*progress+extra
            hp = 210+450*max(0, (progress-.6)/.4)
            if offset < 4:
                if offset % 2 == 0:
                    hit('Stabs', bar, .5, .19, gain, cutoff=cutoff, hp=hp)
                    hit('Stabs', bar, 1.275, .11, gain*.61, cutoff=cutoff, hp=hp)
                else:
                    hit('Keys', bar, 1.5, .24, gain, cutoff=cutoff+450)
                    hit('Keys', bar, 2.275, .12, gain*.64, cutoff=cutoff+450)
            elif offset < 6:
                hit('Stabs', bar, .5, .16, gain, cutoff=cutoff, hp=hp)
                hit('Stabs', bar, 1.275, .10, gain*.62, cutoff=cutoff, hp=hp)
                hit('Keys', bar, 2.5, .18, gain*.92, cutoff=cutoff+500)
            elif offset == 6:
                for beat, vel in [(.5, 1.), (1.5, .74), (2.5, .98), (3.275, .64)]:
                    hit('Stabs', bar, beat, .12, gain*vel, cutoff=cutoff, hp=hp)
            else:
                beats = [0., .5, 1., 1.5, 2., 2.5]
                if first == 89: beats += [2.75]
                for i, beat in enumerate(beats):
                    hit('Stabs', bar, beat, .055 if beat == 2.75 else .085,
                        gain*(.68 if i%2 else 1.), cutoff=cutoff, hp=hp)
        # Rebuild percussion without the old synth/pitched ticks in V2 Build.
        a, b = sample((first-1)*4), sample((first+7)*4)
        segment = tops[a:b].copy()
        dark = hf.filt(segment, 3000)
        mix = np.linspace(.8, 0, len(segment), dtype=np.float32)[:, None]
        segment = segment*(1-mix)+dark*mix
        rhythm[a:b] = segment

    snare = hf.filt(ss.read('Odd Frequency - Grid Vol 2 - Clap_Snare 20.wav'), 280, 'highpass')
    snare /= max(np.max(abs(snare)), 1e-9)
    for first in (49, 89):
        for _, beat, _, vel in groove.build_roll(bars=8, vel_from=28, vel_to=90, gap_last_beat=True):
            # Thin the early roll; shorter hits later increase tension without
            # masking the recurring tonic stab. Keep the last beat empty.
            if beat < 16 and beat % 4 != 2: continue
            duration = .14 if beat < 24 else .085
            shot = hf.edge(snare[:round(duration*SR)], .003, .025)
            shot = hf.filt(shot, 2200+5200*beat/31)
            put(rhythm, shot, (first-1)*4+beat, (.105 if first == 49 else .115)*vel/127)

    # A real noise riser from the user's Minimal Tech House pack. Modest speed
    # adjustment to eight bars; no vocal or musical motif is sourced externally.
    riser = ss.read('AA_MTH_TECH_RISER_FX.wav')
    riser = signal.resample(riser, sample(32), axis=0).astype(np.float32)
    riser = hf.filt(hf.filt(riser, 650, 'highpass'), 9500)
    riser /= max(np.max(abs(riser)), 1e-9)
    for first, bars, peak in [(39, 2, .032), (49, 8, .065), (79, 2, .030), (89, 8, .075)]:
        count = sample(bars*4)
        y = riser[-count:].copy()
        progress = np.linspace(0, 1, len(y), dtype=np.float32)[:, None]
        dark = hf.filt(y, 1800)
        y = (dark*(1-progress)+y*progress)*(.10+.90*progress**1.5)
        y = edges(y, .20, .04)
        # Both main drops retain a whole beat without new dry material.
        gap = 1 if bars == 8 else .5
        silence(y, bars*4-gap, bars*4, .045)
        put(uplift, y, (first-1)*4, peak)

    for bar in (56, 96):
        for y in audio.values(): silence(y, (bar-1)*4+3, bar*4, .025)
    # Deliberate rhythm-only phrases remain between the hook chapters.
    for first, last in [(69, 73), (109, 111)]:
        for y in (keys, stabs): silence(y, (first-1)*4, (last-1)*4)

    for role, y in audio.items():
        assert np.isfinite(y).all() and np.max(abs(y)) < .8, (role, np.max(abs(y)))
        for bar, label in CHAPTERS.items():
            chunk = edges(y[sample((bar-1)*4):sample((bar+7)*4)], .001, .002)
            if np.max(abs(chunk)) < 1e-7: continue
            p = OUT/f'{bar:03d}_{role}.wav'; sf.write(p, chunk, SR, subtype='PCM_24')
            ASSETS.append(dict(role=role, path=str(p), bar=bar, label=label))
    plan = dict(bpm=BPM, key='B minor', sources=dict(hf.SOURCES, **ss.SOURCES),
                rejected_timbre='GhettoString lead from TH130 Remix Call; archived muted',
                events=EVENTS, assets=ASSETS, dry_gap_beats=1,
                vocal_status='Original from user still pending; no provisional vocal reintroduced',
                shape='2-bar repeated dialogue; 1-bar dialogue; shorter stabs; silence; sub return')
    (OUT/'arrangement.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    midi.write(str(OUT/'Stab and key conversation.mid'),
               [(role, i, [[71, (e['bar']-1)*4+e['beat'], e['duration_s']/BEAT,
                            min(127, round(e['gain']/.18*100))]
                           for e in EVENTS if e['role'] == role])
                for i, role in enumerate(('Stabs', 'Keys'))], BPM)
    print('PREPARED', len(ASSETS), 'clips;', len(EVENTS), 'conversation attacks', flush=True)
    C('transport', action='stop'); C('set_loop', on=False)
    for role in audio:
        name = 'TH130 Expect '+role
        C('create_track', kind='audio', name=name)
        volume = -1. if role == 'Stabs' else 0.
        C('set_track', track=name, volume_db=volume, pan=0, monitoring='off', arm=False)
        if role in ('Keys', 'Stabs'):
            C('set_send', track=name, send=0, db=-27 if role == 'Keys' else -32)
        for asset in ASSETS:
            if asset['role'] == role:
                C('create_audio_clip', track=name, path=asset['path'], bar=asset['bar'],
                  name=role+' | repeat, open, withhold' if role in ('Uplift', 'Rhythm') else role+' | '+asset['label'],
                  warp=False, gain_db=0)
        print('LIVE', name, flush=True)
    for name in ('TH130 Remix Keys', 'TH130 Remix Stabs', 'TH130 Remix Call', 'TH130 V2 Build'):
        C('set_track', track=name, mute=True)
    for bar in (41, 49, 81, 89):
        C('set_clip', track='TH130 ARR Tops', clip={'at': (bar-1)*4}, muted=True)
    for bar, label in [(41, 'EXPECT break I - tonic and conversation'),
                       (49, 'EXPECT build I - repeat and open'),
                       (57, 'EXPECT drop I - sub release'),
                       (81, 'EXPECT break II - answer and breathe'),
                       (89, 'EXPECT build II - shorten then withhold'),
                       (97, 'EXPECT drop II - full groove')]:
        C('set_cue', bar=bar, name=label)
    for role in audio:
        t = client.call('get_track', dict(track='TH130 Expect '+role, clips=True))
        assert not t['mute'] and len(t['clips']) == len([a for a in ASSETS if a['role'] == role])
        assert all(abs(c['length']-32) < .01 and Path(c['file']).exists() for c in t['clips'])
    s = client.call('get_song')
    assert next(t for t in s['tracks'] if t['name'] == 'TH130 Remix Call')['mute']
    assert next(t for t in s['tracks'] if t['name'] == 'TH130 ARR Vocal')['mute']
    (OUT/'after.json').write_text(json.dumps(s, indent=2))
    (OUT/'Production notes.md').write_text(
        '130 BPM, B minor. Stab/key colours retained from the approved user-pack samples.\n\n'
        'Rejected question lead archived muted. Old V2 Build with pitched synth ticks also '
        'archived muted; replaced with a quieter snare roll and the existing tops.\n'
        'Breaks: tonic arrival, two bars open for a sung phrase, recurring stab/key cell, '
        'gradual percussion opening. Builds: two-bar dialogue becomes one bar, gates shorten, '
        'filter opens, low-mid weight is withheld, pack noise riser swells, final beat clears.\n'
        'Drops: established sub/drums first; stable dialogue repeats in chosen chapters. '
        'Pure groove phrases at 69–73 and 109–111 remain. No new bassline or master change.\n'
        'Original vocal still pending. No externally retrieved or provisional vocal active. '
        'Semantic vocal call/response and satire require the supplied recording.\n'
        'All replaced parts retained muted, edits journaled, MIDI and audio assets stored. '
        'The Live .als still requires a native save.\n')
    print('READY', OUT, flush=True)


if __name__ == '__main__': main()
