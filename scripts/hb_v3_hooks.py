"""V3: sung reggae, a native Meld hook, purposeful builds and phrase-end drums."""
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client,loops,server
from ableton_claude.ear import midi

OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB163_V3_20261020'
V2=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB155_ReggaeBreak_20261020'
KIT=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB155_Tutty_20261020'
PROJECT=Path.home()/'Music/Ableton Claude/Projects/Hard Bounce 155 - Tutty Sketch Project'
SR,BPM=44100,163
BEAT=60/BPM
LOG=[]


def dump(name,x): (OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2))


def C(cmd,**args):
    r=server._journaled(cmd,args);LOG.append(dict(cmd=cmd,args=args,result=r));dump('v3-changes.json',LOG)
    print(cmd,str(r)[:110],flush=True);return r


def batch(commands):
    r=server.ableton_batch(commands);LOG.extend(dict(command=c,result=x)for c,x in zip(commands,r));dump('v3-changes.json',LOG)
    assert all(x.get('ok')for x in r),r
    print('batch',len(r),'OK',flush=True)


def filt(x,f,kind='lowpass'):
    return signal.sosfilt(signal.butter(2,f,kind,fs=SR,output='sos'),x,axis=0)


def edge(x,a=.003,b=.025):
    x=x.copy();na=min(len(x),round(a*SR));nb=min(len(x),round(b*SR))
    if na:x[:na]*=np.linspace(0,1,na)[:,None]
    if nb:x[-nb:]*=np.linspace(1,0,nb)[:,None]
    return x


def put(y,x,beat,g=1):
    a=round(beat*BEAT*SR);n=min(len(x),len(y)-a)
    if a>=0 and n>0:y[a:a+n]+=x[:n]*g


def peak(x):return x/max(float(abs(x).max()),1e-9)


