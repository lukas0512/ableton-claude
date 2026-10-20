"""Raw vocal auditions in the actual bounce groove; no pitch/time processing."""
import sys,json,time,shutil
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp_server'))
from ableton_claude import client,server,loops,analysis
OUT=Path.home()/'Music/Ableton/User Library/Samples/Codex/HB163_V7_20261020'
PROJECT=Path.home()/'Music/Ableton Claude/Projects/Hard Bounce 155 - Tutty Sketch Project'
SR=44100;B=60/163;LOG=[]
def C(cmd,**args):
 r=server._journaled(cmd,args);LOG.append(dict(cmd=cmd,args=args,result=r));(OUT/'audition-changes.json').write_text(json.dumps(LOG,indent=2));print(cmd,str(r)[:140],flush=True);return r

def main():
 assert not(OUT/'audition-changes.json').exists(),'Inspect partial receipt before retry'
 rows=json.load(open(OUT/'candidates.json'));plans=[]
 for label,i in[('A',0),('B',2)]:
  row=rows[i];x=loops.read(row['path'],SR)
  x=signal.sosfilt(signal.butter(2,110,'highpass',fs=SR,output='sos'),x,axis=0)
  # Only remove leading/trailing quiet and fade edges. Preserve natural word rhythm.
  env=np.sqrt(signal.lfilter(np.ones(132)/132,1,np.mean(x*x,axis=1))+1e-12)
  active=np.where(env>max(env)*.022)[0];a=max(0,int(active[0])-round(.012*SR));z=min(len(x),int(active[-1])+round(.04*SR));x=x[a:z].copy()
  na=min(len(x),round(.003*SR));nb=min(len(x),round(.025*SR));x[:na]*=np.linspace(0,1,na)[:,None];x[-nb:]*=np.linspace(1,0,nb)[:,None]
  x*=10**(-15/20)/max(abs(x).max(),1e-12)
  n=round(8*B*SR);y=np.zeros((n,2));offset=round(.06*SR);size=min(len(x),n-offset);y[offset:offset+size]=x[:size]
  name='Test '+label+' - raw voice.wav';sf.write(OUT/name,y,SR,subtype='PCM_24')
  plans.append(dict(label=label,source=row,trim_seconds=[a/SR,z/SR],native_duration=len(x)/SR,onset_offset_seconds=.06,warp=False,pitch=0,file=name))
 (OUT/'audition-plan.json').write_text(json.dumps(plans,indent=2))
 C('transport',action='stop');C('set_track',track='HB 21 LATIN VOCAL',mute=True)
 for plan in plans:
  label=plan['label'];track='HB 22 VOCAL TEST A'if label=='A'else'HB 23 VOCAL TEST B'
  C('create_track',kind='audio',name=track);C('set_track',track=track,volume_db=0,mute=True,pan=0,arm=False,monitoring='off')
  for bar,gain in[(25,0),(27,-2.5)]:C('create_audio_clip',track=track,path=str(OUT/plan['file']),bar=bar,warp=False,gain_db=gain,name='AUDITION '+label+' - original timing and timbre')
 for plan in plans:
  label=plan['label'];track='HB 22 VOCAL TEST A'if label=='A'else'HB 23 VOCAL TEST B'
  C('set_track',track=track,mute=False)
  name='V7 Test '+label+' Print';C('record_master',start_bar=25,end_bar=33,name=name)
  for _ in range(20):
   time.sleep(1);s=client.call('record_status')
   if s['state']=='done':break
  assert s['state']=='done',s
  dest=PROJECT/'Renders'/('V7 - Teste '+label+' no groove.wav');shutil.copy2(s['file'],dest)
  C('delete_track',track=name);C('set_track',track=track,mute=True)
  a=analysis.analyze(str(dest));assert a['loudness']['true_peak_dbtp']<-.9
  (OUT/('test-'+label+'-analysis.json')).write_text(json.dumps(a,indent=2));print(label,a['loudness'],flush=True)
 C('transport',action='locate',bar=25)
 s=client.call('get_song');assert s['tracks'][0]['mute'] and not any(t['solo']for t in s['tracks'])
 assert all(t['mute']for t in s['tracks']if t['name']in['HB 21 LATIN VOCAL','HB 22 VOCAL TEST A','HB 23 VOCAL TEST B'])
 (OUT/'final-live.json').write_text(json.dumps(s,indent=2))
 d=PROJECT/'Production V7';d.mkdir(exist_ok=True)
 for f in['cleanup.json','audition-plan.json','audition-changes.json','final-live.json','test-A-analysis.json','test-B-analysis.json']:shutil.copy2(OUT/f,d/f)
 (d/'Notes.txt').write_text('''V7 — vocal reset and two short in-context auditions.

User rejected the Brazilian scat voice and chose the GADDAM reference direction. The rejected vocal is muted; its baked throws were removed while retaining Latin percussion. The previous clips were unwarped in Live, but their WAVs already contained the double Complex Pro processing (+5 semitones, then individual syllable warping). Switching the clip Warp button off could not undo those printed artifacts. All those files are excluded from playback now.

Two alternatives were prepared as brief auditions only: A = Move your body; B = Drop it low. Sources and exact trims in audition-plan.json. Neither is pitched, stretched, vocoded or syllable-warped. The file contains natural spoken timing with a small initial offset and empty space. Same drop bars 25–33, same voice peak level, two calls then marimba reply. Both audition tracks are muted in the saved set pending the user's voice choice; no new voice has been propagated through the arrangement.

Reference excerpt was separated and transcribed for analysis only; no reference audio is used as production material. Automatic transcription of its highly processed/background vocal was unreliable, so no semantic claim is made about its words.
''')
 print('Two raw in-context auditions ready; saved working state remains vocal-free.',flush=True)
if __name__=='__main__':main()
