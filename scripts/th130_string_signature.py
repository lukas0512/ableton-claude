"""String anticipation, tonic Chicago stab, and a four-note signature conversation.

Uses verified user-pack samples and journals Live edits. Previous stab arrangement
is retained muted; the existing sub-bounce and complete form are preserved.
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

SR, BPM, BEAT = 44100, 130, 60/130
OUT = Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 String Signature 2026-10-16'
INDEX = json.loads((Path(__file__).resolve().parents[1]/'knowledge/samples_index.json').read_text())['items']
SOURCES, ASSETS, LOG, MELODY, STAB_MIDI = {}, [], [], [], []
CALL = [(71, .275, .24, 100), (66, .75, .44, 104), (69, 1.5, .22, 90), (73, 2.275, .42, 102)]
REPLY = [(3.5, .90), (4.275, .63), (6.5, 1.)]
CACHE = {}


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    (OUT/'live-changes.json').write_text(json.dumps(LOG, ensure_ascii=False, indent=2))
    return r


def read(name):
    p = next(r['path'] for r in INDEX if os.path.basename(r['path']) == name and os.path.isfile(r['path']))
    SOURCES[name] = p
    return loops.read(p).astype(np.float32)


def filt(x, hz, kind='lowpass'):
    return signal.sosfilt(signal.butter(2, hz, kind, fs=SR, output='sos'), x, axis=0).astype(np.float32)


def edge(x, attack=.004, release=.035):
    x = x.copy()
    a, b = min(len(x), round(attack*SR)), min(len(x), round(release*SR))
    if a:x[:a] *= np.linspace(0, 1, a)[:, None]
    if b:x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def pitch(x, source, target, seconds, attack=.004, release=.035):
    key = (id(x), source, target)
    if key not in CACHE:
        ratio = 2**((target-source)/12)
        CACHE[key] = signal.resample_poly(x, 10000, round(10000*ratio), axis=0).astype(np.float32)
    y = CACHE[key][:round(seconds*SR)]
    assert len(y) >= round(seconds*SR)-1, 'Source too short for requested sustain.'
    return edge(y, attack, release)


def put(y, x, beat, gain=1., pan=0.):
    i = round(beat*BEAT*SR)
    n = min(len(x), len(y)-i)
    if n>0:y[i:i+n] += x[:n]*gain*np.array([min(1, 1-pan), min(1, 1+pan)])


def emit(role, x, bar, label):
    assert np.isfinite(x).all() and abs(x).max()<.85
    if abs(x).max()<1e-7:return
    p = OUT/f'{bar:03d}_{role.replace(" ", "_")}_{label}.wav'
    sf.write(p, edge(x, .001, .008), SR, subtype='PCM_24')
    ASSETS.append(dict(role=role, path=str(p), bar=bar, beats=len(x)/SR/BEAT, label=label))


def main():
    song = client.call('get_song')
    assert song['tempo']==BPM and any(t['name']=='TH130 Chicago Sub Bounce' for t in song['tracks'])
    assert not any(t['name'].startswith('TH130 Signature') or t['name']=='TH130 String Tension' for t in song['tracks'])
    OUT.mkdir(parents=True, exist_ok=True)
    names = ['TH130 Chicago Stabs', 'TH130 V2 Build', 'TH130 V2 Atmos', 'TH130 V2 Vocal']
    before = {n:client.call('get_track', dict(track=n, clips=True)) for n in names}
    (OUT/'before.json').write_text(json.dumps(dict(song=song, tracks=before), ensure_ascii=False, indent=2))
    string = filt(read('TOMM_MIRAGE_LIFESTRINGS_C5.wav'), 230, 'highpass') # measured C6, MIDI 84
    string /= abs(string).max()
    lead = filt(filt(read('C_GhettoStringLeadTone_01_SP.wav'), 220, 'highpass'), 4600)
    lead /= abs(lead).max()  # measured +38 cents above C5 (MIDI 72)
    stab = filt(read('PL_DTP2_Reveal_Sample_ChicagoKey_G3.wav'), 160, 'highpass')
    # G-minor sampled chord -> tonic B-minor. All stab triggers stay at this pitch.
    stab = pitch(stab, 67-.15, 71, .6)
    stab = filt(stab, 5100); stab /= abs(stab).max()

    def answer(y, at, global_start, gain=.18, downbeat=False):
        if downbeat:
            put(y, edge(stab[:round(.36*SR)], .002, .09), at, gain)
            STAB_MIDI.append([71, global_start+at, .6, 108])
        for beat, vel in REPLY:
            shot = edge(stab[:round((.20 if vel>.8 else .12)*SR)], .002, .035)
            put(y, shot, at+beat, gain*vel)
            put(y, filt(shot, 2300), at+beat+.75, gain*vel*.13, -.12)
            STAB_MIDI.append([71, global_start+at+beat, .35, round(vel*110)])

    def call(y, at, global_start, gain=.16, variation=False, hint=False):
        for p, beat, dur, vel in CALL[:2] if hint else CALL:
            if variation and p==73:p=74 # occasional upper neighbour; tonic answer stays fixed
            shot = pitch(lead, 72.38, p, dur*BEAT, .006, .035)
            put(y, shot, at+beat, gain*vel/104, .07)
            # Only the final note throws a quiet dotted-eighth delay into the gap.
            if beat==2.275:
                put(y, filt(shot, 2400), at+beat+.75, gain*.19, -.15)
            MELODY.append([p, global_start+at+beat, dur, vel])

    for start, end, label, kind in SECTIONS:
        bars=end-start
        y={r:np.zeros((round(bars*4*BEAT*SR), 2), np.float32) for r in ('Signature Stabs', 'Signature Call')}
        for phrase in range(bars//4):
            base=phrase*16
            if kind=='intro':
                if phrase==1:answer(y['Signature Stabs'], base+8, start*4, .075)
            elif kind=='groove':
                if phrase%2:answer(y['Signature Stabs'], base+8, start*4, .12)
            elif kind=='hook':
                answer(y['Signature Stabs'], base+8, start*4, .17)
                if phrase==3:call(y['Signature Call'], base+8, start*4, .10, hint=True)
            elif kind in ('break','air'):
                # Voice gets the first two bars of the break, then the melodic
                # question and the three-hit tonic answer occupy separate gaps.
                at=base+(8 if kind=='break' else 0)
                call(y['Signature Call'], at, start*4, .21 if kind=='break' else .17,
                     variation=phrase==1)
                answer(y['Signature Stabs'], at, start*4, .21 if kind=='break' else .16)
                if phrase==0 and kind=='break':
                    put(y['Signature Stabs'], edge(stab[:round(.42*SR)], .002, .12), 0, .22)
                    STAB_MIDI.append([71, start*4, .8, 114])
            elif kind in ('drop','final'):
                # Full signature recurs after eight bars, then a phrase of pure
                # vocal + sub groove gives it somewhere to return from.
                answer(y['Signature Stabs'], base+8, start*4, .19)
                if phrase in (2,4):
                    call(y['Signature Call'], base+8, start*4, .145 if kind=='drop' else .165,
                         variation=kind=='final' and phrase==4)
            elif kind in ('build','build2'):
                if phrase==0:
                    call(y['Signature Call'], base+8, start*4, .14)
                    answer(y['Signature Stabs'], base+8, start*4, .115)
                else:
                    put(y['Signature Stabs'], edge(stab[:round(.17*SR)], .002, .03), base+.5, .11)
                    STAB_MIDI.append([71, start*4+base+.5, .3, 78])
        if kind in ('build','build2'):
            for x in y.values():
                stop=round((bars*4-1)*BEAT*SR)
                x[:stop]=edge(x[:stop], .002, .035); x[stop:]=0
        for role,x in y.items():emit(role,x,start+1,kind)

    # Pre-break anticipation is disclosed four bars before the break; the second
    # transition reuses the same idea. The eight-bar builds expand that gesture.
    for bar,bars,label in [(37,4,'before_break'),(77,4,'before_air'),(49,8,'build_I'),(89,8,'build_II')]:
        n=round(bars*4*BEAT*SR); y=np.zeros((n,2),np.float32)
        dur=(bars*4-1)*BEAT
        held=pitch(string,84,66,dur,.65,.18)
        dark=filt(held,1400); bright=filt(held,5800)
        progress=np.linspace(0,1,len(held),dtype=np.float32)[:,None]
        opening=dark*(1-progress)+bright*progress
        amp=(.035+(.19 if bars==8 else .13)*progress**1.6)
        put(y,opening*amp,0)
        # Quiet G above F# in the last bar supplies a b9 rub; it releases
        # before the tonic chord and never occupies the sub register.
        rub=pitch(string,84,67,2.5*BEAT,.22,.18)
        put(y,rub,bars*4-4,.045 if bars==8 else .032)
        if bars==8:
            upper=pitch(string,84,73,7*BEAT,.6,.3)
            put(y,upper,bars*4-8,.065)
        emit('String Tension',y,bar,label)
    for bar in (41,81):
        y=np.zeros((round(4*BEAT*SR),2),np.float32)
        release=pitch(string,84,71,3.2*BEAT,.025,.85)
        put(y,release,0,.065)
        emit('String Tension',y,bar,'tonic_release')

    midi.write(str(OUT/'Signature - melody and tonic replies.mid'),
               [('Ghetto string call',0,MELODY),('Tonic Chicago stab triggers',1,STAB_MIDI)],BPM)
    (OUT/'arrangement.json').write_text(json.dumps(dict(bpm=BPM,key='B minor',call=CALL,reply=REPLY,
        stab_pitch='B minor chord, fixed tonic',sources=SOURCES,assets=ASSETS),ensure_ascii=False,indent=2))
    print('PREPARED',len(ASSETS),'clips;',len(MELODY),'melody notes',flush=True)
    C('transport',action='stop');C('set_loop',on=False)
    for role in ('Signature Stabs','Signature Call','String Tension'):
        t='TH130 '+role
        C('create_track',kind='audio',name=t)
        C('set_track',track=t,monitoring='off',arm=False,volume_db=0,pan=0)
        C('set_send',track=t,send=0,db={'Signature Stabs':-24,'Signature Call':-23,'String Tension':-25}[role])
        for a in ASSETS:
            if a['role']==role:C('create_audio_clip',track=t,path=a['path'],bar=a['bar'],warp=False,
                                  gain_db=0,name=role+' | '+a['label'])
        print('LIVE',t,flush=True)
    C('set_track',track='TH130 Chicago Stabs',mute=True)
    for bar in (49,89):C('set_clip',track='TH130 V2 Build',clip={'at':(bar-1)*4},gain_db=-6)
    # Reuse the spacious texture quietly; the new string becomes the tension voice.
    for bar in (41,81):C('set_clip',track='TH130 V2 Atmos',clip={'at':(bar-1)*4},gain_db=-4)
    for bar in (49,89):C('set_clip',track='TH130 V2 Atmos',clip={'at':(bar-1)*4},muted=True)
    (OUT/'after.json').write_text(json.dumps(client.call('get_song'),ensure_ascii=False,indent=2))
    (OUT/'Production notes.md').write_text('130 BPM, B minor. Full 128-bar form and sub bounce kept.\n\n'
        'Tonic stab: fixed B-minor Chicago chord throughout. A longer tonic attack marks bar 41.\n'
        'Signature: B4–F#4–A4–C#5, then three separated tonic-chord answers. '
        'The last call occasionally reaches D5; the stab stays on B minor. '
        'Revealed in the break, recalled after eight bars of the drops.\n'
        'Strings: F#4 pedal, rising gain and filter opening, quiet G4 neighbour in the last bar; '
        'one-beat gap then B4 release at the break. Repeated in second build.\n'
        'Measured source pitches: Tom Middleton string C6/MIDI84 despite C5 filename; '
        'Samplephonics Ghetto String approximately C5+38 cents, compensated in rendering.\n'
        'Earlier Chicago stab track archived muted. Existing build reduced 6dB; build atmosphere muted. '
        'No master change. Native MIDI and per-section audio retained.\n')
    print('READY',OUT,flush=True)


if __name__=='__main__':main()
