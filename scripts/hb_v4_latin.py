"""V4 Latin bounce: native marimba, interlocking hand percussion and phrase turns."""
import json,sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client,server,loops
from ableton_claude.ear import midi
ROOT=Path(__file__).resolve().parents[1]
OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB163_V4_20261020'
V3=OUT.parent/'HB163_V3_20261020'
SR=44100;BEAT=60/163
LOG=[]
def C(cmd,**args):
 r=server._journaled(cmd,args);LOG.append(dict(cmd=cmd,args=args,result=r));(OUT/'changes.json').write_text(json.dumps(LOG,indent=2));print(cmd,str(r)[:140],flush=True);return r
def batch(cs):
 r=server.ableton_batch(cs);LOG.extend(dict(command=c,result=x)for c,x in zip(cs,r));(OUT/'changes.json').write_text(json.dumps(LOG,indent=2));assert all(x.get('ok')for x in r),r;print('batch OK',len(r),flush=True)
def edge(x,a=.002,b=.025):
 x=x.copy();na=min(len(x),round(a*SR));nb=min(len(x),round(b*SR));x[:na]*=np.linspace(0,1,na)[:,None];x[-nb:]*=np.linspace(1,0,nb)[:,None];return x
def filt(x,hz,kind='lowpass'):return signal.sosfilt(signal.butter(2,hz,kind,fs=SR,output='sos'),x,axis=0)
def norm(x):return x/max(float(abs(x).max()),1e-9)
def put(y,x,t,g=1):
 a=round(t*BEAT*SR);n=min(len(x),len(y)-a)
 if a>=0 and n>0:y[a:a+n]+=x[:n]*g