def prepare():
    assert not (OUT/'v3-plan.json').exists(),'Already prepared.'
    state=client.call('get_song');assert not state['is_playing']
    dump('pre-edit-song.json',state)
    score=json.loads((V2/'score.json').read_text())
    # Anchor stays; variations live at phrase endings and in support voices.
    for tr in ['HB 04 HAT tight','HB 05 HAT offbeat','HB 08 PERC reply']:
        score[tr]=[n for n in score[tr]if 128<=n[1]<160]
    score['HB 07 SNARE build']=[n for n in score['HB 07 SNARE build']if n[1]>=64]
    score['HB 01 KICK']=[n for n in score['HB 01 KICK']if not(int(n[1]//4)in[23,31,47,55]and n[1]%4>=3)]
    score['HB 02 DONK F1']=[n for n in score['HB 02 DONK F1']if not(int(n[1]//4)in[23,31,47,55]and n[1]%4>=3)]
    def add(tr,p,t,d,v):score[tr].append([p,t,d,v])
    for bar in range(16,56):
        if 32<=bar<40:continue
        transition=bar in[23,31,47,55]
        if bar in[23,47]:add('HB 01 KICK',60,bar*4+3.5,.22,95)
        for st in range(16):
            if bar<24 and st%2:continue
            if bar%2==0 and st in[7,11]:continue
            if transition and st>=12:continue
            v=[77,66,108,72][st%4]+(3 if bar>=48 else 0)
            add('HB 04 HAT tight',60,bar*4+st/4+(.008 if st%2 else 0),.07,v)
        for at in[.5,1.5,2.5,3.5]:
            if bar%2 and at==2.5:continue
            if transition and at>=3:continue
            add('HB 05 HAT offbeat',60,bar*4+at,.20,106 if at%2==.5 else 112)
        if bar%2:
            for at,v in[(.75,84),(2.25,92),(3.75,75)]:
                if transition and at>=3:continue
                add('HB 08 PERC reply',60,bar*4+at+.008,.09,v)
        if bar%4==3 and not transition:
            for at,v in[(2.75,74),(3.5,87),(3.75,79)]:
                add('HB 07 SNARE build',60,bar*4+at+.008,.08,v)
            add('HB 04 HAT tight',60,bar*4+3.875,.06,78)
    # Build develops the motif; the roll is a short final punctuation.
    for bar in[4,6]:
        for at,v in[(.75,75),(2.75,86)]:add('HB 08 PERC reply',60,bar*4+at+.008,.09,v)
    for bar in range(8,12):
        for at in[.5,1.5,2.5,3.5]:add('HB 04 HAT tight',60,bar*4+at,.07,85 if at<2 else 91)
    for bar in range(8):
        for at,v in[(.5,86),(1.5,80),(2.5,94),(3.5,83)]:
            add('HB 04 HAT tight',60,bar*4+at,.07,v+(3 if bar>=4 else 0))
    for bar in range(4,8):
        for at,v in[(1,85),(3,91)]:add('HB 03 CLAP',60,bar*4+at,.12,v)
    for t,v in[(51.25,73),(51.5,87),(55.5,79)]:add('HB 07 SNARE build',60,t,.10,v)
    for at,v in[(0,84),(.75,87),(1.5,91),(2.5,96),(3,101),(3.5,105)]:
        add('HB 07 SNARE build',60,56+at,.10,v)
    for at,v in[(0,90),(.5,94),(1,98),(1.5,102),(2,107),(2.25,111),(2.5,115)]:
        add('HB 07 SNARE build',60,60+at,.07,v)
    for tr in score:score[tr].sort(key=lambda n:(n[1],n[0]))
    dump('drum-score.json',score)
    base=json.loads((OUT/'hook-cell.json').read_text())
    hooks=[]
    # Instrument answers the vocal. The same cell, with a recognisable turnaround.
    for start,bars in[(16,8),(28,4),(40,4),(48,8)]:
        for p,t,d,v in base:
            if t>=bars*4:continue
            at=start*4+t
            if int(at//4)in[23,31,55]and at%4>=3:continue
            hooks.append([p,at,d,v])
    dump('hook-score.json',hooks)
    meter=json.loads((OUT/'hook-prototype-analysis.json').read_text())['loudness']['integrated_lufs']
    native_db=min(5.0,-14+(-25-meter))
    gain=10**((native_db+14)/20)
    dry=loops.read(str(OUT/'Hook prototype dry.wav'),SR)[:round(32*BEAT*SR)]*gain
    def take(a,b):return dry[round(a*BEAT*SR):round(b*BEAT*SR)]
    hint=edge(take(0,1.12),.002,.025);question=take(0,4);cell=take(0,8)
    build=np.zeros((round(64*BEAT*SR),2),np.float32)
    for at,hz,g in[(0,850,.65),(8,1200,.72),(16,1700,.85),(24,2100,.92)]:
        put(build,filt(hint if at<16 else question,hz),at,g)
    put(build,filt(hint,2200),46,.75)
    put(build,filt(cell,2700),48,.95)
    put(build,filt(question,3800),56,1.08)
    small=edge(take(.25,.65),.002,.012)
    for at,g in[(60,.8),(60.5,.9),(61,1),(61.5,1.06)]:put(build,small,at,g)
    pitched=signal.resample_poly(small,10000,round(10000*2**(7/12)),axis=0)
    put(build,pitched,62,1.0)
    build[round(63*BEAT*SR):]=0
    bb=np.arange(len(build))/SR/BEAT
    build*=np.interp(bb,[0,15.9,16,47,48,64],[2**.5,2**.5,1,1,2,2])[:,None]
    sf.write(OUT/'Build - motif reveal 163.wav',edge(build),SR,subtype='PCM_24')
    index=json.loads((Path(__file__).resolve().parents[1]/'knowledge/samples_index.json').read_text())['items']
    src=next(x['path']for x in index if Path(x['path']).name=='SMO_140_F_LU_Melody.wav')
    vocal=loops.read(src,SR);vocal=np.repeat(vocal.mean(axis=1,keepdims=True),2,axis=1)
    vocal=filt(filt(vocal,105,'highpass'),9000)
    phrases={}
    # Full lyric boundaries checked by local speech transcription, not filenames.
    for name,a,b,beats in[('Alive',0,5.66,16),('Verse',0,10.96,32),('Someone',19.56,24.75,16)]:
        x=edge(vocal[round(a*SR):round(b*SR)],.003,.040)
        env=np.sqrt(signal.lfilter([1/882]*882,[1],np.mean(x*x,axis=1))+1e-12)
        db=20*np.log10(env+1e-8);reduction=np.maximum(db+24,0)*(1-1/3)
        x*=10**(-reduction[:,None]/20)
        x=peak(x)*.71
        n=round(beats*60/140*SR);x=np.pad(x,((0,max(0,n-len(x))),(0,0)))[:n]
        before=OUT/(name+' - 140 source.wav');after=OUT/(name+' - 163 sung.wav')
        sf.write(before,x,SR,subtype='PCM_24')
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(before),'-af','atempo=1.1642857142857144','-c:a','pcm_s24le',str(after)],check=True)
        y=loops.read(str(after),SR);target=round(beats*BEAT*SR)
        y=np.pad(y,((0,max(0,target-len(y))),(0,0)))[:target];y=edge(y,.002,.025)
        sf.write(after,y,SR,subtype='PCM_24');phrases[name]=y
    # Only a handful of derived accents; no continuous noise riser.
    fx=np.zeros((round(224*BEAT*SR),2),np.float32)
    rev=peak(edge(filt(hint[::-1],450,'highpass'),.02,.004))
    rev=rev[-round(.18*SR):]
    for end,g in[(32,.035),(64,.055),(160,.055)]:put(fx,rev,end-len(rev)/SR/BEAT-.025,g)
    conga_src=next(x['path']for x in index if Path(x['path']).name=='909Conga_01_SP.wav')
    conga=peak(edge(filt(loops.read(conga_src,SR),160,'highpass')))
    for beat in[95.25,143.0,191.25]:
        for i,ratio in enumerate([1.2,1,.85]):
            hit=signal.resample_poly(conga,1000,round(1000*ratio),axis=0)
            hit=hit*np.array([1,.35]if i%2==0 else[.35,1])
            put(fx,hit,beat+i/6,.06 if i==1 else .045)
    # A short pitch fall announces the broken beat without a new unrelated sound.
    stop=edge(peak(filt(take(3,3.8),350,'highpass')),.003,.040)
    speed=np.linspace(1,.18,round(.27*SR));pos=np.cumsum(speed);pos*=max(1,len(stop)-1)/pos[-1]
    fall=np.column_stack([np.interp(pos,np.arange(len(stop)),stop[:,i])for i in range(2)])
    put(fx,edge(fall,.003,.035),127.05,.045)
    # Echo the final voiced word, leaving the dry lyric centred and intelligible.
    for name,start in[('Alive',32),('Verse',128),('Someone',96),('Someone',176)]:
        x=phrases[name];energy=np.max(abs(x),axis=1);active=np.where(energy>.008)[0]
        end=active[-1]+1;tail=edge(filt(filt(x[max(0,end-round(.35*SR)):end],420,'highpass'),3700),.012,.04)
        for i,g in enumerate([.20,.11,.06]):
            at=start+(end-len(tail))/SR/BEAT+.75*(i+1)
            put(fx,tail*np.array([1,.3]if i%2==0 else[.3,1]),at,g)
    fx[round(63*BEAT*SR):round(63.45*BEAT*SR)]=0
    sf.write(OUT/'Ear candy - phrase turns 163.wav',edge(fx),SR,subtype='PCM_24')
    dump('v3-plan.json',dict(native_hook_db=native_db,vocal_source=src,vocal_events=[['Alive',9,16],['Someone',25,16],['Verse',33,32],['Someone',45,16]],
         hook_intent='Two-bar rhythmic question/answer, repeated identity and four-bar turnaround; gaps for the sung voice.',
         build_intent='Hint -> question -> sung reveal -> recognisable motif -> short rhythmic cadence -> breath.',
         drums_intent='Backbeat anchors retained; hats develop, bass leaves room for pickup kicks, fills punctuate four/eight bars.',
         lyric_verification='Local whisper.cpp transcription, sung-aligned.json. No massive/MC call samples used.'))
    midi.write(str(OUT/'V3 arrangement score.mid'),[(k,i,v)for i,(k,v)in enumerate(score.items())]+[('Meld hook',8,hooks)],BPM)
    print('Prepared V3; native hook fader',native_db,flush=True)


def apply():
    assert not(OUT/'v3-changes.json').exists(),'Inspect partial receipt.'
    assert(PROJECT/'Hard Bounce 163 - Hook and Sung Reggae V3.als').is_file()
    s=client.call('get_song');assert s['tempo']==BPM
    C('transport',action='stop')
    plan=json.loads((OUT/'v3-plan.json').read_text())
    # Previous ideas remain recoverable, muted, in the preceding saved version too.
    for tr in['HB 06 RAVE hook','HB 10 AIR transitions','HB 11 REGGAE voice','HB 12 DUB echo']:
        C('set_track',track=tr,mute=True)
    C('set_track',track='HB 14 HOOK',volume_db=plan['native_hook_db'],mute=False)
    C('delete_clips_in_range',track='HB 14 HOOK',start_bar=57,end_bar=66)
    hooks=json.loads((OUT/'hook-score.json').read_text())
    for a,b,label in[(17,25,'HOOK - question answer'),(29,33,'HOOK - reply to singer'),(41,45,'HOOK - bounce returns'),(49,57,'HOOK - final answer')]:
        nn=[[p,t-(a-1)*4,d,v]for p,t,d,v in hooks if(a-1)*4<=t<(b-1)*4]
        C('create_midi_clip',track='HB 14 HOOK',bar=a,length=(b-a)*4,notes=nn,loop=False,name=label)
    score=json.loads((OUT/'drum-score.json').read_text())
    for tr,nn in score.items():
        if tr=='HB 06 RAVE hook':continue
        data=client.call('get_track',dict(track=tr));cmds=[]
        # Clips already divide the current arrangement into the production chapters.
        for clip in data['clips']:
            notes=[[p,t-clip['start'],d,v]for p,t,d,v in nn if clip['start']<=t<clip['end']]
            cmds.append(dict(cmd='add_notes',args=dict(track=tr,clip=clip['i'],notes=notes,replace=True)))
        batch(cmds)
        for a,b in[(0,16),(16,48)]:
            early=[[p,t-a,d,v]for p,t,d,v in nn if a<=t<b]
            if early and not any(c['start']<b and c['end']>a for c in data['clips']):
                C('create_midi_clip',track=tr,beat=a,length=b-a,notes=early,loop=False,name='BUILD - rhythm stays connected')
    C('delete_clips_in_range',track='HB 09 BUILD sweep',start_bar=1,end_bar=18)
    C('create_audio_clip',track='HB 09 BUILD sweep',path=str(OUT/'Build - motif reveal 163.wav'),bar=1,warp=False,gain_db=0,name='BUILD - tease / reveal / answer / breath')
    C('create_track',kind='audio',name='HB 15 EAR CANDY')
    C('set_track',track='HB 15 EAR CANDY',volume_db=0,pan=0,monitoring='off',arm=False)
    C('create_audio_clip',track='HB 15 EAR CANDY',path=str(OUT/'Ear candy - phrase turns 163.wav'),bar=1,warp=False,name='Reverse motif / conga turns / pitch fall / vocal throws')
    C('create_track',kind='audio',name='HB 16 SUNG REGGAE')
    C('set_track',track='HB 16 SUNG REGGAE',volume_db=-3.5,pan=0,monitoring='off',arm=False)
    for name,bar,beats in plan['vocal_events']:
        C('create_audio_clip',track='HB 16 SUNG REGGAE',path=str(OUT/(name+' - 163 sung.wav')),bar=bar,warp=False,name='SUNG | '+name)
    for bar,label in[(1,'V3 BUILD - hook hint'),(5,'V3 BUILD - question'),(9,'V3 BUILD - sung reveal'),(13,'V3 BUILD - hook answers'),
                      (17,'V3 DROP - main hook'),(25,'V3 DROP - singer'),(29,'V3 DROP - synth reply'),(33,'V3 BREAK - sung reggae / broken beat'),
                      (41,'V3 RETURN - bounce hook'),(45,'V3 RETURN - sung answer'),(49,'V3 RETURN - final hook')]:
        C('set_cue',bar=bar,name=label)
    C('set_loop',on=False,start_bar=1,end_bar=57)
    C('transport',action='locate',bar=9)
    dump('applied-song.json',client.call('get_song'))


if __name__=='__main__':{'prepare':prepare,'apply':apply}[sys.argv[1]]()
