"""Fit the existing TH130 arrangement around soft, bright tonic house keys.

Replace two drum support tracks with one balanced tops stem and archive prior
parts muted. The established sub, melody, strings and complete form remain.
"""
import json
import os
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client, loops, server, analysis
from ableton_claude.ear import midi
from develop_th130_track import SECTIONS

SR, BPM, BEAT = 44100, 130, 60/130
OUT = Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 House Fit 2026-10-16'
INDEX = json.loads((Path(__file__).resolve().parents[1]/'knowledge/samples_index.json').read_text())['items']
LOG, ASSETS, SOURCES, NOTES, FIT = [], [], {}, [], []
# Repeat the recognizable answer; change its ending or leave a phrase empty.
ANSWERS = {
    'A': [(3.5,.28,1.), (4.275,.15,.61), (6.5,.31,.94)],
    'B': [(3.5,.25,.94), (5.,.17,.70), (6.275,.12,.50), (7.,.23,.94)],
    'C': [(3.5,.37,1.)],
    'D': [(3.275,.14,.70), (3.75,.24,1.), (5.5,.28,.91)],
}


def C(cmd, **args):
    r=server._journaled(cmd,args)
    LOG.append(dict(cmd=cmd,args=args,result=r))
    (OUT/'live-changes.json').write_text(json.dumps(LOG,ensure_ascii=False,indent=2))
    return r


def source(name, parent=None):
    p=next(r['path'] for r in INDEX if os.path.basename(r['path'])==name and
           (parent is None or parent in r['path']) and os.path.isfile(r['path']))
    SOURCES[name]=p
    return loops.read(p).astype(np.float32)


def filt(x,hz,kind='lowpass'):
    return signal.sosfilt(signal.butter(2,hz,kind,fs=SR,output='sos'),x,axis=0).astype(np.float32)


def edge(x,attack=.010,release=.055):
    x=x.copy();a=min(len(x),round(attack*SR));b=min(len(x),round(release*SR))
    if a:x[:a]*=(.5-.5*np.cos(np.linspace(0,np.pi,a)))[:,None]
    if b:x[-b:] *= (.5+.5*np.cos(np.linspace(0,np.pi,b)))[:,None]
    return x


def put(y,x,beat,gain=1.):
    i=round(beat*BEAT*SR);n=min(len(x),len(y)-i)
    if n>0:y[i:i+n]+=x[:n]*gain


def emit(role,x,bar,kind):
    assert np.isfinite(x).all() and abs(x).max()<.85
    if abs(x).max()<1e-8:return
    p=OUT/f'{bar:03d}_{role.replace(" ","_")}_{kind}.wav'
    sf.write(p,edge(x,.001,.008),SR,subtype='PCM_24')
    ASSETS.append(dict(role=role,path=str(p),bar=bar,kind=kind,beats=len(x)/SR/BEAT,
        peak_db=float(20*np.log10(abs(x).max())),rms_db=float(20*np.log10(np.sqrt(np.mean(x*x))))))


