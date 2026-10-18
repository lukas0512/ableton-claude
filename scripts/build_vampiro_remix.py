"""Vampiro vocal remix using the current, user-approved TH130 house keys.

The selected recording is published as 'Raul Seixas', not independently credited.
Use isolated, phrase-aligned vocals, pitch +2 in Live Complex Pro; archive the old
voice and competing melodic call muted. Existing house-key audio is unchanged.
"""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client,loops,server

SR,BPM,BEAT=44100,130,60/130
OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/Vampiro Doidao Remix 2026-10-16'
LEAD='VAMPIRO Lead';CHOPS='VAMPIRO Chops'
LOG,ASSETS=[],[]


def C(cmd,**args):
    r=server._journaled(cmd,args);LOG.append(dict(cmd=cmd,args=args,result=r))
    (OUT/'remix-live-changes.json').write_text(json.dumps(LOG,ensure_ascii=False,indent=2))
    return r


def filt(x,hz,kind='lowpass'):
    return signal.sosfilt(signal.butter(2,hz,kind,fs=SR,output='sos'),x,axis=0).astype(np.float32)


def edge(x,attack=.008,release=.040):
    x=x.copy();a=min(len(x),round(attack*SR));b=min(len(x),round(release*SR))
    if a:x[:a]*=np.linspace(0,1,a)[:,None]
    if b:x[-b:]*=np.linspace(1,0,b)[:,None]
    return x


def put(y,x,beat,gain=1.):
    i=round(beat*BEAT*SR);n=min(len(x),len(y)-i)
    if n>0:y[i:i+n]+=x[:n]*gain


def prepare():
    original=loops.read(str(OUT/'Source separated - vocals.wav')).astype(np.float32)
    # Mono centre suppresses stereo instrumental spill while retaining voice body.
    dry=np.repeat(original.mean(axis=1,keepdims=True),2,axis=1)
    dry=filt(filt(dry,105,'highpass'),8500)
    g=json.loads((OUT/'source-analysis.json').read_text())['grid']
    source_beat=g['period']
    definitions={'A':(35.2,8,None),'B':(38.4,8,None),
                 'Tag':(41.8,8,43.88),'Word':(37.10,2,38.00)}
    phrases={}
    for name,(start,beats,stop) in definitions.items():
        # Whole calls retain source beat spacing. Word is intentionally a tighter
        # instrumental fragment; silent padding avoids carrying the next sentence.
        duration=beats*source_beat
        take=dry[round(start*SR):round((start+duration)*SR)].copy()
        if stop is not None:
            end=min(len(take),max(0,round((stop-start)*SR)))
            take[:end]=edge(take[:end],.008,.040);take[end:]=0
        env=ndimage.uniform_filter1d(abs(take).mean(axis=1),size=round(.012*SR))
        expansion=np.clip((env/.018)**.55,.28,1.)
        take*=expansion[:,None]
        take=edge(take)
        source=OUT/f'Phrase {name} - source time.wav';sf.write(source,take,SR,subtype='FLOAT')
        intermediate=OUT/f'Phrase {name} - stretched.wav'
        subprocess.run(['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','error','-y',
            '-i',str(source),'-af',f'atempo={BPM/g["bpm"]:.9f}',str(intermediate)],check=True)
        x=loops.read(str(intermediate)).astype(np.float32)
        n=round(beats*BEAT*SR)
        # ffmpeg's overlap-add can differ by a few milliseconds at the silent tail.
        assert abs(len(x)-n)<SR*.15
        x=np.pad(x,((0,max(0,n-len(x))),(0,0)))[:n]
        x=edge(x,.008,.045)
        x*= (.24 if name=='Word' else .29)/max(float(abs(x).max()),1e-8)
        path=OUT/f'Vampiro {name} - 130 BPM.wav';sf.write(path,x,SR,subtype='PCM_24')
        phrases[name]=dict(path=str(path),beats=beats,source_start_s=start,
                           source_end_s=start+duration,cut_after_s=stop)
    # Complete two-bar calls leave the next two bars for the approved keys.
    calls=[(25,'A'),(29,'B'),(37,'A'),(41,'A'),(43,'B'),(45,'Tag'),
           (49,'A'),(57,'A'),(61,'B'),(73,'A'),(81,'Tag'),
           (89,'A'),(91,'B'),(97,'A'),(101,'B'),(105,'Tag'),(113,'A'),(117,'B')]
    for bar,name in calls:ASSETS.append(dict(track=LEAD,bar=bar,name=name,**phrases[name]))
    word=loops.read(phrases['Word']['path']).astype(np.float32)
    n=round(128*4*BEAT*SR);effects=np.zeros((n,2),np.float32)
    for bar,at,gain in [(7,.5,.34),(15,.5,.44),(23,.5,.52),(53,0,.72),
                        (55,2,.75),(79,1.5,.65),(95,.5,.72),(112,1.5,.70)]:
        beat=(bar-1)*4+at;put(effects,word,beat,gain)
        put(effects,filt(word,2400),beat+2.75,gain*.20)
    short=edge(word[:round(.75*BEAT*SR)],.004,.025)
    for at,gain in [(.5,.6),(1.5,.75),(2.25,.9)]:put(effects,short,(96-1)*4+at,gain)
    for bar,at in [(56,1),(94,2)]:
        reverse=edge(filt(word[::-1],320,'highpass'),.12,.015)
        put(effects,reverse,(bar-1)*4+at,.50)
    for bar in (56,96):
        i,j=round(((bar-1)*4+3)*BEAT*SR),round(bar*4*BEAT*SR)
        f=round(.030*SR);effects[i-f:i]*=np.linspace(1,0,f)[:,None];effects[i:j]=0
    for bar in range(1,129,8):
        a,b=round((bar-1)*4*BEAT*SR),round((bar+7)*4*BEAT*SR)
        x=edge(effects[a:b],.001,.008)
        if abs(x).max()<1e-7:continue
        path=OUT/f'{bar:03d} Vampiro chops - 130 BPM.wav';sf.write(path,x,SR,subtype='PCM_24')
        ASSETS.append(dict(track=CHOPS,bar=bar,name='word rhythm and throws',path=str(path),beats=32))
    (OUT/'remix-arrangement.json').write_text(json.dumps(dict(bpm=BPM,
        vocal_transpose_semitones=2,warp_mode='complex_pro',keys='Existing approved Bm9 audio unchanged',
        phrases=phrases,assets=ASSETS),ensure_ascii=False,indent=2))
    print('PREPARED',len(ASSETS),'vocal clips',flush=True)


