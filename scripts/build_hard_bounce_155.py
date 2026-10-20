"""Additive hard-bounce workshop: 16-bar build and 32-bar drop, native MIDI.

Run prepare, apply, then inspect. Existing project material is never deleted.
All Live changes use the journaled ClaudeBridge interface.
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
from ableton_claude.ear import midi

BPM, SR = 155, 44100
BEAT = 60 / BPM
OUT = Path.home() / 'Music/Ableton/User Library/Samples/Codex/HB155_Tutty_20261020'
BROWSER = 'user_library/Samples/Codex/HB155_Tutty_20261020/'
LOG = []
PARTS = {
    'HB 01 KICK': ('Kick 909 short.wav', 0, 0),
    'HB 02 DONK F1': ('Donk F1 short.wav', 0, 0),
    'HB 03 CLAP': ('Clap 909.wav', -1, 0),
    'HB 04 HAT tight': ('Hat tight.wav', -6, -.12),
    'HB 05 HAT offbeat': ('Hat open.wav', -4, .12),
    'HB 06 RAVE hook': ('Rave F4.wav', 0, 0),
    'HB 07 SNARE build': ('Snare 909.wav', -1, 0),
    'HB 08 PERC reply': ('Rim.wav', -9, -.20),
}


def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def C(cmd, **args):
    result = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=result))
    dump('live-changes.json', LOG)
    print(cmd, str(result)[:160], flush=True)
    return result


def edge(x, attack=.001, release=.012):
    y = x.copy()
    for n, reverse in [(min(len(y), round(attack*SR)), False),
                       (min(len(y), round(release*SR)), True)]:
        if n:
            if reverse: y[-n:] *= np.linspace(1, 0, n)[:, None]
            else: y[:n] *= np.linspace(0, 1, n)[:, None]
    return y


def filt(x, hz, kind='lowpass'):
    return signal.sosfilt(signal.butter(2, hz, kind, fs=SR, output='sos'), x, axis=0)


def norm(x, peak=.88):
    return x * peak / max(float(np.max(abs(x))), 1e-10)


def put(y, x, beat, gain=1):
    a = round(beat*BEAT*SR)
    n = min(len(x), len(y)-a)
    if a >= 0 and n > 0: y[a:a+n] += x[:n]*gain


def prepare():
    assert not OUT.exists(), 'Existing workshop assets: inspect before retrying.'
    song = client.call('get_song')
    assert not song['is_playing']
    assert all(not t['clips'] and not t['devices'] for t in song['tracks'])
    # Check Session as well as Arrangement before touching the new set.
    session = client.call('api_probe', {'expr':
        'any(sl.has_clip for t in song.tracks for sl in t.clip_slots)'})
    assert session in (False, 'False'), session
    OUT.mkdir(parents=True)
    dump('before.json', song)
    items = json.loads((Path(__file__).resolve().parents[1]/'knowledge/samples_index.json').read_text())['items']
    sources = {}

    def read(name):
        p = next(x['path'] for x in items if os.path.basename(x['path']) == name)
        sources[name] = p
        return loops.read(p, SR)

    kick = read('SOBV2_KICK_beefy909_hit.wav')
    # A controlled 149 ms body leaves 44 ms before the offbeat bass starts.
    kick = norm(edge(kick[:round(.149*SR)], .0003, .020))
    bass = read('SOBV2_BASS_fmdonk_C.wav')
    # Source is C2 (65.4 Hz); resample down seven semitones to F1 (43.65 Hz).
    bass = signal.resample_poly(bass, 10000, round(10000*2**(-7/12)), axis=0)
    bass = np.repeat(bass.mean(axis=1, keepdims=True), 2, axis=1)
    bass = bass[:round(.167*SR)]
    bass = norm(edge(np.tanh(2.4*bass), .002, .018))
    clap = norm(edge(filt(read('909Clap_01_SP.wav'), 450, 'highpass')[:round(.16*SR)], .0003, .020))
    snare = norm(edge(filt(read('909SnareDrum_01_SP.wav'), 220, 'highpass')[:round(.14*SR)], .0003, .025))
    closed = norm(edge(read('3Q_TT2_Hat_14.wav')[:round(.045*SR)], .0003, .012))
    opened = norm(edge(read('3Q_TT2_Hat_01.wav')[:round(.12*SR)], .0003, .030))
    # Original short supersaw voice: a dry centre with a restrained stereo halo.
    t = np.arange(round(.18*SR))/SR
    f = 349.2282314  # F4, MIDI 65, the prepared sample's root at MIDI 60.
    lead = np.zeros((len(t), 2))
    for cents, pan in [(-12,-.6), (-5,.3), (0,0), (6,-.3), (13,.6)]:
        wave = signal.sawtooth(2*np.pi*f*2**(cents/1200)*t)
        lead[:,0] += wave*math.sqrt((1-pan)/2)/5
        lead[:,1] += wave*math.sqrt((1+pan)/2)/5
    lead = filt(lead, 4600)
    lead *= (np.exp(-t/.075)*(1-np.exp(-t/.0015)))[:,None]
    lead = norm(edge(filt(lead, 250, 'highpass'), .001, .025))
    # A rim made from the snare's first transient avoids a second full backbeat.
    rim = norm(edge(filt(snare[:round(.032*SR)], 1600, 'highpass'), .0003, .015))
    waves = dict(zip([v[0] for v in PARTS.values()],
                     [kick,bass,clap,closed,opened,lead,snare,rim]))
    for name, x in waves.items(): sf.write(OUT/name, x, SR, subtype='PCM_24')

    notes = {name: [] for name in PARTS}
    def n(track, pitch, at, dur, vel): notes[track].append([pitch,at,dur,vel])
    # The four-bar cell remains recognisable; small fills punctuate eight bars.
    for bar in range(16,48):
        rel = bar-16
        for b in range(4):
            if rel in (15,31) and b == 3: continue
            n('HB 01 KICK',60,bar*4+b,.35,118 if b==0 else 114)
        for b in range(4):
            if rel in (15,31) and b == 3: continue
            pitch = 60
            if rel%4 == 3 and b == 3: pitch = 67
            if rel%8 == 7 and b == 2: pitch = 72
            n('HB 02 DONK F1',pitch,bar*4+b+.5,.40,112 if b%2==0 else 104)
        if rel%4 == 2:
            n('HB 02 DONK F1',60,bar*4+3.25,.16,72)
        for b in (1,3):
            if rel in (15,31) and b == 3: continue
            n('HB 03 CLAP',60,bar*4+b+.010,.22,106 if b==1 else 113)
        for step in range(16):
            if rel in (15,31) and step >= 12: continue
            # Fast, mostly straight bounce; all secondary 16ths share a 3 ms delay.
            if step%2==0 or rel>=8:
                n('HB 04 HAT tight',60,bar*4+step/4+(.008 if step%2 else 0),.08,
                  [80,65,108,72][step%4])
        for b in range(4):
            if rel in (15,31) and b == 3: continue
            n('HB 05 HAT offbeat',60,bar*4+b+.5,.22,106 if b%2==0 else 112)
        if rel%4 in (1,3):
            for b,v in [(1.75,71),(2.75,85),(3.5,65)]:
                if rel in (15,31) and b>=3: continue
                n('HB 08 PERC reply',60,bar*4+b+.008,.10,v)
        # Two-bar question and answer. First eight bars keep a spacious response.
        if rel < 8 and rel%4 in (2,3): continue
        if 16 <= rel < 20: continue  # second phrase drops the hook, bass keeps identity
        cell = ([(0.25,60,109),(.75,60,88),(1.5,63,100),(2.75,67,108)]
                if rel%2==0 else
                [(.25,70,103),(.75,67,91),(1.75,63,99),(2.5,60,112)])
        if rel in (15,31): cell=cell[:2]
        for at,p,v in cell: n('HB 06 RAVE hook',p,bar*4+at,.23,v)
        if rel%8==7:
            for at,v in [(3.0,60),(3.25,72),(3.5,88)]:
                if rel in (15,31): continue
                n('HB 07 SNARE build',60,bar*4+at,.10,v)
    # Build: progressive subdivisions, all low end held back for bar 17.
    for bar in range(4,16):
        step = 1 if bar<8 else .5 if bar<12 else .25 if bar<15 else .125
        for at in np.arange(0,4,step):
            beat = bar*4+float(at)
            if beat >= 63: continue
            v = min(114,round(62+(beat-16)/47*65))
            if round(at/step)%2: v-=10
            n('HB 07 SNARE build',60,beat,min(.10,step*.7),v)

    build=np.zeros((round(64*BEAT*SR),2))
    for bar in range(16):
        cell=[(0,60),(1.5,63),(3,67)] if bar<8 else [(0,60),(1,63),(2,67),(3,70)]
        if bar>=12: cell=[(at,67 if bar<15 else 72) for at in np.arange(0,4,.5)]
        cutoff=700*(7000/700)**(bar/15)
        for at,p in cell:
            if bar*4+at>=63:continue
            hit=signal.resample_poly(lead,10000,round(10000*2**((p-60)/12)),axis=0)
            hit=filt(hit,cutoff)
            gain=.065+.065*bar/15
            put(build,hit,bar*4+at,gain)
            put(build,hit,bar*4+at+.75,gain*.27)
    # Rising noise is quiet; no low frequencies under the build or pre-drop gap.
    rng=np.random.default_rng(155)
    fx=np.zeros((round(192*BEAT*SR),2))
    count=round(32*BEAT*SR)
    noise=rng.normal(0,1,(count,2))
    noise=filt(filt(noise,1700,'highpass'),6500)
    ramp=np.linspace(0,1,count)**1.7
    noise=norm(noise,.7)*ramp[:,None]
    put(fx,edge(noise,.05,.10),31,.035)
    # Reverse the clap into the impact; a short, filtered downlifter marks chapters.
    rev=edge(clap[::-1],.025,.003)
    put(fx,rev,64-len(rev)/SR/BEAT-.03,.10)
    for beat in (64,128,160):
        tt=np.arange(round(.7*SR))/SR
        crash=filt(rng.normal(0,1,(len(tt),2)),2200,'highpass')
        crash=norm(crash)*np.exp(-tt/.14)[:,None]
        put(fx,edge(crash,.0005,.03),beat,.035)
    # Exactly one beat of empty anticipation (apart from the reverse pickup).
    build[round(63*BEAT*SR):]=0
    fx[round(63*BEAT*SR):round(63.55*BEAT*SR)]=0
    sf.write(OUT/'Build F minor.wav',edge(build,.003,.008),SR,subtype='PCM_24')
    sf.write(OUT/'Air transitions.wav',edge(fx,.003,.03),SR,subtype='PCM_24')
    for name,nn in notes.items():
        nn.sort(key=lambda x:(x[1],x[0]))
        assert all(0 <= x[1] < 192 for x in nn)
    dump('notes.json',notes)
    midi.write(str(OUT/'Hard Bounce 155 F minor.mid'),[(name,i,nn) for i,(name,nn) in enumerate(notes.items())],BPM)
    dump('sources.json',sources)
    dump('creative.json',dict(bpm=BPM,key='F minor',build_bars=[1,17],drop_bars=[17,49],
         source_tuning=dict(donk='C2 -> F1 (-7 semitones), prepared root MIDI 60',hook='F4 at MIDI 60'),
         web_context=['https://ra.co/events/2383923','https://de.ra.co/events/2472428',
                      'https://ra.co/dj/phyles','https://paisana.moxi.fan/'],
         reference_scope='Scene and lineup research only; no reference audio analysed.',
         intent='Offbeat FM bass, tight 909, short rave motif; low end reserved for the drop.'))
    print('Prepared',OUT, {k:len(v) for k,v in notes.items()},flush=True)


def apply():
    assert not (OUT/'live-changes.json').exists(), 'Already applied or partially applied: inspect receipt.'
    expected=json.loads((OUT/'before.json').read_text())
    assert client.call('get_song') == expected, 'Live changed since preparation.'
    notes=json.loads((OUT/'notes.json').read_text())
    C('set_tempo',bpm=BPM)
    for track,(file,db,pan) in PARTS.items():
        C('create_track',kind='midi',name=track)
        C('load_device',track=track,path=BROWSER+file)
        d=client.call('get_device',dict(track=track,device=0))
        dump(track.replace(' ','_')+'-device.json',d)
        assert d['class']=='OriginalSimpler'
        C('set_device_prop',track=track,device=0,prop='playback_mode',value=1)
        C('set_param',track=track,device=0,param='Volume',value=-24)
        C('set_param',track=track,device=0,param='Vol < Vel',display='100 %')
        C('set_track',track=track,volume_db=db,pan=pan,arm=False,monitoring='off')
        for start,end,label in [(0,8,'BUILD hint'),(8,12,'BUILD accelerate'),(12,16,'BUILD pressure'),
                                (16,24,'DROP A - donk pocket'),(24,32,'DROP B - full hook'),
                                (32,40,'DROP C - space then reply'),(40,48,'DROP D - hook returns')]:
            nn=[[p,t-start*4,du,v] for p,t,du,v in notes[track] if start*4<=t<end*4]
            if nn:
                C('create_midi_clip',track=track,bar=start+1,length=(end-start)*4,
                  name=label+' | '+track[6:],notes=nn,loop=False)
    for track,file in [('HB 09 BUILD sweep','Build F minor.wav'),('HB 10 AIR transitions','Air transitions.wav')]:
        C('create_track',kind='audio',name=track)
        C('set_track',track=track,volume_db=0,pan=0,arm=False,monitoring='off')
        C('create_audio_clip',track=track,path=str(OUT/file),bar=1,warp=False,
          gain_db=15 if 'BUILD' in track else 0,name=track[6:])
    for bar,label in [(1,'HB BUILD - tease F minor'),(9,'HB BUILD - accelerate'),
                      (13,'HB BUILD - pressure'),
                      (17,'HB DROP - donk'),(25,'HB DROP - full riff'),
                      (33,'HB DROP - space and reply'),(41,'HB DROP - lift')]:
        C('set_cue',bar=bar,name=label)
    C('load_device',track='master',path='audio_effects/Limiter')
    C('set_param',track='master',device=0,param='Ceiling',display='-1.0 dB')
    C('set_param',track='master',device=0,param='Mode',item='True Peak')
    dump('limiter.json',client.call('get_device',dict(track='master',device=0)))
    C('set_loop',on=False,start_bar=1,end_bar=49)
    C('transport',action='locate',bar=1)
    dump('after.json',client.call('get_song'))


if __name__=='__main__':
    {'prepare':prepare,'apply':apply}[sys.argv[1]]()