def main():
    song=client.call('get_song')
    assert song['tempo']==BPM and any(t['name']=='TH130 Signature Stabs' for t in song['tracks'])
    assert not any(t['name'].startswith('TH130 House Fit ') for t in song['tracks'])
    OUT.mkdir(parents=True,exist_ok=True)
    roles=['TH130 V2 Hats','TH130 V2 Perc','TH130 V2 Vocal','TH130 Signature Stabs',
           'TH130 Signature Call','TH130 String Tension','TH130 V2 Atmos']
    tracks={t:client.call('get_track',dict(track=t,clips=True)) for t in roles}
    (OUT/'before.json').write_text(json.dumps(dict(song=song,tracks=tracks),ensure_ascii=False,indent=2))

    keys=filt(source('wasc_key_housey_Bmin9.wav','/resampled & effected/'),200,'highpass')
    upper=signal.resample_poly(keys,1,2,axis=0).astype(np.float32)
    bright=.55*keys[:len(upper)]+.60*upper
    bright=filt(bright,6800)
    bright/=abs(bright).max()
    # Keep low-mid weight centred; only the chord's upper partials carry width.
    mid=bright.mean(axis=1);side=(bright[:,0]-bright[:,1])*.5
    side-=filt(side[:,None],300)[:,0]
    bright=np.column_stack([mid+side*1.08,mid-side*1.08]).astype(np.float32)
    bright/=max(float(abs(bright).max()),1e-9)
    # No pitched content is retuned here: this unpitched percussion loop gets the
    # small +3.17% DJ speed change to land precisely on four bars at 130 BPM.
    top=source('SOBV2_TOP_chicago_126bpm.wav')
    top=signal.resample(top,round(16*BEAT*SR),axis=0).astype(np.float32)
    top=filt(filt(top,420,'highpass'),13500)
    top=edge(top,.002,.008)
    sf.write(OUT/'Source Chicago tops - 130 BPM.wav',top,SR,subtype='FLOAT')

    def stem(name,start,n):
        y=np.zeros((n,2),np.float32)
        t=tracks[name]
        if t['mute']:return y
        for c in t['clips']:
            if c['muted'] or abs(c['start']-start*4)>.02:continue
            x=loops.read(c['file']).astype(np.float32)
            y[:min(n,len(x))]+=x[:n]*10**((c['gain_db']+t['vol_db'])/20)
        return y

    for start,end,label,kind in SECTIONS:
        bars=end-start;n=round(bars*4*BEAT*SR)
        keys_bus=np.zeros((n,2),np.float32)
        voice=stem('TH130 V2 Vocal',start,n)
        # Gentle word-aware clearance on the chord, with no full-mix pumping.
        env=ndimage.uniform_filter1d(abs(voice).mean(axis=1),size=round(.035*SR))
        activity=filt(np.clip((env-.008)/.025,0,1)[:,None],8)[:,0]
        activity=np.clip(activity,0,1)

        def hit(at,dur,gain,vel=1.,throw=False):
            count=min(round(dur*SR),len(bright))
            shot=edge(bright[:count],.010,.055 if dur>.2 else .035)
            put(keys_bus,shot,at,gain*vel)
            NOTES.append([71,start*4+at,dur/BEAT,round(vel*110)])
            if throw:
                put(keys_bus,filt(shot,2700),at+.75,gain*vel*.13)

        for phrase in range(bars//4):
            base=phrase*16;at=base+8
            variant=['A','A','B','C'][phrase%4]
            gain=.24 if kind in ('drop','final') else .19
            if kind=='intro':
                if phrase==1:hit(base+14.5,.22,.085)
                continue
            if kind=='groove':
                if phrase%2==0:continue
                gain=.15;variant='C' if phrase==1 else 'A'
            if kind=='hook':variant=['A','B','C','A'][phrase]
            if kind in ('break','air'):
                gain=.22 if kind=='break' else .17
                variant='A' if phrase==0 else 'B'
                if kind=='air':at=base
                if kind=='break' and phrase==0:hit(0,.43,.22,throw=True)
            if kind in ('drop','final'):
                if phrase==3:continue # whole phrase of vocal + sub, for contrast
                variant=['A','B','A','C','D','A'][phrase]
                if phrase==0:hit(0,.25,.15) # short tonic accent, leaving room for the vocal
                if kind=='final':gain=.255
            if kind in ('build','build2'):
                if phrase==1:
                    hit(base+.5,.21,.105);continue
                gain=.13;variant='A'
            if kind=='outro':continue
            for i,(beat,dur,vel) in enumerate(ANSWERS[variant]):
                hit(at+beat,dur,gain,vel,throw=i==len(ANSWERS[variant])-1)
        keys_bus*= (1-.23*activity)[:,None]
        if kind in ('groove','hook','drop','final','outro'):
            # Let the kick's initial transient pass; a six-millisecond preview
            # keeps the small clearance envelope continuous at each beat.
            phase=(np.arange(n)/SR)%BEAT
            recover=np.clip(phase/.09,0,1)
            duck=.85+.15*(.5-.5*np.cos(np.pi*recover))
            pre=np.clip((phase-(BEAT-.006))/.006,0,1)
            duck*=1-.15*(.5-.5*np.cos(np.pi*pre))
            keys_bus*=duck[:,None]

        hats=stem('TH130 V2 Hats',start,n)
        perc=stem('TH130 V2 Perc',start,n)
        tops=hats*.88+perc*.82
        for b in range(bars):
            if kind in ('intro','break','air','outro'):level=0.
            elif kind=='groove':level=.055 if b>=8 else 0.
            elif kind=='hook':level=.085 if b%8>=4 else .045
            elif kind in ('drop','final'):
                level=(.135 if kind=='drop' else .155) if b>=4 else .055
                if b%8==7:level*=.7
                if b//4==3:level*=.5 # a lighter chapter before the hook returns
            else:level=.045 if b>=6 else 0.
            if level:
                count=round(4*BEAT*SR);i=round((b%4)*4*BEAT*SR)
                shot=top[i:i+count]
                put(tops,edge(shot,.002,.008),b*4,level)
            if kind in ('hook','drop','final') and b%8==7:
                # A short coordinated disappearance supplies anticipation instead
                # of another layer or another fill.
                a=round((b*4+3.5)*BEAT*SR);z=min(n,round((b*4+4)*BEAT*SR))
                f=min(round(.025*SR),a)
                tops[a-f:a]*=np.linspace(1,0,f)[:,None];tops[a:z]=0
        tops*=(1-.08*activity)[:,None]
        if kind in ('build','build2'):
            stop=round((bars*4-1)*BEAT*SR)
            for x in (keys_bus,tops):
                x[:stop]=edge(x[:stop],.002,.04);x[stop:]=0
        emit('Keys',keys_bus,start+1,kind);emit('Groove Tops',tops,start+1,kind)
        FIT.append(dict(bar=start+1,kind=kind,word_clearance_max_db=-2.27,
                        keys_rms_db=round(float(20*np.log10(np.sqrt(np.mean(keys_bus**2))+1e-12)),2),
                        tops_rms_db=round(float(20*np.log10(np.sqrt(np.mean(tops**2))+1e-12)),2)))
    midi.write(str(OUT/'House tonic - response variations.mid'),[('Bm9 keys triggers',0,NOTES)],BPM)
    bands,_,_=analysis.band_levels(bright.mean(axis=1),SR)
    bands={name:{k:float(v) for k,v in row.items()} for name,row in bands.items()}
    (OUT/'arrangement.json').write_text(json.dumps(dict(bpm=BPM,key='B minor',sources=SOURCES,
        response_variants=ANSWERS,assets=ASSETS,section_fit=FIT,keys_bands=bands),ensure_ascii=False,indent=2))
    print('PREPARED',len(ASSETS),'clips',FIT,flush=True)
    C('transport',action='stop');C('set_loop',on=False)
    for role in ('Keys','Groove Tops'):
        name='TH130 House Fit '+role
        C('create_track',kind='audio',name=name)
        C('set_track',track=name,volume_db=0,pan=0,monitoring='off',arm=False)
        if role=='Keys':C('set_send',track=name,send=0,db=-27)
        for a in ASSETS:
            if a['role']==role:C('create_audio_clip',track=name,path=a['path'],bar=a['bar'],warp=False,
                                  gain_db=0,name=role+' | '+a['kind'])
        print('LIVE',name,flush=True)
    for t in ('TH130 Signature Stabs','TH130 V2 Hats','TH130 V2 Perc'):C('set_track',track=t,mute=True)
    C('set_track',track='TH130 Signature Call',volume_db=tracks['TH130 Signature Call']['vol_db']-1.)
    C('set_track',track='TH130 String Tension',volume_db=tracks['TH130 String Tension']['vol_db']-1.5)
    C('set_send',track='TH130 V2 Vocal',send=0,db=-24)
    for bar in (41,81):C('set_clip',track='TH130 V2 Atmos',clip={'at':(bar-1)*4},gain_db=-6)
    (OUT/'after.json').write_text(json.dumps(client.call('get_song'),ensure_ascii=False,indent=2))
    (OUT/'Production notes.md').write_text('130 BPM, B minor, full 128-bar form retained.\n\n'
        'House keys: user Wave Alchemy housey Bm9, measured B/D/F#/A/C# chord tones. '
        'Same harmony on every trigger; 55% base + 60% octave blend, 10 ms cosine attack, '
        '35–55 ms releases and 120–430 ms gates. Width restricted above 300 Hz.\n'
        'Responses keep A as the anchor, with different endings B/D and a single-hit C. '
        'One drop phrase is left for the vocal/sub. Gentle word-aware chord clearance (max 2.3 dB).\n'
        'Groove tops: existing hats and percussion rebalance plus user Blanc Chicago percussion, '
        '126->130 BPM DJ speed change. Revealed in chapters, half-beat holes every eight bars, '
        'no extra loop in the breaks, one-beat gap before each drop.\n'
        'Call down 1 dB, tension strings down 1.5 dB, shorter perceived vocal room via send -24 dB. '
        'Earlier stabs/hats/percussion retained muted. Sub pattern and master unchanged.\n')
    print('READY',OUT,flush=True)


if __name__=='__main__':main()
