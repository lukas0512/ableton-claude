"""Reggae/breakbeat development of the saved hard-bounce sketch.

Reference: user's GADDAM file, measured at 163 BPM. New media and original
scores stay separate; every Live mutation goes through the bridge journal.
"""
import json
import os
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.ear import midi

OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB155_ReggaeBreak_20261020'
OLD=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB155_Tutty_20261020'
PROJECT=Path.home()/'Music/Ableton Claude/Projects/Hard Bounce 155 - Tutty Sketch Project'
BPM,SR=163,44100
BEAT=60/BPM
LOG=[]


def dump(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))


def C(cmd,**args):
    r=server._journaled(cmd,args)
    LOG.append(dict(cmd=cmd,args=args,result=r));dump('changes.json',LOG)
    print(cmd,str(r)[:110],flush=True)
    return r


def batch(commands):
    r=server.ableton_batch(commands)
    LOG.extend(dict(command=c,result=v) for c,v in zip(commands,r));dump('changes.json',LOG)
    assert all(x.get('ok') for x in r),r
    print('batch',len(r),'OK',flush=True)


def edge(x,attack=.003,release=.025):
    x=x.copy();a=min(len(x),round(attack*SR));b=min(len(x),round(release*SR))
    if a:x[:a]*=np.linspace(0,1,a)[:,None]
    if b:x[-b:]*=np.linspace(1,0,b)[:,None]
    return x


def filt(x,f,kind):
    return signal.sosfilt(signal.butter(2,f,kind,fs=SR,output='sos'),x,axis=0)


