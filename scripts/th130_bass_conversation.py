"""Four-bar bass conversation, preserving the approved drums and transition arcs.

Uses the producer's GRID sample for a moving upper body over the existing held
sub voice. Only 02 Sub Bass is replaced through ClaudeBridge. No master capture.
"""
import json
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server
from ableton_claude.ear import midi
import th130_house_fit as hf
import th130_string_signature as ss
import th130_pulse_story as story
from th130_flow_continuity import ramp
from th130_arrangement_motion import put, sample, silence
from th130_remix_conversation import assemble

SR, BPM, BEAT = 44100, 130, 60/130
OUT = Path.home()/'Music/Ableton/User Library/Samples/Codex/TH130 Bass Conversation 2026-10-17'
ROLE = '02 Sub Bass'


def dump(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2))


def rms(x):
    return float(np.sqrt(np.mean(x.astype(float)**2)))


def db(x):
    return float(20*np.log10(max(rms(x), 1e-12)))


def voice():
    held = story.bass_voice()
    raw = ss.read('Odd Frequency - Grid Vol 2 - Bass Shot 2 - B.wav')
    raw = np.repeat(raw.mean(axis=1, keepdims=True), 2, axis=1)
    source = json.loads((OUT/'source-check.json').read_text())['source_midi']
    cache = {}

    def note(pitch, duration, accent):
        key = pitch, duration, accent
        if key not in cache:
            base = held(pitch, duration)
            ratio = 2**((pitch-source)/12)
            take = signal.resample_poly(raw, 10000, round(10000*ratio), axis=0).astype(np.float32)
            take = take[:len(base)]
            take = np.pad(take, ((0, len(base)-len(take)), (0, 0)))
            take = hf.edge(hf.filt(hf.filt(take, 145, 'highpass'), 1700), .008, .045)
            upper = hf.filt(hf.filt(base, 145, 'highpass'), 1700)
            # Replace a small portion of the static upper band, rather than
            # add low-end energy. Cap matching when a short sample decays away.
            take *= min(2.5, rms(upper)/max(rms(take), 1e-9))
            blend = .32 if accent else .20
            result = base + blend*(take-upper)
            result *= rms(base)/max(rms(result), 1e-9)
            cache[key] = hf.edge(result, .004, .018)
        return cache[key]
    return note


def cell(bar):
    position = (bar-9) % 4
    if position == 0:
        return [(23,.5,1.05,108), (23,2.787,.18,76), (30,3.5,.23,82)]
    if position == 1:
        return [(23,.287,.82,106), (23,1.787,.16,70),
                (23,2.5,1.02,100), (23,3.787,.30,82)]
    if position == 2:
        return [(23,.787,.86,104), (23,2.5,.22,82), (23,3.287,.36,92)]
    result = [(23,.5,1.40,108), (30,2.787,.18,74),
              (33 if bar % 8 == 0 else 23,3.5,.18,75), (23,3.787,.40,97)]
    # A recognisable ending returns; a small rising turn appears only three
    # times across the track. The root remains the long-duration foundation.
    if bar in (24,72,120):
        result.insert(1, (28,2.287,.14,70))
    elif bar % 16 == 0:
        result = [n for n in result if n[1] != 3.5]
        result[-1] = (23,3.787,.50,97)
    if bar == 124:
        result[-1] = (23,3.787,.21,82)
    return result


