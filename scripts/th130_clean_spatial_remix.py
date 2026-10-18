"""Clean, separated, phrase-complete remix with native stereo movement.

prepare/stage retain the old tracks muted for verification. clean removes only the
snapshotted old tracks after a successful full master recording and audio checks.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.music import groove
import th130_house_fit as hf
import th130_string_signature as ss
from th130_arrangement_motion import CHAPTERS, edges, put, sample, silence
from th130_remix_conversation import assemble
from develop_th130_track import SECTIONS

SR, BPM, BEAT = 44100, 130, 60/130
ROOT = Path.home()/'Music/Ableton/User Library/Samples/Codex'
OUT = ROOT/'TH130 Clean Spatial Remix 2026-10-17'
SOURCE = ROOT/'Vampiro Doidao Remix 2026-10-16'
NAMES = ['01 Kick', '02 Sub Bass', '03 Clap', '04 Closed Hat', '05 Open Hat',
         '06 Percussion', '07 Chicago Top Loop', '08 Build Snare', '09 Chicago Stab',
         '10 House Keys', '11 Vocal Lead', '12 Vocal FX', '13 Strings',
         '14 Atmosphere', '15 Uplifter', '16 Downlifter', '17 Sweep']
EVENTS = []


def dump(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2))


def C(cmd, **args):
    logpath = OUT/'live-changes.json'
    log = json.loads(logpath.read_text()) if logpath.exists() else []
    r = server._journaled(cmd, args)
    log.append(dict(cmd=cmd, args=args, result=r)); dump('live-changes.json', log)
    return r


def backup():
    assert not (OUT/'backup.json').exists(), 'This pass already has a snapshot; inspect before rerunning.'
    OUT.mkdir(parents=True, exist_ok=True)
    song = client.call('get_song'); assert song['tempo'] == BPM
    assert not any(t['name'] in NAMES for t in song['tracks'])
    state = dict(song=song, tracks={}, devices={})
    for t in song['tracks']:
        name = t['name']; row = client.call('get_track',dict(track=name,clips=True))
        state['tracks'][name] = row
        for d in row['devices']:
            state['devices'][name+':'+str(d['i'])] = client.call('get_device',dict(track=name,device=d['i']))
    for i in range(len(song['returns'])):
        name = 'return:'+str(i); row = client.call('get_track',dict(track=name,clips=False))
        state['tracks'][name] = row
        for d in row['devices']:
            state['devices'][name+':'+str(d['i'])] = client.call('get_device',dict(track=name,device=d['i']))
    dump('backup.json', state)
    print('BACKUP',len(song['tracks']),'tracks; source files retained',flush=True)


def prepare():
    state = json.loads((OUT/'backup.json').read_text())
    n = sample(512)
    y = {name:np.zeros((n,2),np.float32) for name in NAMES}
    assets = []
    # Keep proven foundation clips and string/atmosphere sources intact.
    for name, old in [('01 Kick','TH130 ARR Kick'), ('02 Sub Bass','TH130 Chicago Sub Bounce'),
                      ('03 Clap','TH130 V2 Clap'), ('13 Strings','TH130 String Tension'),
                      ('14 Atmosphere','TH130 V2 Atmos')]:
        t = state['tracks'][old]
        for c in t['clips']:
            if not c['muted']:
                assets.append(dict(track=name,path=c['file'],bar=c['start']/4+1,
                                   beats=c['length'],gain_db=c['gain_db'],name=c['name']))
    # Reconstruct individual percussion layers from their original user samples.
    kit = groove.pattern('tech_house',bars=8,swing=55,seed=17)
    shots = {'closed_hat':ss.read('3Q_TT2_Hat_14.wav'),
             'open_hat':ss.read('3Q_TT2_Hat_01.wav'), 'rim':ss.read('3Q_TT2_Perc_09.wav')}
    roles = {'closed_hat':'04 Closed Hat','open_hat':'05 Open Hat','rim':'06 Percussion'}
    levels = {'closed_hat':.27*.88,'open_hat':.24*.88,'rim':.39*.82}
    top = ss.read('SOBV2_TOP_chicago_126bpm.wav')
    top = signal.resample(top,sample(16),axis=0).astype(np.float32)
    top = hf.edge(hf.filt(hf.filt(top,420,'highpass'),13500),.002,.008)
    for start,end,label,kind in SECTIONS:
        bars=end-start; strong=kind in ('drop','final'); no_low=kind in ('break','air','build','build2')
        for b in range(bars):
            for part,role in roles.items():
                for _,onset,_,vel in kit[part]:
                    if int(onset//4) != b%8: continue
                    if kind=='intro' and part in ('rim','open_hat') and b<4: continue
                    if kind=='outro' and b>=6 and part in ('rim','open_hat'): continue
                    at=b*4+onset%4
                    if kind in ('build','build2') and at>=bars*4-1: continue
                    gain=(.55 if no_low else .78 if kind=='intro' else 1.)
                    if strong and b>=8 and part=='open_hat': gain*=1.18
                    shot=shots[part]
                    if part=='rim': shot=shot*np.array([.9,1.],np.float32)
                    put(y[role],shot,start*4+at,levels[part]*gain*vel/110)
            if strong and b%8==7:
                for step,level in [(13,.20),(14,.26),(15,.34)]:
                    put(y['06 Percussion'],shots['rim']*np.array([1.,.82],np.float32),
                        start*4+b*4+step/4+groove.swing_offset(step,55),level*.82)
            if kind in ('intro','break','air','outro'): level=0.
            elif kind=='groove': level=.055 if b>=8 else 0.
            elif kind=='hook': level=.085 if b%8>=4 else .045
            elif strong:
                level=(.135 if kind=='drop' else .155) if b>=4 else .055
                if b%8==7: level*=.7
                if b//4==3: level*=.5
            else: level=.045 if b>=6 else 0.
            if level:
                i=sample((b%4)*4)
                put(y['07 Chicago Top Loop'],hf.edge(top[i:i+sample(4)],.002,.008),start*4+b*4,level)
            if kind in ('hook','drop','final') and b%8==7:
                for role in list(roles.values())+['07 Chicago Top Loop']:
                    silence(y[role],start*4+b*4+3.5,start*4+b*4+4,.025)
    drum_roles=list(roles.values())+['07 Chicago Top Loop']
    for role in drum_roles:
        z=y[role]
        count=sample(400)-sample(384)
        z[sample(384):sample(400)]=z[sample(400):sample(400)+count].copy()
        z[sample(336):sample(352)]*=10**(1.2/20)
        for bar in (40,80):
            a,b=sample((bar-2)*4),sample(bar*4); original=z[a:b].copy()
            mix=np.linspace(0,.75,len(original),dtype=np.float32)[:,None]
            z[a:b]=original*(1-mix)+hf.filt(original,2800)*mix
            silence(z,(bar-1)*4+3,bar*4)
        silence(z,(112-1)*4+2,112*4)
        z[sample(496):sample(512)]*=np.linspace(1,10**(-3/20),sample(512)-sample(496))[:,None]
        for first in (41,81):
            a,b=sample((first-1)*4),sample((first+7)*4);seg=z[a:b].copy()
            mix=np.linspace(.80,.10,len(seg),dtype=np.float32)[:,None]
            z[a:b]=(seg*(1-mix)+hf.filt(seg,3400)*mix)*np.linspace(.88,1.07,len(seg))[:,None]
        for first in (49,89):
            a,b=sample((first-1)*4),sample((first+7)*4);seg=z[a:b].copy()
            mix=np.linspace(.8,0,len(seg),dtype=np.float32)[:,None]
            z[a:b]=seg*(1-mix)+hf.filt(seg,3000)*mix
        for bar in (56,96): silence(z,(bar-1)*4+3,bar*4)
        silence(z,510,512,.035)
    snare=hf.filt(ss.read('Odd Frequency - Grid Vol 2 - Clap_Snare 20.wav'),280,'highpass')
    snare/=max(np.max(abs(snare)),1e-9)
    for first in (49,89):
        for _,at,_,vel in groove.build_roll(bars=8,vel_from=28,vel_to=90,gap_last_beat=True):
            if at<16 and at%4!=2: continue
            seconds=.14 if at<24 else .085
            shot=hf.filt(hf.edge(snare[:round(seconds*SR)],.003,.025),2200+5200*at/31)
            put(y['08 Build Snare'],shot,(first-1)*4+at,(.105 if first==49 else .115)*vel/127)

    y['09 Chicago Stab']=assemble(state['tracks']['TH130 Expect Stabs'],n)
    y['10 House Keys']=assemble(state['tracks']['TH130 Expect Keys'],n)
    y['15 Uplifter']=assemble(state['tracks']['TH130 Expect Uplift'],n)
    raw=hf.filt(hf.source('wasc_key_housey_Bmin9.wav','/resampled & effected/'),200,'highpass')
    upper=signal.resample_poly(raw,1,2,axis=0).astype(np.float32)
    key=hf.filt(.55*raw[:len(upper)]+.60*upper,6800);key/=np.max(abs(key))
    mid=key.mean(axis=1);side=(key[:,0]-key[:,1])*.5;side-=hf.filt(side[:,None],300)[:,0]
    key=np.column_stack([mid+side*1.08,mid-side*1.08]).astype(np.float32);key/=np.max(abs(key))
    stab=hf.filt(ss.read('PL_DTP2_Reveal_Sample_ChicagoKey_G3.wav'),210,'highpass')
    stab=hf.filt(ss.pitch(stab,66.85,71,.6,.007,.06),5700);stab/=np.max(abs(stab))
    mid=stab.mean(axis=1);stab=.70*np.column_stack([mid,mid])+.30*stab
    # Extend the approved conversation into the former four-bar voids. Retain
    # one-bar breaths and the final beat before each drop; do not change the bass.
    for bar,level in [(19,.12),(23,.13),(45,.11),(59,.14),(69,.15),(71,.13),
                      (85,.12),(99,.15),(109,.15),(111,.13),(119,.14)]:
        at=(bar-1)*4
        for y0 in (y['09 Chicago Stab'],y['10 House Keys']): silence(y0,at,at+8,.015)
        for offset,gain,seconds in [(.5,level,.19),(1.275,level*.61,.11)]:
            put(y['09 Chicago Stab'],hf.edge(stab[:round(seconds*SR)],.007,.04),at+offset,gain)
        for offset,gain,seconds in [(5.5,level*1.12,.25),(6.275,level*.67,.12)]:
            put(y['10 House Keys'],hf.edge(key[:round(seconds*SR)],.010,.045),at+offset,gain)
        EVENTS.append(dict(bar=bar,role='conversation fill',tonic='Bm9/Bm'))

    phrases=prepare_vocal()
    calls=[(17,'Tag'),(25,'Hook'),(33,'Tag'),(41,'Sung'),(43,'Tag'),(49,'Hook'),
           (57,'Hook'),(65,'Tag'),(73,'Sung'),(81,'Sung'),(83,'Tag'),(89,'Hook'),
           (93,'Tag'),(97,'Hook'),(105,'Tag'),(113,'Sung'),(117,'Tag')]
    activity=np.zeros(n,np.float32)
    for bar,phrase in calls:
        p=phrases[phrase];at=(bar-1)*4
        x=loops.read(p['path']).astype(np.float32)
        envelope=ndimage.uniform_filter1d(abs(x).mean(axis=1),size=round(.035*SR))
        i=sample(at);activity[i:i+len(x)]=np.maximum(activity[i:i+len(x)],np.clip((envelope-.006)/.025,0,1))
        assets.append(dict(track='11 Vocal Lead',bar=bar,beats=8,path=p['path'],gain_db=0,
                           name='Vocal | '+phrase+' - entrada completa',pitch=2))
    # Word-level activity provides gentle space while leaving the chord groove
    # present. The phrase endings now carry a release, rather than a hard cut.
    y['09 Chicago Stab']*=(1-.28*activity)[:,None]
    y['10 House Keys']*=(1-.32*activity)[:,None]
    for bar,beat,gain in [(7,1.5,.48),(23,1.5,.58),(55,.5,.56),(79,1.5,.50),
                          (95,.5,.58),(112,.5,.50)]:
        assets.append(dict(track='12 Vocal FX',bar=bar+beat/4,beats=4,path=phrases['Fragment']['path'],
                           gain_db=20*math.log10(gain),name='Vocal | complete word response',pitch=2))

    down=hf.filt(ss.read('Odd Frequency - Grid Vol 2 - Downlifter 9 - 129BPM.wav'),350,'highpass')
    sweep=hf.filt(ss.read('Odd Frequency - Grid Vol 2 - Short Sweep 3.wav'),400,'highpass')
    for bar in (57,97):
        put(y['16 Downlifter'],hf.edge(down[:sample(8)],.002,.35),(bar-1)*4,.20*10**(-2.99/20))
        put(y['17 Sweep'],sweep,(bar-1)*4,.17*10**(-2.99/20))
    for bar in (41,81):put(y['17 Sweep'],sweep,(bar-1)*4,.14)
    for bar in (8.25,128.25):
        put(y['17 Sweep'],hf.edge(sweep[::-1],.02,.02),(bar-1)*4,.12)
    y['17 Sweep'][-round(.35*SR):]*=np.linspace(1,0,round(.35*SR))[:,None]
    for role,z in y.items():
        if role in ('01 Kick','02 Sub Bass','03 Clap','11 Vocal Lead','12 Vocal FX','13 Strings','14 Atmosphere'):continue
        for bar in (56,96):silence(z,(bar-1)*4+3,bar*4,.025)
        assert np.isfinite(z).all() and np.max(abs(z))<.8,(role,np.max(abs(z)))
        for bar,label in CHAPTERS.items():
            chunk=edges(z[sample((bar-1)*4):sample((bar+7)*4)],.001,.002)
            if np.max(abs(chunk))<1e-7:continue
            path=OUT/f'{bar:03d}_{role}.wav';sf.write(path,chunk,SR,subtype='PCM_24')
            assets.append(dict(track=role,path=str(path),bar=bar,beats=32,gain_db=0,name=role+' | '+label))
    dump('arrangement.json',dict(bpm=BPM,key='B minor',tracks=NAMES,assets=assets,
         phrases=phrases,events=EVENTS,sources=dict(hf.SOURCES,**ss.SOURCES),
         source_confirmation='User confirmed the previously retrieved recording; issue was the vocal cut positions.'))
    print('PREPARED',len(assets),'separated clips',flush=True)


def prepare_vocal():
    g=json.loads((SOURCE/'source-analysis.json').read_text())['grid']
    x=loops.read(str(SOURCE/'Source separated - vocals.wav')).astype(np.float32)
    x=np.repeat(x.mean(axis=1,keepdims=True),2,axis=1)
    x=hf.filt(hf.filt(x,115,'highpass'),7800)
    # Complete hook and short contrasting phrase only; no guessed semantic slices.
    # Cached alignment places hook onset 35.42 and final syllable end 37.95;
    # the old 36.12–37.98 cut removed the pickup and part of its first word.
    definitions={'Hook':(35.18,8,38.25), 'Sung':(18.74,8,21.85),
                 'Tag':(41.78,8,43.95), 'Fragment':(42.42,4,43.95)}
    phrases={}
    for name,(start,beats,stop) in definitions.items():
        take=x[round(start*SR):round((start+beats*g['period'])*SR)].copy()
        end=min(len(take),round((stop-start)*SR))
        take[:end]=hf.edge(take[:end],.006,.065);take[end:]=0
        env=ndimage.uniform_filter1d(abs(take).mean(axis=1),size=round(.012*SR))
        take*=np.clip((env/.014)**.45,.35,1.)[:,None]
        source=OUT/f'Vocal {name} - source time.wav';sf.write(source,take,SR,subtype='FLOAT')
        tmp=OUT/f'Vocal {name} - stretched.wav'
        subprocess.run(['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),
                        '-af',f'atempo={BPM/g["bpm"]:.9f}',str(tmp)],check=True)
        z=loops.read(str(tmp)).astype(np.float32);count=sample(beats)
        assert abs(len(z)-count)<SR*.15
        z=np.pad(z,((0,max(0,count-len(z))),(0,0)))[:count]
        z=hf.edge(z,.006,.060);z*=.29/max(np.max(abs(z)),1e-9)
        path=OUT/f'Vocal {name} - 130 BPM.wav';sf.write(path,z,SR,subtype='PCM_24')
        phrases[name]=dict(path=str(path),source_start=start,source_stop=stop,beats=beats)
    dump('vocal-cuts.json',phrases)
    return phrases


def stage():
    plan=json.loads((OUT/'arrangement.json').read_text())
    old=json.loads((OUT/'backup.json').read_text())
    song=client.call('get_song');assert not any(t['name'] in NAMES for t in song['tracks'])
    C('transport',action='stop');C('set_loop',on=False)
    volumes={'02 Sub Bass':0,'09 Chicago Stab':-1,'11 Vocal Lead':-1,'13 Strings':-1.5}
    pans={'04 Closed Hat':-.10,'05 Open Hat':.12,'06 Percussion':-.12,
          '07 Chicago Top Loop':.10,'09 Chicago Stab':-.14,'10 House Keys':.08,'13 Strings':.12}
    for index,name in enumerate(NAMES):
        C('create_track',kind='audio',name=name,index=index)
        C('set_track',track=name,mute=True,volume_db=volumes.get(name,0),pan=pans.get(name,0),monitoring='off',arm=False)
        for a in plan['assets']:
            if a['track']!=name:continue
            C('create_audio_clip',track=name,path=a['path'],bar=a['bar'],warp=False,gain_db=a['gain_db'],name=a['name'])
            if a.get('pitch'):
                at=(a['bar']-1)*4
                C('set_warp_markers',track=name,clip={'at':at},beats=a['beats'])
                r=C('set_clip',track=name,clip={'at':at},warping=True,warp_mode='complex_pro',pitch=a['pitch'],
                    looping=False,start_marker=0,end_marker=a['beats'])
                if r['length']>a['beats']+.02:C('trim_clip',track=name,clip={'at':at},end_beat=at+a['beats'])
        print('STAGED',name,flush=True)
    configure_space()
    activate()


def activate():
    plan=json.loads((OUT/'arrangement.json').read_text())
    old=json.loads((OUT/'backup.json').read_text())
    current=client.call('get_song')
    assert [t['name'] for t in current['tracks'][:len(NAMES)]]==NAMES
    assert len(current['tracks'])==len(NAMES)+len(old['song']['tracks'])
    # Live renumbers untouched default names when tracks are inserted. Resolve
    # those four empty tracks by their verified position, never by a stale name.
    mapping=[]
    for i,t in enumerate(old['song']['tracks']):
        row=current['tracks'][len(NAMES)+i]
        if i>=4:assert row['name']==t['name'],(row['name'],t['name'])
        else:assert row['clips']==0 and not row['devices']
        mapping.append(dict(old=t['name'],current=row['name'],index=row['i']))
        C('set_track',track=row['i'],mute=True)
    dump('legacy-track-map.json',mapping)
    for name in NAMES:C('set_track',track=name,mute=False)
    for name in NAMES:
        t=client.call('get_track',dict(track=name,clips=True))
        expected=[a for a in plan['assets'] if a['track']==name]
        assert t['n_clips']==len(expected) and not t['mute'],name
        for c,a in zip(t['clips'],sorted(expected,key=lambda a:a['bar'])):
            assert abs(c['length']-a['beats'])<.025,(name,c['length'],a['beats'])
    dump('staged-live-state.json',client.call('get_song'))
    print('READY_FOR_FULL_QC',flush=True)


def configure_space():
    def p(track,device,param,**kw):return C('set_param',track=track,device=device,param=param,**kw)
    p('02 Sub Bass',0,'1 Frequency A',display='20 Hz')
    for name,depth,rate,offset in [('10 House Keys',.34,2,.25),('15 Uplifter',.43,4,.5),
                                  ('14 Atmosphere',.48,0,.5),('12 Vocal FX',.30,6,.25)]:
        C('load_device',track=name,path='audio_effects/Auto Pan-Tremolo')
        for param,item in [('Mode','Panning'),('Waveform','Sine'),('Time Mode','Synced'),('Stereo Mode','Phase')]:
            p(name,1,param,item=item)
        for param,value in [('Amount',depth),('Rate',rate),('Phase',.5),('Offset',offset),('Panning Shape',0.)]:
            p(name,1,param,value=value)
    # B was unused in the active arrangement; make it a filtered dotted-eighth echo.
    for param,item in [('Smoothing','Fade'),('Ping Pong','On'),('L Sync','On'),('R Sync','On'),
                       ('L 16th','3'),('R 16th','3'),('Filter On','On')]:p('return:1',0,param,item=item)
    for param,display in [('Feedback',24),('Filter Freq','1.8 kHz'),('Filter Width',2.6),('Dry/Wet',100)]:
        p('return:1',0,param,display=display)
    for param,item in [('In Lo Cut On','On'),('In Hi Cut On','On'),('Chorus On','Off'),
                       ('Diff. Hi Type','Lowpass'),('Density','High')]:p('return:2',0,param,item=item)
    for param,display in [('Predelay','14 ms'),('Decay Time','650 ms'),('Room Size',35),
                          ('Input Freq','2.2 kHz'),('Input Width',4),('Diff. Hi Freq','4.0 kHz'),
                          ('ER Spin Amount',3),('Stereo Image',85),('Dry/Wet',100)]:p('return:2',0,param,display=display)
    for name,send,db in [('09 Chicago Stab',2,-19),('10 House Keys',2,-25),('10 House Keys',0,-27),
                         ('10 House Keys',1,-23.5),('11 Vocal Lead',2,-25),('11 Vocal Lead',0,-29),
                         ('12 Vocal FX',1,-17),('12 Vocal FX',0,-24),('13 Strings',0,-23),
                         ('14 Atmosphere',0,-13),('04 Closed Hat',2,-32),('06 Percussion',2,-28)]:
        C('set_send',track=name,send=send,db=db)
    # No new dry source enters the last beat of either build. Main vocal stays centred.
    C('set_track',track='11 Vocal Lead',pan=0)


def clean():
    receipt=json.loads((OUT/'full-render-receipt.json').read_text())
    a=json.loads((OUT/'full-master-analysis.json').read_text())
    assert receipt['status']['state']=='done' and abs(a['duration_s']-240)<.1
    assert a['loudness']['true_peak_dbtp']<-.7 and a['stereo']['low_correlation_below_120hz']>.95
    old=json.loads((OUT/'backup.json').read_text())
    s=client.call('get_song');assert all(any(t['name']==name and not t['mute'] for t in s['tracks']) for name in NAMES)
    C('transport',action='stop')
    # User explicitly requested removal of obsolete channels. All old assets and
    # complete track/device/clip snapshots remain on disk, outside the working set.
    for i in reversed(range(len(old['song']['tracks']))):
        index=len(NAMES)+i
        now=client.call('get_track',dict(track=index,clips=True));assert now['mute']
        if i>=4:assert now['name']==old['song']['tracks'][i]['name']
        else:assert not now['devices'] and now['n_clips']==0
        C('delete_track',track=index)
    s=client.call('get_song');assert [t['name'] for t in s['tracks']]==NAMES
    dump('final-live-state.json',s)
    print('CLEAN',len(s['tracks']),'tracks;',len(s['returns']),'returns',flush=True)


if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'prepare'
    if action=='prepare':backup();prepare()
    elif action=='prepare-assets':prepare()
    elif action=='stage':stage()
    elif action=='activate':activate()
    elif action=='clean':clean()
    else:raise SystemExit('Use prepare, stage or clean')
