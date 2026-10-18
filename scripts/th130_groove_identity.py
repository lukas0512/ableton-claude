"""Revoice the instrumental pocket around the producer's preferred post-2m part.

Existing saved Spatial project is the rollback. Replace six roles in place through
ClaudeBridge; retain the organised channels and native spatial effects. No vocals.
"""
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client,server
from ableton_claude.ear import midi
import th130_house_fit as hf
import th130_string_signature as ss
from develop_th130_track import SECTIONS
from th130_arrangement_motion import CHAPTERS,edges,put,sample,silence

SR,BPM,BEAT=44100,130,60/130
OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 Groove Identity 2026-10-17'
ROLES=['03 Clap','04 Closed Hat','05 Open Hat','06 Percussion','09 Chicago Stab','10 House Keys']
EVENTS,ASSETS=[],[]
SWING=.287 # 57.4%: measured from the Chicago top loop, not an independent random feel.


def C(cmd,**args):
    p=OUT/'live-changes.json';log=json.loads(p.read_text()) if p.exists() else []
    r=server._journaled(cmd,args);log.append(dict(cmd=cmd,args=args,result=r))
    p.write_text(json.dumps(log,ensure_ascii=False,indent=2));return r


def edge(x,duration,attack=.004,release=.025):
    return hf.edge(x[:round(duration*SR)],attack,min(release,duration*.4))