def place(asset):
    t=asset['track'];bar=asset['bar'];beats=asset['beats'];at=(bar-1)*4
    # Start at the exact target duration, then pin warp markers explicitly so
    # Live's automatic tempo guess cannot move the phrase ending.
    C('create_audio_clip',track=t,path=asset['path'],bar=bar,warp=False,gain_db=0,
      name='Vampiro | '+asset['name'])
    C('set_warp_markers',track=t,clip={'at':at},beats=beats)
    r=C('set_clip',track=t,clip={'at':at},warping=True,warp_mode='complex_pro',pitch=2,
        looping=False,start_marker=0,end_marker=beats)
    if r['length']>beats+.02:
        r=C('trim_clip',track=t,clip={'at':at},end_beat=at+beats)
    assert abs(r['length']-beats)<.025,(t,bar,r)


def main():
    s=client.call('get_song')
    assert s['tempo']==BPM and any(t['name']=='TH130 ARR Keys' and not t['mute'] for t in s['tracks'])
    assert not any(t['name'] in (LEAD,CHOPS) for t in s['tracks']),'Inspect the staged remix before duplicating.'
    (OUT/'before-vocal-placement.json').write_text(json.dumps(s,ensure_ascii=False,indent=2))
    prepare()
    C('transport',action='stop');C('set_loop',on=False)
    for t in (LEAD,CHOPS):
        C('create_track',kind='audio',name=t)
        C('set_track',track=t,volume_db=0,pan=0,monitoring='off',arm=False)
        C('set_send',track=t,send=0,db=-25 if t==LEAD else -22)
        for asset in ASSETS:
            if asset['track']==t:place(asset)
        print('LIVE',t,flush=True)
    for t in ('TH130 ARR Vocal','TH130 Signature Call'):C('set_track',track=t,mute=True)
    # Earlier reverse-voice effects are replaced by the new song's own material.
    for bar in (49,89):C('set_clip',track='TH130 V2 FX',clip={'at':(bar-1)*4},muted=True)
    for bar,name in [(1,'VAMPIRO - tech house 130'),(25,'VAMPIRO - vocal and house keys'),
                     (41,'VAMPIRO - vocal break'),(57,'VAMPIRO - DROP I'),
                     (89,'VAMPIRO - vocal anticipation'),(97,'VAMPIRO - DROP II')]:
        C('set_cue',bar=bar,name=name)
    (OUT/'after-vocal-placement.json').write_text(json.dumps(client.call('get_song'),ensure_ascii=False,indent=2))
    print('REMIX_READY',OUT,flush=True)


if __name__=='__main__':main()
