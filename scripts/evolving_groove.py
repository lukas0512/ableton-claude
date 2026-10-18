"""Apply a staged piano motif and leave negative space in the main drop."""
import json
from pathlib import Path
from ableton_claude import client

out = Path('/Users/lukasgalhardo/Music/Ableton/User Library/Samples/Codex/Evolving Groove')
out.mkdir(parents=True, exist_ok=True)
backup = {}
for track in ['Summer Piano', 'Theme', 'Pad']:
    info = client.call('get_track', {'track': track})
    backup[track] = {'info': info, 'notes': {
        str(c['i']): client.call('get_notes', {'track':track,'clip':c['i']})
        for c in info['clips']}}
assert not (out / 'before.json').exists(), 'Already applied; use the saved backup.'
(out / 'before.json').write_text(json.dumps(backup, indent=2))

def replace(track, clip, notes, name):
    client.call('add_notes', {'track':track,'clip':clip,'notes':notes,'replace':True})
    client.call('set_clip', {'track':track,'clip':clip,'name':name})
    print(track, clip, name, len(notes), flush=True)

# Same rhythmic seed across three levels of melodic disclosure. Native groove stays.
root = [[60,.5,.28,87],[60,2.5,.32,78],[60,6.5,.23,72],
        [68,8.5,.28,83],[68,10.5,.32,75]]
fragment = [[60,.5,.28,89],[63,1.75,.20,73],[67,2.5,.35,84],
            [60,6.5,.28,76],[68,8.5,.3,86],[67,10,.25,75],[63,10.75,.24,71]]
full = fragment + [[70,4.5,.28,78],[67,5.75,.2,69],
                   [72,12.5,.35,88],[70,13.75,.2,72],[68,14.5,.5,83]]
for i, notes, name in [(0,root,'Seed - roots'),(1,fragment,'Question - C Eb G'),
                        (2,root,'Drop - roots and space'),(3,fragment,'Answer - motif revealed'),
                        (4,full,'Full hook'),(5,full,'Full hook - octave answer')]:
    notes = [n[:] for n in notes]
    if i == 5:
        for n in notes:
            if n[1] >= 12: n[0] += 12; n[3] -= 7
    # Sparse chord support only at the fuller phrases, not continuous block chords.
    if i in (4,5):
        notes += [[63,.508,.26,63],[67,.516,.26,60],
                  [63,8.508,.28,62],[72,8.516,.28,59]]
    replace('Summer Piano',i,notes,name)
replace('Summer Piano',6,[[65,.5,.3,80],[65,2.5,.25,69],[68,8.5,.3,74],
                         [67,10.75,.2,66],[65,12.5,.6,77]],'Echo - F minor')

# Pluck introduces the root first; full call/response returns later in the drop.
replace('Theme',12,[[72,.5,.3,68],[72,3,.25,58]],'Drop - root hint')
replace('Theme',13,[[72,1.5,.28,62]],'Drop - space')
for i in (14,15):
    notes = [n for n in backup['Theme']['notes'][str(i)] if n[1]<3.5]
    replace('Theme',i,notes,'Theme - half phrase')

# First 16 bars dry; later pad appears as brief accents, not an uninterrupted bed.
notes = [n[:] for n in backup['Pad']['notes']['4']
         if any(abs(n[1]-p)<.01 for p in (63.5,87.5,95.5,119.5))]
for n in notes:
    n[1]=max(64,n[1]); n[2]=.65; n[3]=38
replace('Pad',4,notes,'Drop - air accents after 16 bars')
notes = [n[:] for n in backup['Pad']['notes']['3'] if n[1]<62]
for n in notes: n[2]=min(n[2],62-n[1])
replace('Pad',3,notes,'Break - release before impact')
print(client.call('record_master', {'start_bar':97,'end_bar':137,'name':'Evolving Groove Test'}),flush=True)
