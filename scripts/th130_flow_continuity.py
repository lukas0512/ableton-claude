"""Stagger the second break's withdrawals; connect the bass and ambience phrases.

Preserve the approved call/response, sources, spoken words and organised set.
Only replace the relevant ranges through ClaudeBridge; no master capture/export.
"""
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.ear import midi
import th130_house_fit as hf
import th130_string_signature as ss
import th130_pulse_story as story
from th130_arrangement_motion import put, sample, silence
from th130_remix_conversation import assemble

SR, BPM, BEAT = 44100, 130, 60/130
OUT = Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 Flow Continuity 2026-10-17'
RHYTHM = ['01 Kick','03 Clap','04 Closed Hat','05 Open Hat','06 Percussion','07 Chicago Top Loop']
RANGES = {r:(73,97) for r in RHYTHM+['09 Chicago Stab','10 House Keys']}
RANGES.update({'02 Sub Bass':(1,129),'12 Atmosphere':(1,129),'13 Uplifter':(73,81),'15 Sweep':(81,89)})


def dump(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2))


def ramp(beats, points):
    return np.asarray(PchipInterpolator([(b-1)*4 for b,_ in points],
                                      [v for _,v in points],extrapolate=True)(beats),np.float32)


def prepare():
    assert not (OUT/'live-changes.json').exists(),'Never rewrite staged media.'
    state=json.loads((OUT/'before.json').read_text());n=sample(512)
    y={r:assemble(state['tracks'][r],n) for r in RANGES}
    old_bass=y['02 Sub Bass'].copy(); y['02 Sub Bass'][:]=0
    shots=story.tones();held=story.bass_voice();notes=[];events=[];assets=[]
    # Alternating held and articulated second bars. The final pickup crosses
    # the bar line, but ends before the next anchor: connection without overlap.
    for bar in range(9,125,2):
        phrase=((bar-9)//2)%4
        pattern=[(23,.5,1.22,108),(23,2.775,.18,80),(30,3.5,.22,68),
                 (23,4.275,1.03,104),(23,5.775,.20,74),
                 (23,6.5,.86,99),(23,7.775,.42,82)]
        if phrase in (1,3):
            pattern=[(p,t,1.40 if t==4.275 else d,v) for p,t,d,v in pattern if t!=5.775]
        if phrase==2:
            pattern=[(23 if t==3.5 else p,t,.16 if t==3.5 else d,60 if t==3.5 else v)
                     for p,t,d,v in pattern]
        if phrase==3:
            pattern=[(p,t,.62 if t==6.5 else .50 if t==7.775 else d,v)
                     for p,t,d,v in pattern]
        strong=57<=bar<81 or 97<=bar<121
        gain=.19 if strong else .175;lp=12000;upper_mix=0.
        if 41<=bar<57:
            rel=bar-41
            gain*=.78 if rel<4 else .66 if rel<8 else .60
            lp=160 if rel<8 else 260
            if rel>=12:
                gain=.135;upper_mix=1.;lp=12000
        elif 73<=bar<97:
            gain=float(ramp((bar-1)*4,[(73,.19),(81,.19),(85,.183),(89,.17),(93,.151),(95,.145),(97,.145)]))
            lp=float(ramp((bar-1)*4,[(73,12000),(81,12000),(85,7000),(89,2400),(93,700),(95,1200),(97,1800)]))
            upper_mix=float(np.clip((bar-92)/3,0,1))
        for pitch,at,duration,vel in pattern:
            if bar==123 and at>=7.775: duration=.34
            global_at=(bar-1)*4+at
            note_mix=upper_mix;note_gain=gain;note_lp=lp
            if 73<=bar<97:
                # Evolve within the two-bar phrase too; the register handover
                # must not itself become a new block boundary at 93 or 95.
                note_mix=float(np.clip((bar+at/4-92)/3,0,1))
                note_gain=float(ramp(global_at,[(73,.19),(81,.19),(85,.183),(89,.17),(93,.151),(95,.145),(97,.145)]))
                note_lp=float(ramp(global_at,[(73,12000),(81,12000),(85,7000),(89,2400),(93,700),(95,1200),(97,1800)]))
            low=held(pitch,duration)
            if note_lp<10000:low=hf.filt(low,note_lp)
            note=low*(1-note_mix)
            if note_mix:note=note+held(pitch+12,duration)*note_mix
            put(y['02 Sub Bass'],note,global_at,note_gain*vel/108)
            notes.append([pitch+12 if note_mix==1 else pitch,global_at,duration,vel])
            events.append(dict(bar=bar,beat=at,length=duration,pitch=pitch,upper_mix=note_mix,gain=note_gain,velocity=vel))

    # Carry the actual full groove through 81. Remove open-hat energy later,
    # soften the kick after 84, withhold it only for the final two build bars.
    a,z=sample(288),sample(384)
    kick=y['01 Kick'][sample(256):sample(256)+sample(.85)].copy()
    assert np.max(abs(kick))>.05
    y['01 Kick'][a:z]=0
    for bar in range(73,95):
        for beat in range(4):
            at=(bar-1)*4+beat
            level=float(ramp(at,[(73,1.),(81,.99),(85,.92),(89,.80),(93,.66),(95,.38)]))
            hz=float(ramp(at,[(73,18000),(81,18000),(85,12000),(89,4300),(93,2200),(95,1500)]))
            put(y['01 Kick'],hf.filt(kick,hz),at,level)
    for role in RHYTHM[1:]:
        reference=y[role][sample(256):sample(288)].copy()
        for bar in range(73,97):
            begin,end=sample((bar-1)*4),sample(bar*4);count=end-begin
            i=sample(((bar-65)%8)*4)
            seg=reference[i:i+count].copy()
            if len(seg)<count:seg=np.pad(seg,((0,count-len(seg)),(0,0)))
            if role=='05 Open Hat':
                level=1. if bar<=82 else .80 if bar<=84 else .55 if bar<=88 else .32 if bar<=92 else 0.
                if bar in (86,88,90,92):level=0.
                seg*=level
            elif role=='07 Chicago Top Loop':
                level=float(ramp((bar-1)*4,[(73,.82),(81,.82),(85,.74),(89,.59),(93,.56),(97,.75)]))
                seg*=level
            else:
                level=float(ramp((bar-1)*4,[(73,1.),(81,1.),(85,.97),(89,.92),(93,.91),(97,.96)]))
                seg*=level
            if role!='03 Clap' and bar>=85:
                cutoff=float(ramp((bar-1)*4,[(85,11000),(89,6200),(93,4800),(97,10500)]))
                seg=hf.filt(seg,cutoff)
            y[role][begin:end]=seg

    # One voice continues across the supposed section edge: reproduce the
    # existing 77-80 cell at 81-84 and 85-88, then hand into the existing build.
    previous=json.loads((story.OUT/'arrangement.json').read_text())
    source_events=[e for e in previous['events'] if 304<=e['beat']<320]
    for role in ['09 Chicago Stab','10 House Keys']:
        y[role][sample(320):sample(352)]=0
    for base in (320,336):
        for e in source_events:
            at=base+e['beat']-304;role=e['role'];duration=e['duration_s']
            if base==336 and role=='K' and abs((at-base)%8-5.787)<.01:duration=.35
            cutoff=float(ramp(at,[(81,5700),(85,5500),(89,4800)]))
            shot=hf.edge(shots[role][:round(duration*SR)],.010 if role=='K' else .006,.04)
            shot=hf.filt(shot,cutoff)
            put(y['10 House Keys' if role=='K' else '09 Chicago Stab'],shot,at,e['gain'])
    # A soft key pickup anticipates the next phrase. Its echoes belong to the
    # atmosphere, rather than resetting every eight-bar audio boundary.
    for bar in (80,88):
        shot=hf.edge(hf.filt(shots['K'][:round(.16*SR)],3900),.010,.045)
        put(y['10 House Keys'],shot,(bar-1)*4+3.287,.085)
    voice=assemble(state['tracks']['16 Spoken Words'],n)
    env=ndimage.uniform_filter1d(abs(voice).mean(axis=1),size=round(.025*SR))
    for r in ['09 Chicago Stab','10 House Keys']:
        y[r][sample(320):sample(352)]*=(1-.16*np.clip(env[sample(320):sample(352)]/.025,0,1))[:,None]

    # Remove the false eight-bar noise promise/impact at 81. The musical
    # handover now carries itself; the actual lift into 97 remains in place.
    y['13 Uplifter'][sample(288):sample(320)]=0
    y['15 Sweep'][sample(320):sample(352)]=0

    # A continuous room thread: existing GRID texture, animated in long arcs,
    # plus filtered tails from the approved key and tonic string. No low-end bed.
    texture=hf.filt(hf.filt(ss.read('Odd Frequency - Grid Vol 2 - Texture 1 - 130 BPM.wav'),600,'highpass'),5200)
    texture*=.025/max(np.sqrt(np.mean(texture.astype(float)**2)),1e-9)
    cross=sample(1);stride=len(texture)-cross
    bed=np.zeros((n,2),np.float32)
    window=np.ones(len(texture),np.float32)
    window[:cross]=np.linspace(0,1,cross);window[-cross:]=np.linspace(1,0,cross)
    for i in range(0,n,stride):
        q=min(len(texture),n-i);bed[i:i+q]+=texture[:q]*window[:q,None]
    beats=np.arange(n,dtype=np.float32)/(SR*BEAT)
    envelope=np.clip(ramp(beats,[(1,.30),(7,.40),(9,.10),(21,.10),(25,.22),(33,.22),
         (37,.43),(41,.55),(47,.45),(49,.45),(55,.62),(57,.45),(61,.10),(69,.10),
         (73,.20),(77,.40),(81,.53),(85,.55),(89,.53),(93,.65),(97,.47),(101,.11),
         (113,.13),(117,.28),(121,.40),(127,.40),(129,0.)]),0,.7)
    # Slow spectral movement complements the native eight-bar pan cycle.
    dark=hf.filt(bed,2400);breath=(.5+.5*np.sin(2*np.pi*beats/64))[:,None]
    y['12 Atmosphere']=(bed*(.65+.35*breath)+dark*(.35-.35*breath))*envelope[:,None]
    for bar in (24,32,40,48,56,64,72,80,88,96,104,112,120):
        tail=hf.edge(hf.filt(hf.filt(shots['K'][:round(.30*SR)],500,'highpass'),2900),.012,.11)
        for offset,gain in [(.75,.095),(1.5,.057),(2.25,.034)]:
            put(y['12 Atmosphere'],tail[:,::-1] if offset==1.5 else tail,(bar-1)*4+3.287+offset,gain)
    tonic=next(c for c in state['tracks']['11 Strings']['clips'] if c['start']==320)
    release=hf.filt(loops.read(tonic['file']).astype(np.float32),700,'highpass')
    for offset,gain in [(1.5,.23),(3.,.12),(4.5,.065)]:
        put(y['12 Atmosphere'],hf.edge(release,.06,.6),320+offset,gain)
    y['12 Atmosphere']*=(1-.18*np.clip(env/.025,0,1))[:,None]

    # Sidechain uses actual kick placements, not a pump continuing in silence.
    for bar in range(1,129):
        for beat in range(4):
            at=(bar-1)*4+beat
            if np.max(abs(y['01 Kick'][sample(at):sample(at+.12)]))<.01:continue
            lo,hi=max(0,sample(at)-round(.006*SR)),min(n,sample(at)+round(.170*SR))
            t=np.arange(lo,hi)/SR-at*BEAT;g=np.ones(len(t),np.float32);pre=t<0
            g[pre]=1-.72*(.5-.5*np.cos(np.pi*(t[pre]+.006)/.006))
            q=np.clip((t[~pre]-.025)/.145,0,1);g[~pre]=.28+.72*(.5-.5*np.cos(np.pi*q))
            y['02 Sub Bass'][lo:hi]*=g[:,None]
    # Preserve the first transition's established gap, but not the old empty
    # half-beat before 81. Deepest bass remains connected through that downbeat.
    silence(y['02 Sub Bass'],159.5,160,.015)
    for bar in (56,96):
        silence(y['02 Sub Bass'],(bar-1)*4+3,bar*4,.025)
    for role in RHYTHM+['09 Chicago Stab','10 House Keys']:
        silence(y[role],383,384,.025)
    y['12 Atmosphere'][-round(.2*SR):]*=np.linspace(1,0,round(.2*SR))[:,None]

    for role,(first,last) in RANGES.items():
        segment=y[role][sample((first-1)*4):sample((last-1)*4)]
        assert np.isfinite(segment).all() and np.max(abs(segment))<.85,(role,np.max(abs(segment)))
        if np.max(abs(segment))<1e-7:continue
        p=OUT/f'{first:03d}_{role} - continuidade.wav';sf.write(p,segment,SR,subtype='PCM_24')
        assets.append(dict(track=role,path=str(p),bar=first,beats=(last-first)*4,
                           name=role+' | frase continua' if role in ['02 Sub Bass','12 Atmosphere'] else role+' | passagem encadeada'))
    # Assess the actual disputed boundary bar-by-bar in the source domain. This
    # excludes the limiter/returns: continuity evidence, not a master loudness claim.
    check=[]
    extras={r:assemble(state['tracks'][r],n) for r in ['08 Build Snare','11 Strings','14 Downlifter','16 Spoken Words']}
    rms=lambda x:float(20*np.log10(max(np.sqrt(np.mean(x.astype(float)**2)),1e-12)))
    for bar in range(77,98):
        i,j=sample((bar-1)*4),sample(bar*4)
        mix=sum(x[i:j]*10**(state['tracks'][r]['vol_db']/20) for r,x in dict(y,**extras).items())
        check.append(dict(bar=bar,mix_rms_db=round(rms(mix),2),bass_rms_db=round(rms(y['02 Sub Bass'][i:j]),2),
                          kick_rms_db=round(rms(y['01 Kick'][i:j]),2)))
    edge_drop=check[4]['mix_rms_db']-check[3]['mix_rms_db']
    assert edge_drop>-2.,('Still an abrupt source-level exit at 81',edge_drop)
    assert np.array_equal(y['02 Sub Bass'][:,0],y['02 Sub Bass'][:,1])
    dump('source-checks.json',dict(bars=check,delta_80_to_81_db=edge_drop,bass_mono=True,scope='Dry source sum, channel gains only; excludes native FX/master.'))
    midi.write(str(OUT/'Sub - antecipacoes e respiracao.mid'),[('Sub B0',0,notes)],BPM)
    dump('arrangement.json',dict(assets=assets,ranges=RANGES,bass_events=events,sources=dict(hf.SOURCES,**ss.SOURCES),
         approved_call_response_preserved=True,record_master=False))
    print('PREPARED',len(assets),'new clips; 80→81 dry-source change',round(edge_drop,2),'dB',flush=True)


def stage():
    state=json.loads((OUT/'before.json').read_text());plan=json.loads((OUT/'arrangement.json').read_text())
    for role in RANGES:
        live=client.call('get_track',dict(track=role,clips=True))
        assert [(c['start'],c['file'],c['gain_db']) for c in live['clips']]==[(c['start'],c['file'],c['gain_db']) for c in state['tracks'][role]['clips']],role
    log=json.loads((OUT/'live-changes.json').read_text()) if (OUT/'live-changes.json').exists() else []
    def apply(commands):
        results=server.ableton_batch(commands)
        log.extend(dict(command=c,result=r) for c,r in zip(commands,results));dump('live-changes.json',log)
        assert all(r.get('ok') for r in results),results
    result=server._journaled('transport',dict(action='stop'))
    log.append(dict(command=dict(cmd='transport',args=dict(action='stop')),result=result));dump('live-changes.json',log)
    apply([dict(cmd='set_loop',args=dict(on=False))])
    for role,(first,last) in RANGES.items():
        commands=[dict(cmd='delete_clips_in_range',args=dict(track=role,start_bar=first,end_bar=last))]
        for a in plan['assets']:
            if a['track']==role:commands.append(dict(cmd='create_audio_clip',args=dict(track=role,path=a['path'],bar=a['bar'],name=a['name'],warp=False,gain_db=0)))
        apply(commands);print('LIVE',role,flush=True)
    finish()


def finish():
    plan=json.loads((OUT/'arrangement.json').read_text())
    # Locator edits and transport wait for Live and must remain sequential.
    log=json.loads((OUT/'live-changes.json').read_text())
    for bar,name in [(81,'PASSAGEM II - groove atravessa'),(85,'RESPIRO II - camadas saem aos poucos'),
                     (93,'EXPECTATIVA - peso passa para o corpo')]:
        args=dict(bar=bar,name=name);r=server._journaled('set_cue',args)
        log.append(dict(command=dict(cmd='set_cue',args=args),result=r));dump('live-changes.json',log)
    for a in plan['assets']:
        t=client.call('get_track',dict(track=a['track'],clips=True))
        c=next(c for c in t['clips'] if abs(c['start']-(a['bar']-1)*4)<.01)
        assert abs(c['length']-a['beats'])<.01 and not c['muted'],a['track']
    dump('after.json',client.call('get_song'));print('READY - no master capture',flush=True)


if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'prepare'
    {'stage':stage,'finish':finish,'prepare':prepare}[action]()