def prepare():
    assert not (OUT/'plan.json').exists(),'Already prepared; inspect the existing plan.'
    score=json.loads((OLD/'final-score.json').read_text())
    state=client.call('get_song');assert not state['is_playing'] and state['tempo']==155
    snap={t['name']:client.call('get_track',dict(track=t['name'])) for t in state['tracks']}
    for name,t in snap.items():
        if name in score:
            actual=[]
            for clip in t['clips']:
                actual.extend([[p,round(at+clip['start'],4),round(dur,4),v]
                   for p,at,dur,v in client.call('get_notes',dict(track=name,clip=clip['i']))])
            assert sorted(actual)==sorted([[p,round(at,4),round(d,4),v]for p,at,d,v in score[name]]),name
    dump('before-tracks.json',snap)
    # Keep the first sixteen drop bars; the bridge is eight bars, return sixteen.
    for name,nn in score.items():
        extension=[[p,t+32,d,v]for p,t,d,v in nn if 160<=t<192]
        score[name]=[x for x in nn if not 128<=x[1]<160]+extension
    bass=score['HB 02 DONK F1']
    bass[:]=[n for n in bass if abs((n[1]%1)-.25)>.01]
    for n in bass:
        if n[0]==67:n[0]=63
    # The voice occupies these phrases; the rave hook answers in the gaps.
    score['HB 06 RAVE hook']=[n for n in score['HB 06 RAVE hook']
                            if not (96<=n[1]<108 or 176<=n[1]<188)]
    def add(name,p,t,d,v):score[name].append([p,t,d,v])
    for bar in range(32,40):
        alternate=(bar-32)%2
        kicks=[0,1.75,2.75] if not alternate else [0,.75,2.5]
        if bar==39:kicks=[0,1.75]
        for at in kicks:add('HB 01 KICK',60,bar*4+at,.30,112 if at==0 else 103)
        basses=[.5,2.25,3.5] if not alternate else [1.5,3.5]
        if bar==39:basses=[.5,2.25]
        for at in basses:
            # End before the syncopated kick, retaining the donk's familiar attack.
            add('HB 02 DONK F1',60 if bar%4!=3 else 63,bar*4+at,.32,99 if at<2 else 94)
        for at in (1,3):
            if bar==39 and at==3:continue
            add('HB 07 SNARE build',60,bar*4+at+.008,.15,108 if at==1 else 113)
        for at,v in [(1.75,65),(2.75,74)]:
            if bar==39:continue
            add('HB 07 SNARE build',60,bar*4+at+.008,.08,v)
        for step in range(16):
            if bar==39 and step>=12:continue
            add('HB 04 HAT tight',60,bar*4+step/4+(.008 if step%2 else 0),.07,
                [78,64,105,70][step%4])
        for at in (1.5,3.5):
            if bar==39 and at>=3:continue
            add('HB 05 HAT offbeat',60,bar*4+at,.17,95)
        for at,v in [(0.75,82),(2.25,91)]:
            add('HB 08 PERC reply',60,bar*4+at+.008,.08,v)
    # Small final acceleration and a beat of breath into the four-on-the-floor return.
    for at,v in [(2,76),(2.25,86),(2.5,96),(2.75,107)]:
        add('HB 07 SNARE build',60,156+at,.08,v)
    for name in score:score[name].sort(key=lambda n:(n[1],n[0]))
    dump('score.json',score)
    midi.write(str(OUT/'Reggae Break 163 - sampler score.mid'),
               [(name,i,nn)for i,(name,nn) in enumerate(score.items())],BPM)
    index=json.loads((Path(__file__).resolve().parents[1]/'knowledge/samples_index.json').read_text())['items']
    sources={}
    def source(name):
        p=next(x['path']for x in index if os.path.basename(x['path'])==name)
        sources[name]=p
        return loops.read(p,SR)
    vocals={}
    for key,file in [('Reggae','RMC2_reggae_music.wav'),('Bring back','RMC2_bring_that_one_back.wav')]:
        x=source(file);x=np.repeat(x.mean(axis=1,keepdims=True),2,axis=1)
        x=filt(filt(x,105,'highpass'),9000,'lowpass')
        hop=441;env=np.sqrt(np.mean(x[:len(x)//hop*hop].reshape(-1,hop,2)**2,axis=(1,2)))
        ix=np.where(env>max(env)*.065)[0]
        a=max(0,(ix[0]-1)*hop);b=min(len(x),(ix[-1]+10)*hop)
        x=edge(x[a:b]);x*=.70/max(abs(x).max(),1e-9)
        sf.write(OUT/(key+'.wav'),x,SR,subtype='PCM_24');vocals[key]=x
        padded=np.pad(x,((0,round(16*BEAT*SR)-len(x)),(0,0)))
        sf.write(OUT/(key+' - native 4 bars.wav'),padded,SR,subtype='PCM_24')
    # Speech stays at its natural speed, onset aligned. No arbitrary vowel warping.
    events=[('Reggae',33,.85),('Bring back',55,.85),('Reggae',97,.78),
            ('Reggae',129,1),('Reggae',141,.90),('Bring back',152,1),
            ('Reggae',177,.80),('Bring back',215,.80)]
    echoes=np.zeros((round(224*BEAT*SR),2),np.float32)
    for key,beat,gain in events:
        x=vocals[key];tail=edge(filt(filt(x[-round(.42*SR):],450,'highpass'),3600,'lowpass'),.015,.045)
        for i,g in enumerate([.16,.09,.05]):
            at=beat+len(x)/SR/BEAT-.42/BEAT+.75*(i+1)
            a=round(at*BEAT*SR);n=min(len(tail),len(echoes)-a)
            if n<=0:continue
            lr=np.array([1,.35] if i%2==0 else [.35,1])
            echoes[a:a+n]+=tail[:n]*g*gain*lr
    # Keep the gap before the returning kick clear; echoes may follow the voice elsewhere.
    a,b=round(159*BEAT*SR),round(160*BEAT*SR)
    echoes[a:b]=0
    sf.write(OUT/'Dub echo 163.wav',edge(echoes),SR,subtype='PCM_24')
    br=source('120_BreakbeatDrums_01_SP.aif')
    br=filt(filt(br,210,'highpass'),10000,'lowpass')
    br=edge(br,.0005,.010);br*=.75/max(abs(br).max(),1e-9)
    sf.write(OUT/'Break texture 120 - 2 bars.wav',br,SR,subtype='PCM_24')
    dump('sources.json',sources)
    dump('plan.json',dict(bpm=BPM,key='F minor',break_bars=[33,41],return_bars=[41,57],
          vocal_events=events,reference_bpm=163,reference_basis='Measured actual user-supplied file; corrected 3:2 tempo ambiguity.',
          reference_lessons=['Near-straight hats, ~51% swing; no house shuffle.',
             '98% bass offbeats; mostly root, with minor-third/fifth turns.',
             'Bass relative to drums is -4.6 dB; previous sketch was -1.2 dB.',
             'Hook and vocal gestures leave space; low end is mono.',
             'Reference loudness is -5.6 LUFS, not used as a blind limiter target.']))
    print('Prepared',OUT,flush=True)


def apply():
    assert not (OUT/'changes.json').exists(),'Inspect partial receipt before resuming.'
    assert (PROJECT/'Hard Bounce 163 - Reggae Break V2.als').is_file(),'Save V2 first.'
    snap=json.loads((OUT/'before-tracks.json').read_text())
    for name,expected in snap.items():assert client.call('get_track',dict(track=name))==expected,name
    score=json.loads((OUT/'score.json').read_text());plan=json.loads((OUT/'plan.json').read_text())
    C('transport',action='stop')
    # Pin the earlier unwarped audio before raising the project tempo.
    for name,beats in [('HB 09 BUILD sweep',64),('HB 10 AIR transitions',192)]:
        C('set_clip',track=name,clip=0,warping=True,warp_mode='complex_pro')
        C('set_warp_markers',track=name,clip=0,beats=beats)
    C('set_tempo',bpm=BPM)
    commands=[]
    levels={'HB 02 DONK F1':-3.4,'HB 03 CLAP':1,'HB 04 HAT tight':-5,
            'HB 05 HAT offbeat':-3,'HB 06 RAVE hook':-4}
    for tr,db in levels.items():commands.append(dict(cmd='set_track',args=dict(track=tr,volume_db=db)))
    for tr,pan in [('HB 04 HAT tight',-.28),('HB 05 HAT offbeat',.28),('HB 08 PERC reply',-.32)]:
        commands.append(dict(cmd='set_track',args=dict(track=tr,pan=pan)))
    batch(commands)
    # Body peak measured 68.6 Hz in the sketch, 61.9 Hz in the reference.
    # Two semitones down puts this kick near 61.1 Hz and still clears the offbeat.
    C('set_param',track='HB 01 KICK',device=0,param='Transpose',value=-2)
    C('set_param',track='master',device=0,param='Input Gain',display='3.0 dB')
    # Reuse native clips and sample instruments; update their notes in bounded batches.
    for name,nn in score.items():
        commands=[]
        for clip in snap[name]['clips']:
            data=[[p,t-clip['start'],d,v]for p,t,d,v in nn if clip['start']<=t<clip['end']]
            commands.append(dict(cmd='add_notes',args=dict(track=name,clip=clip['i'],notes=data,replace=True)))
            if clip['start']==128:
                commands.append(dict(cmd='set_clip',args=dict(track=name,clip=clip['i'],name='BREAK - broken beat + bounce | '+name[6:])))
            elif clip['start']==160:
                commands.append(dict(cmd='set_clip',args=dict(track=name,clip=clip['i'],name='RETURN - full bounce | '+name[6:])))
        batch(commands)
        extension=[[p,t-192,d,v]for p,t,d,v in nn if 192<=t<224]
        if extension:C('create_midi_clip',track=name,bar=49,length=32,loop=False,notes=extension,name='RETURN - second phrase | '+name[6:])
    C('create_track',kind='audio',name='HB 11 REGGAE voice')
    C('set_track',track='HB 11 REGGAE voice',volume_db=-6,pan=0,monitoring='off',arm=False)
    for key,beat,gain in plan['vocal_events']:
        r=C('create_audio_clip',track='HB 11 REGGAE voice',path=str(OUT/(key+' - native 4 bars.wav')),
          beat=beat,warp=False,gain_db=20*np.log10(gain),name='REGGAE | '+key)
        if r['end']>224:
            C('trim_clip',track='HB 11 REGGAE voice',clip={'at':beat},end_beat=224)
    C('create_track',kind='audio',name='HB 12 DUB echo')
    C('set_track',track='HB 12 DUB echo',volume_db=-6,pan=0,monitoring='off',arm=False)
    C('create_audio_clip',track='HB 12 DUB echo',path=str(OUT/'Dub echo 163.wav'),bar=1,warp=False,name='Dub throws - phrase endings')
    C('create_track',kind='audio',name='HB 13 BREAK texture')
    C('set_track',track='HB 13 BREAK texture',volume_db=-15,pan=0,monitoring='off',arm=False)
    for bar in [33,35,37,39]:
        r=C('create_audio_clip',track='HB 13 BREAK texture',path=str(OUT/'Break texture 120 - 2 bars.wav'),
            bar=bar,warp=True,warp_mode='beats',beats=8,length=8,name='Broken drums | organic ghost groove')
        if r['end']>(bar+1)*4+1e-4:
            C('trim_clip',track='HB 13 BREAK texture',clip={'at':(bar-1)*4},end_bar=bar+2)
    # The final break loop leaves a beat of space before the bounce returns.
    C('trim_clip',track='HB 13 BREAK texture',clip=3,end_beat=159)
    for bar,label in [(33,'HB BREAK - reggae + broken beat'),(37,'HB BREAK - bounce stays'),
                      (41,'HB RETURN - full bounce'),(49,'HB RETURN - final phrase')]:
        C('set_cue',bar=bar,name=label)
    C('set_loop',on=False,start_bar=1,end_bar=57)
    C('transport',action='locate',bar=29)
    dump('after-song.json',client.call('get_song'))


if __name__=='__main__':
    {'prepare':prepare,'apply':apply}[sys.argv[1]]()