def prepare():
    assert not (OUT/'live-changes.json').exists(), 'Never overwrite staged media.'
    state = json.loads((OUT/'before.json').read_text())
    n = sample(512); old = assemble(state['tracks'][ROLE], n)
    kick = assemble(state['tracks']['01 Kick'], n)
    y = np.zeros_like(old); render = voice(); events = []; notes = []
    for bar in range(9,125):
        for pitch, at, duration, velocity in cell(bar):
            # Reveal the question before the complete reply, using the same
            # rhythm later. Do not replace every four-bar phrase with a fill.
            if bar < 17 and velocity < 80: continue
            if bar < 25 and pitch == 33: pitch = 23
            global_at = (bar-1)*4+at
            gain = .19 if 57 <= bar < 81 or 97 <= bar < 121 else .175
            cutoff = 12000.; register = 0.
            if 41 <= bar < 57:
                rel = bar-41
                gain *= .78 if rel < 4 else .66 if rel < 8 else .60
                cutoff = 160 if rel < 8 else 260
                if rel >= 12: gain=.135; register=1.; cutoff=12000
            elif 73 <= bar < 97:
                gain = float(ramp(global_at, [(73,.19),(81,.19),(85,.183),
                                  (89,.17),(93,.151),(95,.145),(97,.145)]))
                cutoff = float(ramp(global_at, [(73,12000),(81,12000),(85,7000),
                                    (89,2400),(93,700),(95,1200),(97,1800)]))
                register = float(np.clip((bar+at/4-92)/3, 0, 1))
            low = render(pitch, duration, velocity >= 97)
            if cutoff < 10000: low = hf.filt(low, cutoff)
            take = low*(1-register)
            if register: take = take + render(pitch+12, duration, velocity >= 97)*register
            put(y, take, global_at, gain*velocity/108)
            notes.append([pitch+12 if register == 1 else pitch, global_at, duration, velocity])
            events.append(dict(bar=bar, beat=at, pitch=pitch, duration=duration,
                               velocity=velocity, gain=gain, cutoff=cutoff, upper_mix=register))
    # The actual approved kick drives clearance, including the half-time break.
    for beat in range(512):
        if np.max(abs(kick[sample(beat):sample(beat+.12)])) < .01: continue
        lo, hi = max(0,sample(beat)-round(.006*SR)), min(n,sample(beat)+round(.170*SR))
        t = np.arange(lo,hi)/SR-beat*BEAT
        g = np.ones(len(t),np.float32); pre = t < 0
        g[pre] = 1-.72*(.5-.5*np.cos(np.pi*(t[pre]+.006)/.006))
        q = np.clip((t[~pre]-.025)/.145,0,1)
        g[~pre] = .28+.72*(.5-.5*np.cos(np.pi*q))
        y[lo:hi] *= g[:,None]
    silence(y,159.5,160,.015)
    for bar in (56,96): silence(y,(bar-1)*4+3,bar*4,.025)
    # Match the main passage's average level: articulation, not added gain,
    # must account for the audible difference. One gain for the whole track.
    a,b = sample(256),sample(320)
    match = rms(old[a:b])/max(rms(y[a:b]),1e-9)
    assert .80 < match < 1.25, match
    y *= match
    assert np.isfinite(y).all() and np.max(abs(y)) < .85
    assert np.array_equal(y[:,0],y[:,1])
    ordered = sorted(events, key=lambda e:(e['bar']-1)*4+e['beat'])
    for e,f in zip(ordered,ordered[1:]):
        assert (e['bar']-1)*4+e['beat']+e['duration'] <= (f['bar']-1)*4+f['beat']+.001
    measures=[]
    for first,last in [(9,17),(25,41),(41,49),(49,57),(57,73),(73,81),(81,85),(85,89),(89,93),(93,97),(97,121)]:
        a,b=sample((first-1)*4),sample((last-1)*4)
        measures.append(dict(first=first,last=last,old_rms_db=db(old[a:b]),new_rms_db=db(y[a:b])))
    path = OUT/'02 Sub Bass - pergunta resposta 4 compassos.wav'
    sf.write(path,y,SR,subtype='PCM_24')
    midi.write(str(OUT/'Sub B0 - pergunta resposta.mid'), [('Sub B0',0,notes)], BPM)
    dump('source-checks.json',dict(mono=True,peak_db=float(20*np.log10(np.max(abs(y)))),
          matched_gain_db=float(20*np.log10(match)),passages=measures,
          no_note_overlaps=True,scope='Dry source only; excludes native EQ, returns and master.'))
    dump('arrangement.json',dict(path=str(path),beats=512,events=events,
         source=ss.SOURCES,preserve_drums=True,record_master=False))
    print(json.dumps(dict(prepared=len(events),checks=measures,match_db=20*np.log10(match)),indent=2),flush=True)


def stage():
    assert not (OUT/'live-changes.json').exists(), 'Already staged; inspect the receipt.'
    state=json.loads((OUT/'before.json').read_text())
    plan=json.loads((OUT/'arrangement.json').read_text())
    for role, expected in state['tracks'].items():
        actual=client.call('get_track',dict(track=role,clips=True))
        assert actual == expected, f'Live changed since snapshot: {role}'
    assert client.call('record_status').get('state') not in ('recording','finalizing')
    result=server._journaled('transport',dict(action='stop'))
    log=[dict(cmd='transport',args=dict(action='stop'),result=result)]
    dump('live-changes.json',log)
    commands=[dict(cmd='delete_clips_in_range',args=dict(track=ROLE,start_bar=1,end_bar=130)),
              dict(cmd='create_audio_clip',args=dict(track=ROLE,path=plan['path'],bar=1,
                   name='02 Sub Bass | pergunta e resposta 4c',warp=False,gain_db=0))]
    results=server.ableton_batch(commands)
    log.extend(dict(command=c,result=r) for c,r in zip(commands,results));dump('live-changes.json',log)
    assert all(r.get('ok') for r in results), results
    after={role:client.call('get_track',dict(track=role,clips=True)) for role in state['tracks']}
    for role in state['tracks']:
        if role != ROLE: assert after[role] == state['tracks'][role],role
    clips=after[ROLE]['clips']
    assert len(clips)==1 and abs(clips[0]['length']-512)<.01 and not clips[0]['muted']
    assert Path(clips[0]['file']) == Path(plan['path'])
    dump('after.json',after)
    print('STAGED bass only; 15 other tracks unchanged, including all approved drums.',flush=True)


if __name__ == '__main__':
    {'prepare':prepare,'stage':stage}[sys.argv[1]]()
