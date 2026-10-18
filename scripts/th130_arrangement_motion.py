"""Develop the existing 128-bar TH130 set through entrances, exits and returns.

Archive the four changed roles muted, retain bass/melody/string identity, and
place the developed material in labelled eight-bar Arrangement clips.
"""
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client, loops, server

SR, BPM, BEAT = 44100, 130, 60/130
OUT = Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 Arrangement Motion 2026-10-16'
ROLES = {'Kick':'TH130 V2 Kick','Tops':'TH130 House Fit Groove Tops',
         'Vocal':'TH130 V2 Vocal','Keys':'TH130 House Fit Keys'}
CHAPTERS = {
    1:'DJ intro - reveal pulse',9:'Bass first - voice at the turn',
    17:'Pocket established - answer returns',25:'Hook A - introduce conversation',
    33:'Hook B - clear space then anticipate',41:'Break - voice hands over to melody',
    49:'Build I - question and withholding',57:'Drop I - sub and drums lead',
    65:'Drop I - signature revealed',73:'Drop I - recall then release',
    81:'Air - thread and gradual return',89:'Build II - vocal fragment pickup',
    97:'Drop II - open percussion from arrival',105:'Drop II - theme and turnaround',
    113:'Final reply - resolve the story',121:'DJ outro - progressive handover',
}
LOG, ASSETS = [], []


def sample(beat):return round(beat*BEAT*SR)


def C(cmd, **args):
    r=server._journaled(cmd,args)
    LOG.append(dict(cmd=cmd,args=args,result=r))
    (OUT/'live-changes.json').write_text(json.dumps(LOG,ensure_ascii=False,indent=2))
    return r


def edges(x, a=.005, b=.025):
    x=x.copy();na=min(len(x),round(a*SR));nb=min(len(x),round(b*SR))
    if na:x[:na]*=np.linspace(0,1,na)[:,None]
    if nb:x[-nb:]*=np.linspace(1,0,nb)[:,None]
    return x


def silence(x, a, b, fade=.020):
    i,j=sample(a),min(len(x),sample(b));f=round(fade*SR)
    if i>=j:return
    k=min(f,i)
    if k:x[i-k:i]*=np.linspace(1,0,k)[:,None]
    x[i:j]=0
    k=min(f,len(x)-j)
    if k:x[j:j+k]*=np.linspace(0,1,k)[:,None]


def put(x, audio, beat, gain=1.):
    i=sample(beat);n=min(len(audio),len(x)-i)
    if n>0:x[i:i+n]+=audio[:n]*gain


def filt(x,hz,kind='lowpass'):
    return signal.sosfilt(signal.butter(2,hz,kind,fs=SR,output='sos'),x,axis=0).astype(np.float32)