def prepare():
    assert not (OUT/'arrangement.json').exists(),'Inspect existing pass before preparing it again.'
    n=sample(512);y={r:np.zeros((n,2),np.float32) for r in ROLES}
    clap=ss.read('3Q_TT2_Clap_02.wav')
    closed=ss.read('3Q_TT2_Hat_14.wav');opened=ss.read('3Q_TT2_Hat_01.wav')
    bongo=hf.filt(hf.filt(ss.read('SOBV2_PERCUSSION_umbongo_hit.wav'),160,'highpass'),6500)
    bongo*=.75/max(np.max(abs(bongo)),1e-9)
    raw=hf.filt(hf.source('wasc_key_housey_Bmin9.wav','/resampled & effected/'),200,'highpass')
    upper=signal.resample_poly(raw,1,2,axis=0).astype(np.float32)
    key=hf.filt(.55*raw[:len(upper)]+.60*upper,6800);key/=np.max(abs(key))
    mid=key.mean(axis=1);side=(key[:,0]-key[:,1])*.5;side-=hf.filt(side[:,None],300)[:,0]
    key=np.column_stack([mid+side*1.08,mid-side*1.08]).astype(np.float32);key/=np.max(abs(key))
    stab=hf.filt(ss.read('PL_DTP2_Reveal_Sample_ChicagoKey_G3.wav'),210,'highpass')
    stab=hf.filt(ss.pitch(stab,66.85,71,.65,.007,.06),5700);stab/=np.max(abs(stab))
    mid=stab.mean(axis=1);stab=.70*np.column_stack([mid,mid])+.30*stab
    tones={'09 Chicago Stab':stab,'10 House Keys':key}

    def hit(role,at,seconds,gain,cutoff=None):
        shot=edge(tones[role],seconds,.010 if role=='10 House Keys' else .006,.04)
        if cutoff:shot=hf.filt(shot,cutoff)
        # Shared fixed pocket, not per-note timing randomisation. The key's soft
        # attack stays intact and sits slightly behind the percussion transient.
        put(y[role],shot,at,gain)
        EVENTS.append(dict(role=role,beat=at,duration_s=seconds,gain=gain,cutoff=cutoff))

    # Interlocking two-bar phrase: bass pickup at 2.775 answered by short stab
    # at 2.787; keys anticipate the next kick at 1.787 and the bass release at
    # 5.795 with a longer answer at 5.787. Same chord colours, new musical syntax.
    core=[('S',.5,.10,.62),('K',1.5+SWING,.23,.95),('S',2.5+SWING,.10,1.),
          ('S',4+SWING,.17,.88),('K',5.5+SWING,.30,1.),('K',7+SWING,.11,.55)]
    for start,end,label,kind in SECTIONS:
        bars=end-start;strong=kind in ('drop','final');no_low=kind in ('break','air','build','build2')
        for b in range(bars):
            base=start*4+b*4
            drum_gain=.58 if no_low else .78 if kind=='intro' else 1.
            # Firm backbeat, seven milliseconds behind the kick grid.
            for at,vel in [(1,112 if b%2==0 else 110),(3,106 if b%2==0 else 104)]:
                put(y['03 Clap'],edge(clap,.24,.001,.03),base+at+.007/BEAT,.55*vel/110*drum_gain)
            # Off-beat eighths carry the hat phrase. Quiet delayed sixteenths
            # connect those accents; loud on-beat ticks no longer double the kick.
            accents=[(.5,76),(1.5,86),(2.5,70),(3.5,89)] if b%2==0 else [(.5,82),(1.5,72),(2.5,88),(3.5,71)]
            if kind=='intro' and b<4:accents=[(1.5,68),(3.5,72)]
            open_at=[.5] if b%2==0 else [2.5]
            if b%8==5:open_at.append(3.5)
            if kind in ('intro','break','air','build','build2','outro'):open_at=[]
            for at,vel in accents:
                if at in open_at:continue # explicit closed/open hat handover
                put(y['04 Closed Hat'],edge(closed,.065,.001,.018),base+at,.235*vel/100*drum_gain)
            ghosts=[(SWING,25),(1.5+SWING,34),(3+SWING,29)] if b%2==0 else [(.5+SWING,28),(1.5+SWING,32),(3.5+SWING,36)]
            if kind!='intro' or b>=4:
                for at,vel in ghosts:put(y['04 Closed Hat'],edge(closed,.04,.001,.012),base+at,.18*vel/100*drum_gain)
            for at in open_at:put(y['05 Open Hat'],edge(opened,.19,.002,.035),base+at,.18*(1.08 if strong else .95))
            # Same-pack dry bongo supplies a recognisable lower-mid answer.
            perc=[(.5+SWING,.28),(2.5,.85),(3.5+SWING,.30)] if b%2==0 else [(1.5,.75),(2.5+SWING,.27),(3.5,.58)]
            if kind=='intro' and b<4:perc=[]
            if kind=='outro' and b>=6:perc=[]
            for at,vel in perc:
                shot=edge(bongo,.145 if vel>.5 else .085,.002,.025)
                if vel<.5:shot=hf.filt(shot,3200)
                put(y['06 Percussion'],shot,base+at,.18*vel*drum_gain)

        if kind=='intro':
            hit('09 Chicago Stab',start*4+22.5,.10,.055,1900)
            hit('10 House Keys',start*4+29.5+SWING,.20,.07,2700)
            continue
        if kind=='outro':continue
        for pair in range(bars//2):
            base=start*4+pair*8
            if kind=='groove' and pair<2:continue
            gain=.19 if strong else .16 if kind=='hook' else .13
            cutoff=5700 if strong else 4200 if kind=='hook' else 3200
            pattern=core
            # A recurring tail changes once per eight bars; the main accents stay.
            if pair%4==2:
                pattern=core[:-1]+[('K',3.5,.11,.45),('S',7.5+SWING,.075,.42)]
            elif pair%4==3:pattern=core[:-1]
            if kind=='groove':pattern=core if pair>=4 else [core[1],core[2],core[4]]
            if kind=='drop' and pair<2:pattern=[core[0],core[1],core[3],core[4]]
            if kind in ('break','air'):
                gain=.15 if kind=='break' else .14
                cutoff=2100+pair*650
                if pair==0:
                    hit('10 House Keys',base,.65,gain,cutoff)
                    pattern=[core[2],core[4]]
                else:pattern=core if pair>1 else [core[0],core[1],core[3],core[4]]
            if kind in ('build','build2'):
                gain=.10+pair*.018;cutoff=1000*(5700/1000)**(pair/3)
                pattern=core if pair<3 else [('S',at,.08,.8 if i%2==0 else .5)
                                             for i,at in enumerate([.5,1.5,2.5,3.5,4.5,5.,5.5,6.,6.5])]
                if pair<3:pattern=pattern+[('S',7.5,.08,.4)]
            for role,offset,seconds,vel in pattern:
                hit('10 House Keys' if role=='K' else '09 Chicago Stab',base+offset,seconds,gain*vel,cutoff)

    # Keep prepared exits, without four empty bars in the harmonic conversation.
    for bar in (40,80):
        for role in ['03 Clap','04 Closed Hat','05 Open Hat','06 Percussion']:
            silence(y[role],(bar-1)*4+3,bar*4,.02)
    for bar in (56,96):
        for z in y.values():silence(z,(bar-1)*4+3,bar*4,.025)
    for role in ['04 Closed Hat','05 Open Hat','06 Percussion']:
        silence(y[role],(112-1)*4+2,112*4,.02)
        y[role][sample(496):]*=np.linspace(1,10**(-3/20),len(y[role])-sample(496))[:,None]
    for z in y.values():z[-round(.1*SR):]*=np.linspace(1,0,round(.1*SR))[:,None]
    for role,z in y.items():
        assert np.isfinite(z).all() and np.max(abs(z))<.85,(role,np.max(abs(z)))
        for bar,label in CHAPTERS.items():
            chunk=edges(z[sample((bar-1)*4):sample((bar+7)*4)],.001,.003)
            if np.max(abs(chunk))<1e-7:continue
            p=OUT/f'{bar:03d}_{role}.wav';sf.write(p,chunk,SR,subtype='PCM_24')
            ASSETS.append(dict(track=role,path=str(p),bar=bar,name=role+' | shared pocket',beats=32))
    midi.write(str(OUT/'Stab Keys - shared pocket.mid'),[(role,i,[[71,e['beat'],e['duration_s']/BEAT,
               min(127,round(e['gain']/.19*100))] for e in EVENTS if e['role']==role])
               for i,role in enumerate(['09 Chicago Stab','10 House Keys'])],BPM)
    (OUT/'arrangement.json').write_text(json.dumps(dict(bpm=BPM,key='B minor',core=core,events=EVENTS,
        assets=ASSETS,sources=dict(hf.SOURCES,**ss.SOURCES),upper_swing_pct=57.4,
        guide='Producer preferred post-2-minute instrumental section; preserve bass and timbres.',
        choice='Develop the existing pocket rather than replace bass/harmony with an unrelated idea.'),ensure_ascii=False,indent=2))
    print('PREPARED',len(ASSETS),'clips',flush=True)


def stage():
    state=json.loads((OUT/'before.json').read_text());plan=json.loads((OUT/'arrangement.json').read_text())
    C('transport',action='stop');C('set_loop',on=False)
    for role in ROLES:
        current=client.call('get_track',dict(track=role,clips=True));old=state['tracks'][role]
        assert [(c['start'],c['file']) for c in current['clips']]==[(c['start'],c['file']) for c in old['clips']],role
        C('delete_clips_in_range',track=role,start_bar=1,end_bar=130)
        for a in plan['assets']:
            if a['track']==role:C('create_audio_clip',track=role,path=a['path'],bar=a['bar'],name=a['name'],warp=False,gain_db=0)
        print('LIVE',role,flush=True)
    for name in ['11 Vocal Lead','12 Vocal FX']:C('set_track',track=name,mute=True)
    for name,db in [('07 Chicago Top Loop',-4),('08 Build Snare',-4),('15 Uplifter',-3),('13 Strings',-3.5)]:
        C('set_track',track=name,volume_db=db)
    C('set_param',track='10 House Keys',device=1,param='Amount',value=.18)
    C('set_send',track='10 House Keys',send=1,db=-28)
    C('set_send',track='09 Chicago Stab',send=2,db=-23)
    for bar,name in [(1,'INTRO - tonal hint'),(17,'POCKET - reveal the cell'),(25,'HOOK - stab and key lock'),
        (41,'BREAK I - tonic and pulse'),(57,'DROP I - bass and dialogue'),(65,'POCKET - preferred passage developed'),
        (73,'GROOVE - tail variation'),(81,'BREAK II - harmonic breath'),(97,'DROP II - full pocket'),
        (105,'HOOK - recurring answer'),(113,'FINAL - last statement')]:C('set_cue',bar=bar,name=name)
    for role in ROLES:
        t=client.call('get_track',dict(track=role,clips=True))
        assert t['n_clips']==len([a for a in plan['assets'] if a['track']==role])
        assert all(abs(c['length']-32)<.01 for c in t['clips'])
    (OUT/'after.json').write_text(json.dumps(client.call('get_song'),indent=2))
    print('READY',flush=True)


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='stage':stage()
    else:prepare()