def prepare():
 index=json.loads((ROOT/'knowledge/samples_index.json').read_text())['items'];sources={}
 for name,base,hp,sec in [('Conga','17-hit congas 1.wav',180,.26),('Bongo','17-hit bongo 1.wav',260,.15),('Guiro','EG101_Guiro_001_SP.wav',900,.20),('Clave','adt_percussion_clave.wav',650,.11)]:
  p=next(x['path']for x in index if Path(x['path']).name==base);sources[name]=p
  x=loops.read(p,SR)[:round(sec*SR)];x=edge(filt(filt(x,hp,'highpass'),7000));x=norm(x)*.86
  sf.write(OUT/(name+' tight.wav'),x,SR,subtype='PCM_24')
 (OUT/'sample-sources.json').write_text(json.dumps(sources,indent=2))
 cell=json.loads((OUT/'hook-cell.json').read_text());score={'HB 17 MARIMBA':[],'HB 18 CONGAS':[],'HB 19 BONGO':[],'HB 08 PERC reply':[],'HB 07 SNARE build':[],'HB 04 HAT tight':[]}
 for start,bars in[(16,8),(28,4),(40,4),(48,8)]:
  for p,t,d,v in cell:
   if t>=bars*4:continue
   at=start*4+t
   if int(at//4)in[23,31,55]and at%4>=3:continue
   score['HB 17 MARIMBA'].append([p,at,d,v])
 # Tease the actual drop identity rather than running a separate pitched riser.
 for t in[0,8]:
  score['HB 17 MARIMBA'] += [[65,t,.18,77],[65,t+.75,.14,64]]
 for p,t,d,v in cell:
  if t<16:score['HB 17 MARIMBA'].append([p,16+t,d,v-17])
  if t<12:score['HB 17 MARIMBA'].append([p,48+t,d,v-7])
 score['HB 17 MARIMBA'] += [[65,60,.16,102],[65,60.75,.16,112],[72,61.5,.14,108],[68,62.25,.14,96]]
 # Contrasting open hand-drum tones, low ghost taps and spaced bongo answers.
 for bar in range(4,56):
  b=bar*4;isbreak=32<=bar<40;build=bar<16
  strength=.75 if build else (.86 if isbreak else 1)
  conga=[(60,.75,100),(63,1.5,86),(60,3.5,108)] if bar%2==0 else [(63,.25,74),(60,1.75,101),(63,2.5,83),(60,3.25,102)]
  if bar in[7,15,23,31,39,47,55]:conga=[(60,.75,103),(63,1.5,86)]
  if 8<=bar<12:conga=conga[:1]
  for p,t,v in conga:score['HB 18 CONGAS'].append([p,b+t+.009,.10,round(v*strength)])
  if bar%2 and not 8<=bar<12:
   for p,t,v in[(60,2.75,98),(64,3,74),(60,3.75,88)]:
    if bar in[15,23,31,39,47,55]and t>=3:continue
    score['HB 19 BONGO'].append([p,b+t+.014,.075,round(v*strength)])
  # Son-clave accents through the existing dry rim, a two-bar call/answer.
  for t,v in ([(0,77),(1.5,100),(3,87)]if bar%2==0 else[(1,91),(2,102)]):
   if bar==15 and t>=3:continue
   score['HB 08 PERC reply'].append([60,b+t,.07,round(v*strength)])
  # Hats use eighths with small pickups, leaving room for hand percussion.
  for st in range(8):
   if build and st%2==0:continue
   if isbreak and st in[0,4]:continue
   if bar in[15,23,31,39,47,55]and st>=6:continue
   score['HB 04 HAT tight'].append([60,b+st/2,.065,[73,98,69,88][st%4]-(10 if build else 0)])
  if bar%4==2 and not build:score['HB 04 HAT tight'].append([60,b+3.75,.05,58])
 for bar in range(4):
  for t in[.5,2.5]:score['HB 04 HAT tight'].append([60,bar*4+t,.07,69])
 old=json.loads((V3/'drum-score.json').read_text())
 score['HB 07 SNARE build']=[n for n in old['HB 07 SNARE build']if 128<=n[1]<160]
 score['HB 07 SNARE build'] += [[60,60,.10,80],[60,61.5,.09,93],[60,62.5,.08,101]]
 fx=np.zeros((round(224*BEAT*SR),2),np.float32)
 guiro=loops.read(str(OUT/'Guiro tight.wav'),SR);clave=loops.read(str(OUT/'Clave tight.wav'),SR)
 conga=loops.read(str(OUT/'Conga tight.wav'),SR);bongo=loops.read(str(OUT/'Bongo tight.wav'),SR)
 dry=loops.read(str(OUT/'Marimba dry.wav'),SR)*10**(5/20)
 hit=edge(dry[:round(.58*BEAT*SR)],.002,.018)
 for bar in range(4,56):
  if 8<=bar<12:continue
  for at,g in[(.5,.023),(2.5,.032)]:put(fx,guiro*np.array([.55,1]),bar*4+at,g)
 # Three distinct turnaround gestures: paired hits, short cascades, one reverse pickup.
 for end in[32,64,96,128,160,192,224]:
  if end in[64,160]:
   for t,g in[(end-2,.12),(end-1.25,.095),(end-.5,.14)]:put(fx,conga*np.array([1,.65]),t,g)
   for t,g in[(end-1,.075),(end-.75,.055),(end-.25,.09)]:put(fx,bongo*np.array([.55,1]),t,g)
  else:
   for j,(off,g)in enumerate([(1.25,.11),(.75,.08),(.5,.12)]):
    x=conga if j%2==0 else bongo;put(fx,x*np.array([1,.45]if j%2==0 else[.45,1]),end-off,g)
 for end in[64,160]:
  rev=edge(norm(filt(hit[::-1],750,'highpass')),.025,.003)
  put(fx,rev,end-len(rev)/SR/BEAT-.03,.025)
 # Sung tails retained as restrained dotted-eighth answers, no rave pitch fall.
 for name,start in[('Alive',32),('Verse',128),('Someone',96),('Someone',176)]:
  x=loops.read(str(V3/(name+' - 163 sung.wav')),SR);a=np.where(np.max(abs(x),axis=1)>.008)[0];end=a[-1]+1
  tail=edge(filt(filt(x[max(0,end-round(.30*SR)):end],480,'highpass'),3400),.012,.04)
  for i,g in enumerate([.14,.065]):put(fx,tail*np.array([1,.35]if i==0 else[.35,1]),start+(end-len(tail))/SR/BEAT+.75*(i+1),g)
 # A clear breath at the end of the build and before the return.
 fx[round(63*BEAT*SR):round(63.45*BEAT*SR)]=0
 sf.write(OUT/'Latin phrase turns 163.wav',edge(fx),SR,subtype='PCM_24')
 for k in score:score[k].sort(key=lambda n:(n[1],n[0]))
 (OUT/'score.json').write_text(json.dumps(score,indent=2));midi.write(str(OUT/'Latin Bounce V4 score.mid'),[(k,i,v)for i,(k,v)in enumerate(score.items())],163)
 print('PREPARED', {k:len(v)for k,v in score.items()},flush=True)

def apply():
 assert not(OUT/'changes.json').exists(),'Inspect partial changes before resuming'
 score=json.loads((OUT/'score.json').read_text());C('transport',action='stop')
 for tr in['HB 14 HOOK','HB 09 BUILD sweep','HB 15 EAR CANDY']:C('set_track',track=tr,mute=True)
 for name,sample,db,pan in [('HB 18 CONGAS','Conga',-1,-.18),('HB 19 BONGO','Bongo',-4,.24)]:
  C('create_track',kind='midi',name=name);C('load_device',track=name,path='user_library/Samples/Codex/HB163_V4_20261020/'+sample+' tight.wav')
  C('set_device_prop',track=name,device=0,prop='playback_mode',value=1)
  C('set_param',track=name,device=0,param='Volume',value=-18)
  C('set_track',track=name,volume_db=db,pan=pan,monitoring='off',arm=False)
 C('set_track',track='HB 17 MARIMBA',volume_db=-7,solo=False,mute=False)
 C('set_track',track='HB 08 PERC reply',volume_db=-11)
 for tr,notes in score.items():
  C('delete_clips_in_range',track=tr,start_bar=1,end_bar=58)
  ranges=[(1,9),(9,13),(13,17),(17,25),(25,33),(33,41),(41,49),(49,57)]
  cmds=[]
  for a,b in ranges:
   nn=[[p,t-(a-1)*4,d,v]for p,t,d,v in notes if(a-1)*4<=t<(b-1)*4]
   if nn:cmds.append(dict(cmd='create_midi_clip',args=dict(track=tr,bar=a,length=(b-a)*4,notes=nn,loop=False,name=('LATIN - '+tr.split(' ',2)[-1]+' / '+str(a)))))
  batch(cmds)
 C('create_track',kind='audio',name='HB 20 LATIN TURNS')
 C('set_track',track='HB 20 LATIN TURNS',volume_db=0,pan=0,monitoring='off',arm=False)
 C('create_audio_clip',track='HB 20 LATIN TURNS',path=str(OUT/'Latin phrase turns 163.wav'),bar=1,warp=False,name='Guiro / conga turns / bongo replies / sung tails')
 for bar,label in[(1,'V4 LATIN - motivo'),(5,'V4 LATIN - perc call'),(9,'V4 LATIN - sung reggae'),(13,'V4 LATIN - tension'),(17,'V4 LATIN - drop'),(25,'V4 LATIN - sung answer'),(29,'V4 LATIN - marimba answer'),(33,'V4 LATIN - sung breakbeat'),(41,'V4 LATIN - bounce returns'),(45,'V4 LATIN - sung answer'),(49,'V4 LATIN - final hook')]:C('set_cue',bar=bar,name=label)
 C('set_loop',on=False,start_bar=1,end_bar=57)
 C('transport',action='locate',bar=13)
 (OUT/'applied.json').write_text(json.dumps(client.call('get_song'),indent=2))
if __name__=='__main__':{'prepare':prepare,'apply':apply}[sys.argv[1]]()