def main():
    song=client.call('get_song')
    assert song['tempo']==BPM and not any(t['name'].startswith('TH130 ARR ') for t in song['tracks'])
    OUT.mkdir(parents=True,exist_ok=True)
    extra=['TH130 Signature Call','TH130 String Tension','TH130 V2 Build']
    state={t:client.call('get_track',dict(track=t,clips=True)) for t in list(ROLES.values())+extra}
    assert all(not state[t]['mute'] for t in ROLES.values())
    (OUT/'before.json').write_text(json.dumps(dict(song=song,tracks=state),ensure_ascii=False,indent=2))
    n=sample(512)
    audio={}
    for role,name in ROLES.items():
        y=np.zeros((n,2),np.float32)
        for c in state[name]['clips']:
            if c['muted']:continue
            assert not c['warping'] and c['pitch']==0 and c['detune']==0
            x=loops.read(c['file']).astype(np.float32)
            x=x[:sample(c['length'])]
            put(y,x,c['start'],10**(c['gain_db']/20))
        audio[role]=y
    kick,tops,voice,keys=(audio[r] for r in ROLES)

    # Establish the foundation, then use the voice as an eight-bar turnaround.
    short=voice[sample(32):sample(40)].copy()
    silence(voice,32,96)
    for bar in (15,23):put(voice,edges(short,.004,.04),(bar-1)*4)
    # Vocal absence has a purpose: hand the listener to the keys/melodic answer.
    for first,last in [(33,37),(45,49),(51,53),(69,73),(91,93),(109,113)]:
        silence(voice,(first-1)*4,(last-1)*4)
    # Recall the short call before leaving the first drop and late in the final one.
    recall=voice[sample((61-1)*4):sample((63-1)*4)].copy()
    for bar in (79,117):put(voice,edges(recall,.004,.05),(bar-1)*4,.86)

    # The final build has its own pickup, cut from the existing user's dry voice.
    index=json.loads((Path(__file__).resolve().parents[1]/'knowledge/samples_index.json').read_text())['items']
    name='Odd Frequency - Grid Vol 2 - Vocal Phrase Dry 4 - 130 BPM.wav'
    path=next(r['path'] for r in index if os.path.basename(r['path'])==name and os.path.isfile(r['path']))
    dry=filt(filt(loops.read(path).astype(np.float32),160,'highpass'),5400)
    first=dry[:round(1.35*SR)]
    env=ndimage.uniform_filter1d(abs(first).mean(axis=1),size=round(.010*SR))
    active=np.flatnonzero(env>env.max()*.22)
    assert len(active)>0
    end=min(len(first),int(active[-1])+round(.015*SR));begin=max(0,end-round(.25*SR))
    word=edges(first[begin:end],.006,.025)
    word*=.19/max(float(abs(word).max()),1e-9)
    silence(voice,(95-1)*4,(97-1)*4)
    for bar,beat,gain in [(95,2.5,.85),(96,1.5,.8),(96,2.25,1.),(112,1.5,.8)]:
        put(voice,word,(bar-1)*4+beat,gain)

    # A few prepared exits, never a fresh bassline for each chapter.
    exits=[(24,3),(32,3),(40,2),(64,3),(72,3),(80,2),(104,3),(112,2),(120,3),(128,3)]
    for bar,beat in exits:silence(kick,(bar-1)*4+beat,bar*4,.008)

    # First drop reveals the harmonic hook after the sub/drum arrival.
    accent=keys[sample(224):sample(224+.8)].copy()
    silence(keys,224,240)
    put(keys,accent,224)
    # The final drop starts with the established open percussion, instead of
    # copying the sparse first-drop entrance. Its later turnaround is distinctive.
    open_tops=tops[sample(400):sample(416)].copy() # bars 101-104
    tops[sample(384):sample(400)]=open_tops[:sample(400)-sample(384)]
    tops[sample(336):sample(352)]*=10**(1.2/20) # last half of air points forward
    for bar in (40,80):
        a,b=sample((bar-2)*4),sample(bar*4)
        original=tops[a:b].copy();dark=filt(original,2800)
        ramp=np.linspace(0,.75,len(original),dtype=np.float32)[:,None]
        tops[a:b]=original*(1-ramp)+dark*ramp
        silence(tops,(bar-1)*4+3,bar*4)
    silence(tops,(112-1)*4+2,112*4)
    # One familiar chord answers the empty phrase before the last return.
    chord=edges(keys[sample(384):sample(384+.72)],.006,.035)
    put(keys,chord,(111-1)*4+1.5,.85)
    keys[sample(448):sample(480)]*=10**(.6/20) # last eight bars of the final drop
    tops[sample(496):sample(512)]*=np.linspace(1,10**(-3/20),sample(512)-sample(496))[:,None]

    # Preserve the one-beat space before each main drop, including new throws.
    for bar in (56,96):
        for x in (tops,voice,keys):silence(x,(bar-1)*4+3,bar*4)

    # Labelled eight-bar clips expose the musical chapters directly in Live.
    for role,x in audio.items():
        assert np.isfinite(x).all() and abs(x).max()<.85
        for bar,label in CHAPTERS.items():
            a,b=sample((bar-1)*4),sample((bar+7)*4)
            chunk=edges(x[a:b],.001,.002)
            if abs(chunk).max()<1e-7:continue
            p=OUT/f'{bar:03d}_{role}.wav';sf.write(p,chunk,SR,subtype='PCM_24')
            ASSETS.append(dict(role=role,path=str(p),bar=bar,end_bar=bar+8,label=label))
    plan=dict(bpm=BPM,bars=128,chapters=CHAPTERS,kick_exits=exits,
              vocal_fragment=dict(source=path,start_s=begin/SR,end_s=end/SR),assets=ASSETS)
    (OUT/'arrangement.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
    print('PREPARED',len(ASSETS),'clips; voice fragment',begin/SR,end/SR,flush=True)
    C('transport',action='stop');C('set_loop',on=False)
    for role,old in ROLES.items():
        t='TH130 ARR '+role;original=state[old]
        C('create_track',kind='audio',name=t)
        C('set_track',track=t,volume_db=original['vol_db'],pan=original['pan'],arm=False,monitoring='off')
        for send,db in enumerate(original['sends_db']):
            if math.isfinite(db):C('set_send',track=t,send=send,db=db)
        for asset in ASSETS:
            if asset['role']==role:C('create_audio_clip',track=t,path=asset['path'],bar=asset['bar'],
                warp=False,gain_db=0,name=role+' | '+asset['label'])
        C('set_track',track=old,mute=True)
        print('LIVE',t,flush=True)
    # The second build is a vocal-led anticipation with a softer bed under it.
    C('set_clip',track='TH130 V2 Build',clip={'at':352},gain_db=-7.5)
    for bar,label in [(17,'ARR pocket - voice at next turn'),(33,'ARR clear space then anticipate'),
                      (65,'ARR signature enters'),(73,'ARR hook recalls'),
                      (105,'ARR final theme and turnaround'),(113,'ARR last return'),
                      (125,'ARR DJ handover')]:C('set_cue',bar=bar,name=label)
    (OUT/'after.json').write_text(json.dumps(client.call('get_song'),ensure_ascii=False,indent=2))
    (OUT/'Production notes.md').write_text('130 BPM, B minor, 128 musical bars plus two bars of tail.\n\n'
        '9–24: bass gets the foreground; voice moves to the ends of the eight-bar phrases.\n'
        '25–40: hook is answered, then a phrase clears before voice/string anticipation. '
        'Kick leaves two beats before the break.\n'
        '41–56: vocal hands over to melody in the second half of the break; the build gives '
        'the melodic call space and keeps its last beat empty.\n'
        '57–80: first four bars expose kick/sub/vocal, keys then re-enter; a pure-groove phrase '
        'and short kick exit prepare the hook recall. Short voice returns before the air.\n'
        '81–96: percussion returns gradually; the second build uses a fragment of the same '
        'dry voice as its pickup, then leaves the last beat free.\n'
        '97–120: open percussion from arrival; a two-beat turnaround and one tonic chord '
        'prepare the final return, with a late vocal recall.\n'
        '121–128: melody/voice leave, bass hands over after four bars, tops recede.\n\n'
        'Four earlier role tracks retained muted. Sub pattern, call notes, chord harmony, '
        'tempo, sends and master remain the established basis. All material is from the '
        'existing session/user packs. New eight-bar clips and locators expose the form.\n')
    print('READY',OUT,flush=True)


if __name__=='__main__':main()
