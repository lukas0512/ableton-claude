"""Build the user's SOLARIA summer tech-house demo in the connected Live set.

Run from mcp_server: uv run python ../scripts/build_solaria.py
Original DT tracks are preserved and muted. Refuses to overwrite an existing SUM version.
Samples remain untouched; generated assets and a command journal live in the User Library.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))
from ableton_claude import client, library, loops

BPM, SR, BARS = 128, 44100, 64
BEAT = 60 / BPM
OUT = Path('/Users/lukasgalhardo/Music/Ableton/User Library/Samples/Codex/SOLARIA')
RNG = np.random.default_rng(283)
EVENTS = []
SOURCES = {}


def C(cmd, **args):
    result = client.call(cmd, args)
    EVENTS.append({'cmd': cmd, 'args': args, 'result': result})
    with (OUT / 'commands.json').open('w') as f:
        json.dump(EVENTS, f, indent=1, ensure_ascii=False)
    return result


def source(filename):
    idx = library.load_index()
    rows = [r for r in idx['items'] if os.path.basename(r['path']) == filename]
    paths = [r['path'] for r in rows if os.path.isfile(r['path'])]
    if not paths:
        raise FileNotFoundError(filename)
    SOURCES[filename] = paths[0]
    return paths[0]


def read(filename, bpm=None, hp=None, lp=None, mono=False):
    path = source(filename)
    if bpm and bpm != BPM:
        path = str(OUT / ('tempo_' + filename))
        subprocess.run(['/opt/homebrew/bin/ffmpeg', '-v', 'error', '-y', '-i',
                        SOURCES[filename], '-af', f'atempo={BPM/bpm}',
                        '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s24le', path], check=True)
    x = loops.read(path, SR).astype(np.float32)
    if mono:
        x[:] = x.mean(axis=1, keepdims=True)
    for cutoff, kind in ((hp, 'highpass'), (lp, 'lowpass')):
        if cutoff:
            sos = signal.butter(2, cutoff, btype=kind, fs=SR, output='sos')
            x = signal.sosfilt(sos, x, axis=0).astype(np.float32)
    return x


def peak(x, db):
    return x * (10 ** (db / 20) / max(1e-8, float(np.abs(x).max())))


def fit(x, beats):
    n = round(beats * BEAT * SR)
    y = np.zeros((n, 2), np.float32)
    y[:min(n, len(x))] = x[:n]
    fade = min(220, len(y)//2)
    y[:fade] *= np.linspace(0, 1, fade)[:, None]
    y[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return y


def put(y, x, beat, gain=1.0, pan=0.0):
    a = round(beat * BEAT * SR)
    n = min(len(x), len(y) - a)
    if a < 0 or n <= 0:
        return
    gains = np.array([min(1, 1-pan), min(1, 1+pan)], np.float32)
    y[a:a+n] += x[:n] * gain * gains


def swing(t):
    return t + (0.04 if round(t * 4) % 2 else 0)


def blank():
    return np.zeros((round(BARS * 4 * BEAT * SR), 2), np.float32)


def save_stem(name, x):
    # Gentle edge fades and explicit headroom; no automatic loudness inflation.
    x[:220] *= np.linspace(0, 1, 220)[:, None]
    x[-4410:] *= np.linspace(1, 0, 4410)[:, None]
    maximum = float(np.abs(x).max())
    if maximum > 0.89:
        x *= 0.89 / maximum
    path = OUT / (name + '.wav')
    sf.write(path, x, SR, subtype='PCM_24')
    return path


def make_audio():
    kick = peak(read('SOBV2_KICK_shortsweet_hit.wav', mono=True, hp=24), -7.5)
    clap = peak(read('SOBV2_CLAP_lazydisco_hit.wav', hp=160), -11)
    hat = peak(read('SOBV2_HAT_likely_hit.wav', hp=1800), -15)
    ghost = peak(read('SOBV2_HAT_kitty_hit_2.wav', hp=2200), -20)
    conga = peak(read('SOBV2_PERCUSSION_umbongo_hit.wav', hp=170), -16)
    stick = peak(read('SOBV2_PERCUSSION_sticks_hit_2.wav', hp=500), -21)
    shake = peak(read('Shaker 4.wav', hp=1200), -22)
    # Pitch-preserving tempo matching for vocal and texture; bass is native 128 BPM.
    bass = fit(read('SOBV2_BASS_mental_Fmin_128bpm.wav', mono=True, hp=23, lp=1800), 16)
    bass = peak(np.tanh(bass * 1.7), -11.5)
    phase = (np.arange(len(bass)) / SR / BEAT) % 1
    duck = 0.45 + 0.55 * np.minimum(1, phase / 0.32)
    bass *= duck[:, None]
    vocal = fit(read('SOBV2_VOCAL_moveyourbody_126bpm.wav', bpm=126, hp=250, lp=10000), 32)
    vocal = peak(vocal, -14)
    air = fit(read('SOBV2_TEXTURE_milkshakes_126bpm.wav', bpm=126, hp=1800, lp=10000), 32)
    air = peak(air, -26)
    riser = read('Riser 15.wav', hp=800, lp=11500)
    riser = signal.resample(riser, round(15.5 * BEAT * SR)).astype(np.float32)
    riser = peak(riser, -13)
    impact = peak(read('SOBV2_FX_impact.wav', hp=200, lp=9500), -15)
    lift = fit(read('DCW_126_Technology_1_Top.wav', bpm=126, hp=1300), 16)
    lift = peak(lift, -15)

    stems = {n: blank() for n in ['KICK', 'CLAP', 'HATS', 'PERC', 'BASS', 'VOCAL', 'AIR', 'FX', 'LIFT']}
    breaks = set(range(16,24)) | set(range(40,48))
    for b in range(BARS):
        pos = b*4
        is_break = b in breaks
        is_last_drop = b >= 48
        if not is_break:
            for beat in range(4):
                if b in (15,39,63) and beat == 3:
                    continue
                put(stems['KICK'], kick, pos+beat, 1 if beat == 0 else .96)
        if not is_break and b>=4:
            for t in (1,3):
                if b in (15,39,63) and t==3:
                    continue
                put(stems['CLAP'], clap, pos+t+.009, .98 if t==3 else .91)
        if not is_break:
            for t in (.5,1.5,2.5,3.5):
                if b in (15,39,63) and t>=3:
                    continue
                put(stems['HATS'], hat, pos+t, .85+RNG.uniform(-.09,.09), -.08)
            for t in (.75,2.25,3.75):
                if b in (15,39,63) and t>=3:
                    continue
                put(stems['HATS'], ghost, pos+swing(t), .7, .14)
        if not is_break or b in (20,21,22,44,45,46):
            for t,vel in [(.75,.7),(1.5,.91),(2.75,.78),(3.25,.55)]:
                put(stems['PERC'], conga, pos+swing(t)+RNG.uniform(-.004,.004),
                    vel*(.48 if is_break else .85), -.18)
            for t in (.25,1.75,3.5):
                put(stems['PERC'], stick, pos+swing(t), .55 if is_break else .8,.22)
        if not is_break and b>=8:
            for step in range(16):
                if b in (15,39,63) and step>=12:
                    continue
                vel=[.30,.48,.62,.40][step%4] * (1 if is_last_drop or b>=32 else .72)
                put(stems['PERC'], shake, pos+swing(step/4)+RNG.uniform(-.003,.003),vel,.3)
    # Bass and drums leave together for the half-beat before each break.
    for b in [4,8,12,24,28,32,36,48,52,56,60]:
        put(stems['BASS'], bass,b*4,.70 if b==4 else 1)
    for b in [15,39,63]:
        a=round((b*4+3)*BEAT*SR); z=round((b*4+4)*BEAT*SR)
        stems['BASS'][a-220:a] *= np.linspace(1,0,220)[:,None]
        stems['BASS'][a:z]=0
    # Short vocal calls leave room for the instrumental response.
    for b in [12,20,32,44,56]:
        seg=vocal[:round(8*BEAT*SR)].copy()
        seg[-220:] *= np.linspace(1,0,220)[:,None]
        put(stems['VOCAL'],seg,b*4,.85 if b in (20,44) else 1)
        delay=round(.75*BEAT*SR)
        put(stems['VOCAL'],seg,b*4+.75,.18,.45)
    for b in range(0,64,8):
        bed=air.copy()
        env=np.linspace(.35,1.4,len(bed)) if b in (16,40) else np.linspace(.7,.4,len(bed))
        bed*=env[:,None]
        if b in (16,40):
            bed[-round(.5*BEAT*SR):]=0
        put(stems['AIR'],bed,b*4)
    for b in [20,44]:
        put(stems['FX'],riser,b*4)
        # Clap roll accelerates across the final two bars; kick stays absent.
        for beat in np.arange(b*4+8,b*4+12,.5):
            put(stems['CLAP'],clap,float(beat),.28+(.025*(beat-b*4-8)))
        for beat in np.arange(b*4+12,b*4+15.5,.25):
            put(stems['CLAP'],clap,float(beat),.4+.055*(beat-b*4-12))
    for b in [24,48]:
        put(stems['FX'],impact,b*4)
    for b in [32,36,56,60]:
        put(stems['LIFT'],lift,b*4, .9 if b>=56 else .7)
    # One shared stop before both drops; reverb tails are handled by Live.
    for name,x in stems.items():
        for boundary in (96,192):
            a=round((boundary-.5)*BEAT*SR); z=round(boundary*BEAT*SR)
            x[a-220:a] *= np.linspace(1,0,220)[:,None]
            x[a:z]=0
    return {name: save_stem(name,x) for name,x in stems.items()}


def settings(track, device, entries):
    for param, mode in entries:
        result=C('set_param',track=track,device=device,param=param,**mode)
        print(track,param,result['display'],flush=True)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    before=client.call('get_song')
    if any(t['name'].startswith('SUM ') for t in before['tracks']):
        raise RuntimeError('SUM version already exists; adjust it instead of overwriting.')
    with (OUT/'before.json').open('w') as f:
        json.dump(before,f,indent=2)
    print('Preparing original patterns with user samples...',flush=True)
    files=make_audio()
    with (OUT/'sources.json').open('w') as f:
        json.dump(SOURCES,f,indent=2,ensure_ascii=False)
    C('transport',action='stop')
    C('set_tempo',bpm=BPM)
    for t in before['tracks']:
        if t['name'].startswith('DT '):
            C('set_track',track=t['name'],mute=True)
    for i,(role,path) in enumerate(files.items()):
        name='SUM '+role
        C('create_track',kind='audio',name=name)
        C('set_track_input',track=name,source='No Input')
        C('set_track',track=name,volume_db=0,monitoring='off',color_index=14 if i<4 else 26)
        C('create_audio_clip',track=name,path=str(path),bar=1,warp=False,name=role+' | SOLARIA 128')
        # User default audio track contains EQ Eight: neutralise on our new stem tracks.
        for d in C('get_track',track=name,clips=False)['devices']:
            if d['name']=='EQ Eight':
                C('set_device_on',track=name,device=d['i'],on=False)
        print('Loaded',name,flush=True)
    for role,preset,level in [('HOOK','sounds/Mallets/Marimba Classic.adv',-10),
                              ('ORGAN','sounds/Piano & Keys/Organ House.adg',-15)]:
        name='SUM '+role
        C('create_track',kind='midi',name=name)
        C('load_device',track=name,path=preset)
        C('set_track',track=name,volume_db=level,color_index=18)
        C('load_device',track=name,path='audio_effects/Echo')
        settings(name,'Echo',[
            ('Dry Wet',{'display':'13 %' if role=='HOOK' else '10 %'}),
            ('Feedback',{'display':'23 %'}),('Channel Mode',{'item':'Ping Pong'}),
            ('HP Freq',{'display':'400 Hz'}),('LP Freq',{'display':'4.5 kHz'})])
    # Memorable four-bar motif, with space between call and response.
    motif=[(72,.75,.27,101),(75,1.5,.24,91),(77,2.75,.32,109),
           (72,4.75,.25,94),(68,5.5,.32,89),(70,7.25,.22,81),
           (72,8.75,.28,99),(75,9.5,.24,89),(77,10.75,.30,105),
           (79,12.5,.24,88),(75,13.25,.3,85),(77,14.5,.65,104)]
    for bar,n,vel,kind in [(9,8,.72,'Tease'),(17,8,.55,'Break'),(25,16,1,'First Drop'),
                           (41,8,.60,'Sunset Break'),(49,16,1.03,'Final Drop')]:
        notes=[]
        for b in range(0,n,4):
            for p,t,d,v in motif:
                if kind=='Tease' and (t>=8 or b==0): continue
                if 'Break' in kind and (b==0 or t>=14): continue
                if bar==49 and b>=8 and t==14.5: p=84
                notes.append([p,round(b*4+swing(t),4),d,min(120,int(v*vel))])
        C('create_midi_clip',track='SUM HOOK',bar=bar,length=n*4,notes=notes,name=kind+' | Summer motif')
    for bar,n,quiet in [(5,4,True),(9,8,False),(17,8,True),(25,16,False),(41,8,True),(49,16,False)]:
        notes=[]
        for b in range(n):
            chord=[56,60,63,67] if b%4<3 else [55,58,63,65]
            hits=[2.75] if quiet else [.75,2.75]
            if quiet and b%2: continue
            for t in hits:
                for p in chord:
                    notes.append([p,round(b*4+swing(t),4),.22 if not quiet else .8,68 if quiet else 88])
        C('create_midi_clip',track='SUM ORGAN',bar=bar,length=n*4,notes=notes,name='Sunlit organ' if not quiet else 'Distant organ')
    # A compact common room glues the clap, percussion and hook.
    for role,send in [('CLAP',-20),('PERC',-19),('HOOK',-17),('ORGAN',-22),('VOCAL',-19),('AIR',-23)]:
        C('set_send',track='SUM '+role,send=0,db=send)
    settings('master','Limiter',[
        ('Mode',{'item':'True Peak'}),('Ceiling',{'db':-1}),
        ('Input Gain',{'db':3}),('Release',{'display':'100 ms'})])
    for cue in before['cues']:
        if cue['name'].startswith('DT '): C('delete_cue',name=cue['name'])
    for name,bar in [('SOLARIA | Intro',1),('Groove',9),('Sunset Break',17),
                     ('DROP 1',25),('Lift',33),('Vocal Break',41),('DROP 2',49),('Final Lift',57),('End',65)]:
        C('set_cue',name=name,bar=bar)
    C('set_loop',on=True,start_bar=17,end_bar=41)
    C('transport',action='locate',bar=17)
    with (OUT/'arrangement.json').open('w') as f:
        json.dump(C('get_song'),f,indent=2)
    print('BUILT SOLARIA: 128 BPM, F minor, 64 bars.',flush=True)


if __name__=='__main__':
    build()
