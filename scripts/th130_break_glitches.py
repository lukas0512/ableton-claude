"""Phrase-end resampling in the two breaks; retain the approved rhythm section.

Only the existing keys, stab, atmosphere and two spoken-word clips change.
All cuts are faded, pitched material retains its tuning, and the deep rhythm
continues. No master recording, downloaded source or new synth is required.
"""
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client, server
import th130_house_fit as hf
from th130_arrangement_motion import sample, put

SR=44100
OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 Break Glitches 2026-10-17'
PROJECT=Path.home()/'Music/Ableton/Projects/TH130 - Groove Identity Project'
STAB,KEY,AIR,VOICE='09 Chicago Stab','10 House Keys','12 Atmosphere','16 Spoken Words'


def dump(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2))


def read(path):
    y,sr=sf.read(path,dtype='float32',always_2d=True)
    assert sr==SR and y.shape[1]==2
    return y


def pan(x,p):
    return x*np.sqrt(np.array([1-p,1+p],np.float32))


def prepare():
    assert not (OUT/'live-changes.json').exists(), 'Do not overwrite staged media.'
    state=json.loads((OUT/'before.json').read_text());events=[];assets=[];masks={}
    old={r:read(state['tracks'][r]['clips'][0]['file']) for r in (STAB,KEY,AIR)}
    # Work on raw PCM with the same clip gain as before, so material outside
    # the explicitly edited windows can remain bit-identical after import.
    y={r:x.copy() for r,x in old.items()}
    for r in old:masks[r]=np.zeros(len(old[r]),bool)
    vox={}
    for bar in (49,89):
        clip=next(c for c in state['tracks'][VOICE]['clips'] if c['start']==(bar-1)*4)
        vox[bar]=dict(clip=clip,old=read(clip['file']))
        vox[bar]['new']=vox[bar]['old'].copy()

    def replace(role,a,b,take,description):
        i,j=sample(a),sample(b);assert len(take)==j-i
        original=y[role][i:j].copy();w=np.ones(len(take),np.float32)
        edge=min(round(.004*SR),len(w)//4)
        w[:edge]=np.linspace(0,1,edge);w[-edge:]=np.linspace(1,0,edge)
        y[role][i:j]=original*(1-w[:,None])+take*w[:,None]
        masks[role][i:j]=True
        events.append(dict(role=role,from_beat=a,to_beat=b,action=description))

    def ratchet(role,source_at,begin,end,positions,durations,gains,cutoffs):
        take=np.zeros((sample(end)-sample(begin),2),np.float32)
        for k,(at,duration,gain,hz) in enumerate(zip(positions,durations,gains,cutoffs)):
            fragment=old[role][sample(source_at):sample(source_at)+sample(duration)].copy()
            fragment=hf.edge(hf.filt(fragment,hz),.004,.013)
            fragment=pan(fragment,(-1 if k%2==0 else 1)*.20)
            put(take,fragment,at-begin,gain)
        replace(role,begin,end,take,'Retrigger of existing tonal attack; alternate subtle pan')

    # Small hints first, more insistent cuts only when the drop is close.
    ratchet(KEY,173.787,174.70,175.70,[174.787,175.287],
            [.22,.16],[.72,.50],[3800,2900])  # bar 44, last two beats
    ratchet(KEY,205.787,207.,207.95,[207.,207.287,207.5,207.75],
            [.19,.16,.12,.10],[.70,.78,.65,.48],[2900,3600,4400,5400])
    ratchet(KEY,222.287,222.287,223.5,[222.287,222.787,223.037,223.287],
            [.27,.20,.15,.12],[1.,.77,.82,.58],[5700,4900,4000,3000])
    ratchet(KEY,349.787,351.,351.95,[351.,351.287,351.5],
            [.23,.19,.14],[.70,.85,.55],[3000,4100,5200])
    ratchet(STAB,374.5,374.5,375.40,[374.5,374.75,375.,375.25],
            [.17,.15,.13,.11],[.88,.68,.83,.60],[3300,4000,4800,5700])
    # The last half-beat stays clear in the upper motif before Drop II.
    ratchet(STAB,382.5,382.5,384.,[382.5,382.75,383.,383.125,383.25],
            [.19,.16,.09,.08,.10],[.95,.78,.90,.70,.62],[5700,5400,4600,3800,2900])
    replace(KEY,382.76,384.,np.zeros((sample(384)-sample(382.76),2),np.float32),
            'Let the stab finish the call; retain half-beat musical breathing room')

    def reverse(source,begin,end,peak,label):
        # Reversing timing leaves pitch intact; HP keeps these cues out of
        # kick/sub territory. No stretched or transposed foreign chord.
        length=sample(end)-sample(begin)
        fragment=source[-min(length,len(source)):][::-1].copy()
        fragment=np.pad(fragment,((length-len(fragment),0),(0,0)))
        fragment=hf.edge(hf.filt(hf.filt(fragment,550,'highpass'),4800),.025,.012)
        fragment*=peak/max(np.max(abs(fragment)),1e-9)
        fragment*=np.linspace(.15,1.,length,dtype=np.float32)[:,None]
        take=y[AIR][sample(begin):sample(end)].copy()+pan(fragment,.27)
        replace(AIR,begin,end,take,label)

    reverse(old[STAB][sample(184.5):sample(184.5)+sample(.50)],191.,191.875,.046,
            'Reverse of own Chicago chord anticipates Build I')

    for source_bar,positions,levels in [(49,[218.787,219.287],[1.,.66]),
                                       (89,[366.787,367.287,367.537],[1.,.72,.48])]:
        source=vox[source_bar]['old'];amp=np.max(abs(source),axis=1)
        voiced=np.flatnonzero(amp>.025);assert len(voiced)>0
        end=int(voiced[-1]);tail=source[max(0,end-sample(.72)):end+1].copy()
        assert np.max(abs(tail))>.03
        grain=hf.edge(hf.filt(hf.filt(tail,300,'highpass'),5200),.006,.018)
        grain*=.11/max(np.max(abs(grain)),1e-9)
        for k,(at,level) in enumerate(zip(positions,levels)):
            duration=.25 if k==0 else .19 if k==1 else .14
            shot=hf.edge(grain[:sample(duration)],.005,.018)
            local=at-(source_bar-1)*4
            existing=vox[source_bar]['old'][sample(local):sample(local)+len(shot)]
            assert np.max(abs(existing))<.01, 'Do not chop an intelligible phrase underneath.'
            put(vox[source_bar]['new'],pan(shot,(-1 if k%2==0 else 1)*.17),local,level)
        events.append(dict(role=VOICE,positions=positions,source_clip_bar=source_bar,
                           action='Quiet tail fragments answer the complete approved spoken phrase'))
        # A dark echo dissipates in the room rather than retriggering the
        # full vocal every bar. Echo is high-passed and below the dry fragments.
        at=positions[-1]+.5;shot=hf.edge(hf.filt(grain[:sample(.25)],2500),.007,.035)
        a,b=sample(at),sample(at)+len(shot)
        take=y[AIR][a:b].copy()+pan(shot,.32)*.23
        replace(AIR,at,at+len(shot)/(SR*60/130),take,'Filtered vocal-tail echo into shared atmosphere')
        if source_bar==89:
            reverse(tail,379.,379.875,.038,'Reverse vocal texture announces the final build bar')

    checks=[]
    for role,x in y.items():
        assert np.isfinite(x).all() and np.max(abs(x))<.70
        assert np.array_equal(x[~masks[role]],old[role][~masks[role]])
        path=OUT/f'{role} - detalhes de break.wav'
        sf.write(path,x,SR,subtype='PCM_24')
        back=read(path)
        assert np.array_equal(back[~masks[role]],old[role][~masks[role]])
        assets.append(dict(track=role,path=str(path),bar=1,beats=512,
                           name=role+' | cortes e respostas no break'))
        delta=x-old[role]
        below=hf.filt(delta,120)
        checks.append(dict(role=role,modified_seconds=float(masks[role].sum()/SR),
                           peak=float(np.max(abs(x))),delta_low_band_rms=float(np.sqrt(np.mean(below**2))),
                           outside_windows_bit_identical=True))
    for bar,v in vox.items():
        x=v['new'];assert np.isfinite(x).all() and np.max(abs(x))<.50
        # Whole original phrases remain unmodified; additions are in silence.
        active=np.max(abs(v['old']),axis=1)>.01
        assert np.array_equal(x[active],v['old'][active])
        path=OUT/f'{bar:03d}_{VOICE} - fragmentos de resposta.wav'
        sf.write(path,x,SR,subtype='PCM_24')
        assets.append(dict(track=VOICE,path=str(path),bar=bar,beats=32,
                           name='Spoken | frase inteira e resposta recortada'))
    dump('arrangement.json',dict(assets=assets,events=events,
         ranges={STAB:[[1,129]],KEY:[[1,129]],AIR:[[1,129]],VOICE:[[49,57],[89,97]]},
         reference_profile='Tracks 2027 Tech House Pista',record_master=False))
    dump('source-checks.json',dict(roles=checks,original_spoken_phrases_unchanged=True,
          kick_bass_and_drums_unchanged=True,scope='Source-domain checks; audition in Live determines musical fit.'))
    print('PREPARED',len(assets),'clips;',len(events),'gestures; source outside edits identical.',flush=True)


def stage():
    assert not (OUT/'live-changes.json').exists()
    state=json.loads((OUT/'before.json').read_text());plan=json.loads((OUT/'arrangement.json').read_text())
    for role,t in state['tracks'].items():
        assert client.call('get_track',dict(track=role,clips=True))==t,role
    assert not client.call('get_song')['is_playing']
    assert client.call('record_status').get('state') not in ('recording','finalizing')
    backup=PROJECT/'Production/Break Glitches';backup.mkdir(parents=True,exist_ok=True)
    shutil.copy2(PROJECT/'TH130 - Groove Identity.als',backup/'Before Break Glitches.als')
    log=[]
    for role,ranges in plan['ranges'].items():
        for first,last in ranges:
            asset=next(a for a in plan['assets'] if a['track']==role and a['bar']==first)
            commands=[dict(cmd='delete_clips_in_range',args=dict(track=role,start_bar=first,end_bar=last)),
                      dict(cmd='create_audio_clip',args=dict(track=role,path=asset['path'],bar=first,
                           name=asset['name'],warp=False,gain_db=0))]
            result=server.ableton_batch(commands)
            log.extend(dict(command=c,result=r) for c,r in zip(commands,result));dump('live-changes.json',log)
            assert all(r.get('ok') for r in result),result
            print('LIVE',role,first,flush=True)
    after={r:client.call('get_track',dict(track=r,clips=True)) for r in state['tracks']}
    for role in state['tracks']:
        if role not in plan['ranges']:assert after[role]==state['tracks'][role],role
    for a in plan['assets']:
        clip=next(c for c in after[a['track']]['clips'] if abs(c['start']-(a['bar']-1)*4)<.01)
        assert abs(clip['length']-a['beats'])<.01 and not clip['muted']
        previous=next(c for c in state['tracks'][a['track']]['clips'] if c['start']==clip['start'])
        assert clip['gain_db']==previous['gain_db']
    dump('after.json',after)
    print('VERIFIED: kick, bass, drums, strings and other effects unchanged.',flush=True)


if __name__=='__main__':
    {'prepare':prepare,'stage':stage}[sys.argv[1]]()
