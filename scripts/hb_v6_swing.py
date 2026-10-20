"""V6: measured syllable timing, swung eighths and clean vocal phrase boundaries."""
import json,sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client,server,loops
OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB163_V6_20261020';V5=OUT.parent/'HB163_V5_20261020'
SR=44100;BEAT=60/163;LOG=[]
def edge(x,a=.003,b=.025):
 x=x.copy();na=min(len(x),round(a*SR));nb=min(len(x),round(b*SR));x[:na]*=np.linspace(0,1,na)[:,None];x[-nb:]*=np.linspace(1,0,nb)[:,None];return x
def filt(x,hz,kind='lowpass'):return signal.sosfilt(signal.butter(2,hz,kind,fs=SR,output='sos'),x,axis=0)
def put(y,x,t,g=1):
 a=round(t*BEAT*SR);n=min(len(x),len(y)-a)
 if a>=0 and n>0:y[a:a+n]+=x[:n]*g

def prepare():
 x=loops.read(str(OUT/'Vocal swing 58 - rendered.wav'),SR)
 def phrase(a,b,beats,name):
  y=edge(x[round(a*BEAT*SR):round(b*BEAT*SR)],.003,.025);n=round(beats*BEAT*SR);y=np.pad(y,((0,max(0,n-len(y))),(0,0)))[:n]
  sf.write(OUT/name,y,SR,subtype='PCM_24');return y
 call=phrase(0,6.2,8,'Tiri Da - swung call 2 bars.wav')
 phrase(0,12.2,16,'Tiri Da - swung break 4 bars.wav')
 phrase(9,12.2,4,'Da - swung answer 1 bar.wav')
 fx=loops.read(str(V5/'Latin turns - new vocal only.wav'),SR)
 old=loops.read(str(V5/'Tiri Da - 163 F minor processed.wav'),SR)
 tail=edge(filt(filt(old[round(7.15*BEAT*SR):round(7.95*BEAT*SR)],500,'highpass'),3400),.008,.035)
 for start in[32,96,144,176,208]:
  for i,g in enumerate([.16,.075]):put(fx,tail*np.array([1,.4]if i==0 else[.4,1]),start+8.05+i*.75,-g)
 # Echo follows the new da attack. Dotted eighth at half-time = 1.5 Live beats.
 tail=edge(filt(filt(x[round(5.52*BEAT*SR):round(6.2*BEAT*SR)],500,'highpass'),3400),.008,.028)
 for start in[32,96,144,176,208]:
  for i,g in enumerate([.14,.06]):put(fx,tail*np.array([1,.4]if i==0 else[.4,1]),start+7.02+i*1.5,g)
 sf.write(OUT/'Latin turns - swung vocal replies.wav',fx,SR,subtype='PCM_24')
 sf.write(OUT/'call verification 16k.wav',loops.read(str(OUT/'Tiri Da - swung call 2 bars.wav'),16000).mean(axis=1),16000)
 print('Prepared clean calls, sung break, swung responses and matching throws',flush=True)

def C(cmd,**args):
 r=server._journaled(cmd,args);LOG.append(dict(cmd=cmd,args=args,result=r));(OUT/'changes.json').write_text(json.dumps(LOG,indent=2));print(cmd,str(r)[:160],flush=True);return r

def apply():
 assert not(OUT/'changes.json').exists(),'Inspect partial receipt before resuming'
 C('transport',action='stop');C('delete_clips_in_range',track='HB 21 LATIN VOCAL',start_bar=1,end_bar=58)
 C('set_track',track='HB 21 LATIN VOCAL',solo=False,mute=False,volume_db=1.5,pan=0,monitoring='off',arm=False)
 files={'call':'Tiri Da - swung call 2 bars.wav','phrase':'Tiri Da - swung break 4 bars.wav','answer':'Da - swung answer 1 bar.wav'}
 plan=json.load(open(V5/'plan.json'))
 for name,bar,length in plan['events']:C('create_audio_clip',track='HB 21 LATIN VOCAL',path=str(OUT/files[name]),bar=bar,warp=False,name='SWUNG | '+name+' - 58%')
 C('delete_clips_in_range',track='HB 20 LATIN TURNS',start_bar=1,end_bar=58)
 C('create_audio_clip',track='HB 20 LATIN TURNS',path=str(OUT/'Latin turns - swung vocal replies.wav'),bar=1,warp=False,name='Latin percussion / swung sung answers')
 C('set_cue',bar=25,name='V6 VOCAL SWING - bounce pocket');C('set_cue',bar=33,name='V6 VOCAL SWING - broken beat')
 C('set_loop',on=False,start_bar=1,end_bar=57);C('transport',action='locate',bar=25)
 (OUT/'applied.json').write_text(json.dumps(client.call('get_song'),indent=2))
if __name__=='__main__':{'prepare':prepare,'apply':apply}[sys.argv[1]]()
