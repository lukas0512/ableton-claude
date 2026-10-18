"""Complementary house voicings and a growing response in the approved key timbre.

Keep the existing bass, phrase onsets, second-break handover and spoken words.
Source-domain checks/native playback only: the producer declined routine exports.
"""
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client, server
from ableton_claude.ear import midi
import th130_house_fit as hf
import th130_string_signature as ss
import th130_pulse_story as story
from th130_flow_continuity import ramp
from th130_arrangement_motion import put, sample, silence
from th130_remix_conversation import assemble

SR,BPM,BEAT=44100,130,60/130
OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 Harmonic Drive 2026-10-17'
ROLES=['09 Chicago Stab','10 House Keys','11 Strings','04 Closed Hat','05 Open Hat','07 Chicago Top Loop']


def dump(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2))


def key_voice(key):
    # The measured C#5 is already part of the approved chord. Separate its
    # narrow harmonic bands to redistribute that voice, rather than transpose
    # the entire sampled chord into unrelated keys. Shared upper harmonics are
    # not perfectly separable; retain most of the original shell and attack.
    voices=[]
    for ch in range(2):
        f,t,z=signal.stft(key[:,ch],SR,nperseg=8192,noverlap=7936)
        mask=np.zeros_like(f)
        for h in range(1,13):
            mask=np.maximum(mask,np.exp(-.5*((f-553.79*h)/max(8.,h*5.))**2))
        _,v=signal.istft(z*mask[:,None],SR,nperseg=8192,noverlap=7936)
        voices.append(v[:len(key)])
    voice=np.column_stack(voices).astype(np.float32)
    shell=key-.80*voice
    shell*=min(1.20,.94*np.sqrt(np.mean(key**2))/max(np.sqrt(np.mean(shell**2)),1e-9))
    voice=hf.edge(voice,.008,.035)
    voice/=max(np.max(abs(voice)),1e-9)
    return shell,voice


