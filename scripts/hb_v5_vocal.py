"""V5: verified Brazilian sung percussion replaces the rejected romantic vocal."""
import json,sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client,server,loops
OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB163_V5_20261020'
V3=OUT.parent/'HB163_V3_20261020';V4=OUT.parent/'HB163_V4_20261020'
SR=44100;BEAT=60/163;LOG=[]
def C(cmd,**args):
 r=server._journaled(cmd,args);LOG.append(dict(cmd=cmd,args=args,result=r));(OUT/'changes.json').write_text(json.dumps(LOG,indent=2));print(cmd,str(r)[:170],flush=True);return r
def edge(x,a=.003,b=.025):
 x=x.copy();na=min(len(x),round(a*SR));nb=min(len(x),round(b*SR));x[:na]*=np.linspace(0,1,na)[:,None];x[-nb:]*=np.linspace(1,0,nb)[:,None];return x
def filt(x,hz,kind='lowpass'):return signal.sosfilt(signal.butter(2,hz,kind,fs=SR,output='sos'),x,axis=0)
def put(y,x,t,g=1):
 a=round(t*BEAT*SR);n=min(len(x),len(y)-a)
 if a>=0 and n>0:y[a:a+n]+=x[:n]*g

def prepare():
 x=loops.read(str(OUT/'Tiri Da - 163 F minor processed.wav'),SR)
 def phrase(a,b,length,name):
  y=edge(x[round(a*BEAT*SR):round(b*BEAT*SR)],.003,.04);n=round(length*BEAT*SR);y=np.pad(y,((0,max(0,n-len(y))),(0,0)))[:n]
  sf.write(OUT/name,y,SR,subtype='PCM_24');return y
 call=phrase(0,8,8,'Tiri Da - call 2 bars.wav')
 full=phrase(0,13.4,16,'Tiri Da - phrase 4 bars.wav')
 # Last voiced syllable with tail, useful as a sparse response instead of another verse.
 answer=phrase(11.3,13.4,4,'Tiri Da - answer 1 bar.wav')
 # Remove every old sung-word throw while preserving V4's percussion gestures.
 fx=loops.read(str(V4/'Latin phrase turns 163.wav'),SR)
 for name,start in[('Alive',32),('Verse',128),('Someone',96),('Someone',176)]:
  old=loops.read(str(V3/(name+' - 163 sung.wav')),SR);active=np.where(np.max(abs(old),axis=1)>.008)[0];end=active[-1]+1
  tail=edge(filt(filt(old[max(0,end-round(.30*SR)):end],480,'highpass'),3400),.012,.04)
  for i,g in enumerate([.14,.065]):put(fx,tail*np.array([1,.35]if i==0 else[.35,1]),start+(end-len(tail))/SR/BEAT+.75*(i+1),-g)
 # New throw is a very short, intelligible sung da with the dry voice centred.
 tail=edge(filt(filt(x[round(7.15*BEAT*SR):round(7.95*BEAT*SR)],500,'highpass'),3400),.008,.035)
 for start in[32,96,144,176,208]:
  for i,g in enumerate([.16,.075]):put(fx,tail*np.array([1,.4]if i==0 else[.4,1]),start+8.05+i*.75,g)
 sf.write(OUT/'Latin turns - new vocal only.wav',fx,SR,subtype='PCM_24')
 events=[('call',9,8),('call',25,8),('answer',28,4),('phrase',33,16),('call',37,8),('call',45,8),('answer',48,4),('call',53,8)]
 (OUT/'plan.json').write_text(json.dumps(dict(source=json.load(open(OUT/'candidates.json'))[3],source_tempo=90,target_half_time=81.5,pitch_semitones=5,warp='Live Complex Pro, formants preserved',events=events,content='Verified source and processed singing: tiri da / que tem que dar; Portuguese rhythmic sung phrase, no old English lyrics'),indent=2))
 print('Prepared new phrases and removed old sung tails',flush=True)

def apply():
 assert not(OUT/'changes.json').exists(),'Inspect partial receipt before resuming'
 C('transport',action='stop');C('set_track',track='HB 16 SUNG REGGAE',mute=True)
 C('set_track',track='HB 21 LATIN VOCAL',volume_db=1.5,pan=0,solo=False,mute=False,monitoring='off',arm=False)
 files={'call':'Tiri Da - call 2 bars.wav','phrase':'Tiri Da - phrase 4 bars.wav','answer':'Tiri Da - answer 1 bar.wav'}
 plan=json.loads((OUT/'plan.json').read_text())
 for name,bar,length in plan['events']:C('create_audio_clip',track='HB 21 LATIN VOCAL',path=str(OUT/files[name]),bar=bar,warp=False,name='BR sung | '+name)
 C('delete_clips_in_range',track='HB 20 LATIN TURNS',start_bar=1,end_bar=58)
 C('create_audio_clip',track='HB 20 LATIN TURNS',path=str(OUT/'Latin turns - new vocal only.wav'),bar=1,warp=False,name='Latin percussion / new sung throws')
 # Final phrase alternates the two leads rather than stacking them.
 tr=client.call('get_track',dict(track='HB 17 MARIMBA'));last=next(c for c in tr['clips']if c['start']==192)
 notes=client.call('get_notes',dict(track='HB 17 MARIMBA',clip=last['i']))
 notes=[n for n in notes if not 16<=n[1]<24]
 C('add_notes',track='HB 17 MARIMBA',clip=last['i'],notes=notes,replace=True)
 for bar,label in[(9,'V5 BR VOCAL - short call'),(25,'V5 BR VOCAL - drop answer'),(33,'V5 BR VOCAL - breakbeat'),(37,'V5 BR VOCAL - reply'),(45,'V5 BR VOCAL - sung return'),(53,'V5 BR VOCAL - final call')]:C('set_cue',bar=bar,name=label)
 C('set_loop',on=False,start_bar=1,end_bar=57);C('transport',action='locate',bar=9)
 (OUT/'applied.json').write_text(json.dumps(client.call('get_song'),indent=2))
if __name__=='__main__':{'prepare':prepare,'apply':apply}[sys.argv[1]]()