def prepare():
    assert not (OUT/'live-changes.json').exists(),'Do not overwrite staged audio.'
    state=json.loads((OUT/'before.json').read_text());n=sample(512)
    y={r:assemble(state['tracks'][r],n) for r in ROLES}
    shots=story.tones();shell,voice=key_voice(shots['K']);events=[];lead_notes=[];string_notes=[]
    sf.write(OUT/'Key - complementary shell.wav',shell,SR,subtype='FLOAT')
    sf.write(OUT/'Key - extracted C sharp voice.wav',voice,SR,subtype='FLOAT')
    pulse=json.loads((story.OUT/'arrangement.json').read_text())
    phrases=[e.copy() for e in pulse['events'] if not 320<=e['beat']<352]
    # Preserve the actual continuation introduced in the last pass at 81.
    source=[e for e in pulse['events'] if 304<=e['beat']<320]
    for base in (320,336):
        for e in source:
            v=e.copy();v['beat']=base+e['beat']-304
            v['cutoff']=float(ramp(v['beat'],[(81,5700),(85,5500),(89,4800)]))
            if base==336 and v['role']=='K' and abs((v['beat']-base)%8-5.787)<.01:v['duration_s']=.35
            phrases.append(v)
    for bar in (80,88):
        phrases.append(dict(role='K',beat=(bar-1)*4+3.287,duration_s=.16,gain=.085,cutoff=3900))
    for r in ['09 Chicago Stab','10 House Keys']:y[r][:]=0
    for e in sorted(phrases,key=lambda e:e['beat']):
        r=e['role'];at=e['beat'];bar=at/4+1;seconds=e['duration_s'];g=e['gain'];hz=e['cutoff']
        strong=57<=bar<85 or 97<=bar<121
        if r=='S':
            # Give the main Chicago chord enough body to answer the keys;
            # the quiet pickup stays short rather than swelling every hit.
            duration=min(.23,max(.16,seconds*1.35)) if strong and g>.14 else seconds
            shot=hf.edge(shots['S'][:round(duration*SR)],.006,min(.045,duration*.38))
            shot=hf.filt(shot,min(6500,hz*1.12 if strong else hz))
            put(y['09 Chicago Stab'],shot,at,g*(1.24 if strong else 1.04))
            continue
        # The same reply slots now trace F#–D / E–C#–B, rather than stacking
        # the exact same full Bm9 voicing against every Bm stab. The sub retains B.
        local=at%8;pair=int(at//8)%2
        if abs(local-1.787)<.04:pitch=78 if pair==0 else 76
        elif abs(local-5.787)<.04:pitch=74 if pair==0 else 73
        elif abs(local-6.287)<.05:pitch=73
        elif abs(local-3.5)<.04:pitch=78
        else:pitch=71
        reveal=.38 if bar<17 else .60 if bar<25 else .82 if bar<41 else .88 if bar<57 else 1.
        # Full chord shell stays on the principal replies; tiny ornaments carry
        # mainly the upper voice so the new melody does not thicken every gap.
        principal=abs(local-1.787)<.04 or abs(local-5.787)<.04
        chord_gain=g*(1.12 if strong else 1.04)*(1. if principal else .72)
        chord=hf.edge(shell[:round(seconds*SR)],.010,min(.05,seconds*.38))
        chord=hf.filt(chord,min(6800,hz+450 if strong else hz))
        put(y['10 House Keys'],chord,at,chord_gain)
        dur=min(.31,max(.10,seconds*.95))
        melodic=ss.pitch(voice,72.982,pitch,dur,.008,.035)
        melodic=hf.filt(melodic,min(6800,hz+600))
        gain=g*.52*reveal
        put(y['10 House Keys'],melodic,at,gain)
        lead_notes.append([pitch,at,dur/BEAT,min(127,round(gain/.105*104))])
        events.append(dict(beat=at,pitch=pitch,duration_s=dur,shell_gain=chord_gain,lead_gain=gain))
    # The strings share F# / A / C# / B with the upper keys. Remove the old G
    # semitone rub against F# and resolve the prepared upper voice into tonic B.
    y['11 Strings'][:]=0
    raw=hf.filt(ss.read('TOMM_MIRAGE_LIFESTRINGS_C5.wav'),230,'highpass');raw/=np.max(abs(raw))
    def string(pitch,at,beats,gain,opening=False):
        take=ss.pitch(raw,84.026,pitch,beats*BEAT,.18,.18)
        if opening:
            dark=hf.filt(take,1500);bright=hf.filt(take,5200)
            progress=np.linspace(0,1,len(take),dtype=np.float32)[:,None]
            take=(dark*(1-progress)+bright*progress)*(.35+.65*progress**1.2)
        else:take=hf.filt(take,3600)
        put(y['11 Strings'],take,at,gain)
        string_notes.append([pitch,at,beats,min(127,round(gain/.14*105))])
    for first,bars in [(37,4),(49,8),(77,4),(89,8)]:
        start=(first-1)*4
        string(66,start,bars*4-1.5,.13 if bars==8 else .105,True)
        if bars==8:
            string(69,start+16,6,.045)
            string(73,start+24,6.5,.052)
        else:string(69,start+12,2.5,.035)
    for first in (41,57,81,97):string(71,(first-1)*4,3.5,.040)

    # Strong sections gain drive through open-hat articulation, not extra
    # channels or master gain. Closed hats hand over explicitly at each open hit.
    closed=ss.read('3Q_TT2_Hat_14.wav');opened=ss.read('3Q_TT2_Hat_01.wav')
    for first,last in [(57,85),(97,121)]:
        lo,hi=sample((first-1)*4),sample((last-1)*4)
        y['04 Closed Hat'][lo:hi]=0;y['05 Open Hat'][lo:hi]=0
        for bar in range(first,last):
            base=(bar-1)*4
            for at,vel in [(1.5,.86 if bar%2 else .74),(3.5,.75 if bar%2 else .91)]:
                put(y['04 Closed Hat'],hf.edge(closed[:round(.065*SR)],.001,.018),base+at,.235*vel)
            ghosts=[(.287,.25),(1.787,.33),(3.287,.28)] if bar%2 else [(.787,.28),(1.787,.32),(3.787,.35)]
            for at,vel in ghosts:
                put(y['04 Closed Hat'],hf.edge(closed[:round(.040*SR)],.001,.012),base+at,.18*vel)
            for at,gain,duration in [(.5,.18 if bar%2 else .125,.15),(2.5,.125 if bar%2 else .18,.14)]:
                put(y['05 Open Hat'],hf.edge(opened[:round(duration*SR)],.002,.035),base+at,gain)
    beats=np.arange(n,dtype=np.float32)/(BEAT*SR)
    drive=ramp(beats,[(1,1.),(17,1.),(25,1.10),(33,1.14),(41,1.05),(49,1.08),
                      (57,1.24),(65,1.28),(73,1.24),(81,1.24),(85,1.19),(89,1.10),
                      (93,1.10),(97,1.28),(105,1.32),(113,1.25),(121,1.),(129,1.)])
    y['07 Chicago Top Loop']*=drive[:,None]
    spoken=assemble(state['tracks']['16 Spoken Words'],n)
    env=ndimage.uniform_filter1d(abs(spoken).mean(axis=1),size=round(.025*SR))
    for r in ['09 Chicago Stab','10 House Keys']:y[r]*=(1-.16*np.clip(env/.025,0,1))[:,None]
    for bar in (56,96):
        for r in ['09 Chicago Stab','10 House Keys','04 Closed Hat','05 Open Hat','07 Chicago Top Loop']:
            silence(y[r],(bar-1)*4+3,bar*4,.025)
    for r in ['04 Closed Hat','05 Open Hat']:silence(y[r],446,448,.020)
    assets=[]
    for r,x in y.items():
        assert np.isfinite(x).all() and np.max(abs(x))<.85,(r,np.max(abs(x)))
        p=OUT/f'{r} - harmonia e impulso.wav';sf.write(p,x,SR,subtype='PCM_24')
        assets.append(dict(track=r,path=str(p),bar=1,beats=512,name=r+' | vozes e impulso'))
    assert {n[0]%12 for n in lead_notes} <= {11,1,2,4,6,9}
    assert {n[0]%12 for n in string_notes} <= {11,1,2,6,9}
    midi.write(str(OUT/'Keys - voz superior e resolucao.mid'),[('Upper house-key voice',0,lead_notes)],BPM)
    midi.write(str(OUT/'Strings - notas comuns e resolucao.mid'),[('Common-tone strings',0,string_notes)],BPM)
    dump('arrangement.json',dict(bpm=BPM,tonic='B minor',assets=assets,key_events=events,
         lead_notes=lead_notes,string_notes=string_notes,sources=dict(hf.SOURCES,**ss.SOURCES),
         voicings='B minor stab; Bm7-like key shell with F#-D / E-C#-B upper response',
         master_unchanged=True,no_recording=True))
    print('PREPARED',len(assets),'roles;',len(lead_notes),'key replies;',len(string_notes),'string voices',flush=True)


def stage():
    before=json.loads((OUT/'before.json').read_text());plan=json.loads((OUT/'arrangement.json').read_text())
    for r in ROLES:
        t=client.call('get_track',dict(track=r,clips=True))
        assert [(c['start'],c['file'],c['gain_db']) for c in t['clips']]==[(c['start'],c['file'],c['gain_db']) for c in before['tracks'][r]['clips']],r
    log=[]
    result=server._journaled('transport',dict(action='stop'));log.append(dict(cmd='transport',result=result))
    for a in plan['assets']:
        commands=[dict(cmd='delete_clips_in_range',args=dict(track=a['track'],start_bar=1,end_bar=130)),
                  dict(cmd='create_audio_clip',args=dict(track=a['track'],path=a['path'],bar=1,name=a['name'],warp=False,gain_db=0))]
        res=server.ableton_batch(commands);log.extend(dict(command=c,result=r) for c,r in zip(commands,res))
        dump('live-changes.json',log);assert all(r.get('ok') for r in res),res
        print('LIVE',a['track'],flush=True)
    for r in ROLES:
        t=client.call('get_track',dict(track=r,clips=True));assert t['n_clips']==1 and abs(t['clips'][0]['length']-512)<.01,r
    dump('after.json',client.call('get_song'));print('READY - native audition, no recording',flush=True)


if __name__=='__main__':
    stage() if len(sys.argv)>1 and sys.argv[1]=='stage' else prepare()
