"""Keep the dance pulse through both breaks and develop one recurring house cell.

Prepare offline, then stage bounded clip replacements via ClaudeBridge. The open
Groove Identity copy and before.json retain the previous pass. No master recording:
the producer is following playback directly in Live.
"""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import soundfile as sf
from scipy import ndimage, signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, loops, server
from ableton_claude.ear import midi
import th130_house_fit as hf
import th130_string_signature as ss
from th130_arrangement_motion import CHAPTERS, edges, put, sample, silence
from th130_remix_conversation import assemble

SR, BPM, BEAT = 44100, 130, 60 / 130
OUT = Path.home() / 'Music/Ableton/User Library/Samples/Codex/TH130 Pulse Story 2026-10-17'
ROLES = ['01 Kick', '02 Sub Bass', '03 Clap', '04 Closed Hat', '05 Open Hat',
         '06 Percussion', '07 Chicago Top Loop', '08 Build Snare',
         '09 Chicago Stab', '10 House Keys', '13 Uplifter']
VOICE = '16 Spoken Words'
SWING = .287
CORE = [('S', .5, .10, .62), ('K', 1.787, .23, .95), ('S', 2.787, .10, 1.),
        ('S', 4.287, .17, .88), ('K', 5.787, .30, 1.), ('K', 7.287, .11, .55)]
# Keep deep, held B0 anchors. Their earlier releases leave a real pocket for
# the answer; the quiet 5.775 pickup connects to the key at 5.787 (5.5 ms later).
BASS = [(23, .5, 1.16, 108), (23, 2.775, .20, 83), (30, 3.5, .25, 76),
        (23, 4.275, 1.23, 104), (23, 5.775, .18, 70),
        (23, 6.5, .80, 98), (23, 7.775, .16, 75)]


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2))


def C(cmd, **args):
    p = OUT / 'live-changes.json'
    log = json.loads(p.read_text()) if p.exists() else []
    result = server._journaled(cmd, args)
    log.append(dict(cmd=cmd, args=args, result=result)); dump(p.name, log)
    return result


def tones():
    raw = hf.filt(hf.source('wasc_key_housey_Bmin9.wav', '/resampled & effected/'), 200, 'highpass')
    upper = signal.resample_poly(raw, 1, 2, axis=0).astype(np.float32)
    key = hf.filt(.55 * raw[:len(upper)] + .60 * upper, 6800)
    key /= np.max(abs(key))
    mid = key.mean(axis=1); side = (key[:, 0] - key[:, 1]) * .5
    side -= hf.filt(side[:, None], 300)[:, 0]
    key = np.column_stack([mid + side * 1.08, mid - side * 1.08]).astype(np.float32)
    key /= np.max(abs(key))
    stab = hf.filt(ss.read('PL_DTP2_Reveal_Sample_ChicagoKey_G3.wav'), 210, 'highpass')
    stab = hf.filt(ss.pitch(stab, 66.85, 71, .65, .007, .06), 5700)
    stab /= np.max(abs(stab))
    mono = stab.mean(axis=1)
    return {'K': key, 'S': .70 * np.column_stack([mono, mono]) + .30 * stab}


def bass_voice():
    raw = ss.read('Odd Frequency - Grid Vol 2 - Bass Shot 2 - B.wav').mean(axis=1)
    t = np.arange(round(.035 * SR), round(.12 * SR)) / SR
    f = 440 * 2 ** ((35 - 69) / 12)
    basis = np.column_stack([fn(2 * np.pi * f * h * t)
                            for h in range(1, 9) for fn in (np.sin, np.cos)])
    c = np.linalg.lstsq(basis, raw[round(.035 * SR):round(.12 * SR)], rcond=None)[0]
    cache = {}

    def note(pitch, duration):
        k = (pitch, duration)
        if k not in cache:
            time = np.arange(sample(duration)) / SR
            f0 = 440 * 2 ** ((pitch - 69) / 12)
            x = sum(c[2 * (h - 1)] * np.sin(2 * np.pi * f0 * h * time) +
                    c[2 * (h - 1) + 1] * np.cos(2 * np.pi * f0 * h * time)
                    for h in range(1, 9))
            x += sum(.42 * (c[2 * (h - 1)] * np.sin(2 * np.pi * f0 * 2 * h * time) +
                           c[2 * (h - 1) + 1] * np.cos(2 * np.pi * f0 * 2 * h * time))
                     for h in range(1, 5))
            x /= max(np.max(abs(x)), 1e-9)
            x *= .84 + .16 * np.exp(-time / .07)
            cache[k] = hf.edge(np.repeat(x[:, None], 2, axis=1).astype(np.float32),
                               .008, .045 if duration > .5 else .022)
        return cache[k]
    return note


def spoken():
    sources = json.loads((OUT / 'spoken-candidates.json').read_text())
    phrases = {}
    for name, filename in [('Music', 'OWN_122_TalkAboutMusic.wav'),
                           ('Reply', 'OWN_122_ThatsWhatWeGot.wav'),
                           ('Club', 'OWN_122_ClubSceneBeauty.wav')]:
        source = next(s['path'] for s in sources if s['name'] == filename)
        path = OUT / f'Spoken {name} - full phrase 130.wav'
        subprocess.run(['/opt/homebrew/bin/ffmpeg', '-hide_banner', '-loglevel', 'error',
                        '-y', '-i', source, '-af', 'atempo=1.065573770', str(path)], check=True)
        x = loops.read(str(path)).astype(np.float32)
        x = np.repeat(x.mean(axis=1, keepdims=True), 2, axis=1)
        x = hf.filt(hf.filt(x, 140, 'highpass'), 7600)
        x = hf.edge(x, .005, .045)
        x *= .22 / max(np.max(abs(x)), 1e-9)
        sf.write(path, x, SR, subtype='PCM_24')
        phrases[name] = dict(path=str(path), source=source, duration_s=len(x) / SR)
    return phrases


def prepare():
    assert not (OUT / 'live-changes.json').exists(), 'Pass staged: never overwrite audio currently used in Live.'
    state = json.loads((OUT / 'before.json').read_text())
    n = sample(512)
    y = {r: assemble(state['tracks'][r], n) for r in ROLES}
    y[VOICE] = np.zeros((n, 2), np.float32)
    original = {r: y[r].copy() for r in ['01 Kick', '02 Sub Bass']}
    shots = tones(); held = bass_voice(); events = []; notes = []
    y['02 Sub Bass'][:] = 0
    # Identical source phase and timbre to the retained kick, without copying a
    # whole bar whose later hits/tails could double the new transition pattern.
    kick = edges(original['01 Kick'][sample(256):sample(256)+sample(.85)], .001, .020)
    assert np.max(abs(kick)) > .05, 'Take a real kick from the established groove, not the silent intro.'
    top = ss.read('SOBV2_TOP_chicago_126bpm.wav')
    top = signal.resample(top, sample(16), axis=0).astype(np.float32)
    top = hf.edge(hf.filt(hf.filt(top, 420, 'highpass'), 13500), .002, .008)

    def harmonic(role, at, duration, gain, cutoff):
        shot = hf.edge(shots[role][:round(duration * SR)], .010 if role == 'K' else .006,
                       min(.045, duration * .38))
        shot = hf.filt(shot, min(cutoff, 6800 if role == 'K' else 5700))
        put(y['10 House Keys' if role == 'K' else '09 Chicago Stab'], shot, at, gain)
        events.append(dict(role=role, beat=at, duration_s=duration, gain=gain, cutoff=cutoff))

    # Bass arcs keep one two-bar identity; small turnarounds appear once per 8
    # bars. The last two notes no longer disappear together for half a phrase.
    for bar in range(9, 129, 2):
        if bar >= 125: continue
        first = 41 if 41 <= bar < 57 else 81 if 81 <= bar < 97 else None
        rel = bar - first if first else None
        strong = 57 <= bar < 81 or 97 <= bar < 121
        gain = .19 if strong else .175
        pattern = BASS.copy()
        if (bar - 9) % 8 == 6:
            pattern = [v for v in pattern if v[1] != 7.775]
            pattern = [(p, a, .56 if a == 6.5 else d, v) for p, a, d, v in pattern]
        if first:
            if rel < 4: gain *= .78
            elif rel < 8: gain *= .66 if first == 41 else .72
            elif rel < 12: gain *= .60
            else:
                # The last four bars release the deepest octave, but retain a
                # moving bass body. The drop restores B0 and the full kick.
                gain = .135 if first == 41 else .145
                pattern = [(35, .5, .60, 104), (35, 2.787, .30, 82),
                           (35, 4.287, .60, 103), (35, 5.787, .24, 76),
                           (42, 7.287, .32, 72)]
        for pitch, at, duration, vel in pattern:
            shot = held(pitch, duration)
            if first and rel < 12: shot = hf.filt(shot, 160 if rel < 8 else 260)
            put(y['02 Sub Bass'], shot, (bar - 1) * 4 + at, gain * vel / 108)
            notes.append([pitch, (bar - 1) * 4 + at, duration, vel])

    # Actual kick-driven ducking only where a kick exists. Cosine transitions
    # avoid the old sub's abrupt phase-boundary gain step.
    kick_times = []
    for bar in range(1, 129):
        in_break = 41 <= bar < 57 or 81 <= bar < 97
        if not in_break:
            for at in range(4):
                if np.max(abs(original['01 Kick'][sample((bar-1)*4+at):sample((bar-1)*4+at+.12)])) > .01:
                    kick_times.append((bar-1)*4+at)
            continue
        first = 41 if bar < 57 else 81; rel = bar - first
        start, stop = sample((bar-1)*4), sample(bar*4)
        y['01 Kick'][start:stop] = 0
        if rel >= 12: continue
        beats = [0, 2] if first == 41 and rel >= 4 else [0, 1, 2, 3]
        level = (.72 if first == 81 else .68) if rel < 4 else .60 if rel < 8 else .48
        cutoff = 2000 if rel < 4 else 1400 if rel < 8 else 1050
        for at in beats:
            put(y['01 Kick'], hf.filt(kick, cutoff), (bar-1)*4+at, level)
            kick_times.append((bar-1)*4+at)
    for at in kick_times:
        a, b = max(0, sample(at)-round(.006*SR)), min(n, sample(at)+round(.170*SR))
        t = np.arange(a, b)/SR-at*BEAT
        envelope = np.ones(len(t), np.float32)
        pre = t < 0
        envelope[pre] = 1-.72*(.5-.5*np.cos(np.pi*(t[pre]+.006)/.006))
        q = np.clip((t[~pre]-.025)/.145, 0, 1)
        envelope[~pre] = .28+.72*(.5-.5*np.cos(np.pi*q))
        y['02 Sub Bass'][a:b] *= envelope[:, None]

    # Keep the existing drum pocket but bring the supporting pulse forward
    # across the breaks. Different low-end handling makes the breaks distinct.
    for first in (41, 81):
        for b in range(16):
            a, z = sample((first+b-1)*4), sample((first+b)*4)
            for role in ['03 Clap', '04 Closed Hat', '06 Percussion']:
                seg = y[role][a:z].copy()
                factor = (1.45 if b < 8 else 1.55) if first == 81 else (1.36 if b < 8 else 1.50)
                dark = hf.filt(seg, 4300 if role != '06 Percussion' else 3700)
                opened = min(1., .25+b*.06)
                y[role][a:z] = (dark*(1-opened)+seg*opened)*factor
            count = z-a; i = sample((b%4)*4)
            loopbar = top[i:i+count]
            if len(loopbar) < count: loopbar = np.pad(loopbar, ((0,count-len(loopbar)),(0,0)))
            y['07 Chicago Top Loop'][a:z] = hf.filt(loopbar, 5000+b*400) * (.045+.002*b)
        # Snare roll builds for four bars, not eight repeated snare bars.
        a, z = sample((first+7)*4), sample((first+15)*4)
        env = np.linspace(.22, 1., z-a, dtype=np.float32)[:,None]
        y['08 Build Snare'][a:z] *= env

    # Re-articulate the existing remembered cell, revealing it across chapters.
    # Harmonic roots/voicing stay Bm/Bm9; this is phrase development, not a new
    # transposed chord on every hit.
    for r in ['09 Chicago Stab', '10 House Keys']: y[r][:] = 0
    harmonic('S', 22.5, .10, .055, 1900)
    harmonic('K', 29.787, .20, .070, 2700)
    for bar in range(13, 121, 2):
        base = (bar-1)*4; pair = ((bar-1)//2)%4
        pattern = CORE.copy(); gain = .17; cutoff = 4400
        if bar < 17: pattern = [CORE[1], CORE[2]]; gain = .12; cutoff = 2700
        elif bar < 25: pattern = [CORE[1], CORE[2], CORE[4]]; gain = .14; cutoff = 3400
        elif bar < 33: gain = .165; cutoff = 4400
        elif bar < 41: gain = .175; cutoff = 4700+(bar-33)*90
        elif 57 <= bar < 81 or bar >= 97:
            gain = .19 if bar < 97 else .195; cutoff = 5700
            if bar in (57,59,73,75,105,107): pattern = [CORE[i] for i in (0,1,3,4)]
        first = 41 if 41 <= bar < 57 else 81 if 81 <= bar < 97 else None
        if first:
            rel = bar-first
            gain = .177+rel*.0012; cutoff = min(5700, 3000+rel*210)
            if rel == 0:
                harmonic('S', base, .22, gain, cutoff)
                pattern = [CORE[i] for i in (1,2,3,4)]
            if rel < 8:
                pattern = [(r,t,.38 if r=='K' and t==5.787 else d,v) for r,t,d,v in pattern]
            if rel >= 12:
                # Repetition tightens while the answering key still identifies
                # the phrase. Reserve the final beat, not an entire empty bar.
                pattern = [('S', t, .085, v) for t,v in
                           [(.5,.85),(1.5,.62),(2.5,.95),(3.5,.62),(4.5,.9),(5.5,.68)]]
                pattern += [('K',6.287,.18,.96)]
                if rel == 14: pattern += [('S',6.5,.07,.55)]
        if pair == 2 and not (first and bar-first>=12):
            pattern = [v for v in pattern if v[1] != 7.287]
            pattern += [('K',3.5,.11,.43),('S',7.787,.075,.43)]
        elif pair == 3 and not (first and bar-first>=12):
            pattern = [v for v in pattern if v[1] != 7.287]
        for role, at, dur, vel in pattern: harmonic(role, base+at, dur, gain*vel, cutoff)

    # Announce the break with a familiar reversed key, keeping the forward
    # motif intact. Reduce the long generic noise lift into these dance breaks.
    for first in (33, 73):
        a, z = sample((first-1)*4), sample((first+7)*4)
        y['13 Uplifter'][a:z] *= np.linspace(.12,.65,z-a,dtype=np.float32)[:,None]
        reverse = hf.edge(hf.filt(shots['K'][:round(.38*SR)][::-1],3800),.04,.008)
        put(y['10 House Keys'], reverse, (first+7)*4-.38/BEAT, .055)
    for first in (49,89):
        a,z=sample((first-1)*4),sample((first+7)*4)
        y['13 Uplifter'][a:z] *= np.linspace(.38,1.,z-a,dtype=np.float32)[:,None]

    phrases = spoken()
    calls = [(23,'Music'),(43,'Reply'),(51,'Music'),(71,'Reply'),
             (83,'Club'),(91,'Music'),(107,'Reply'),(117,'Club')]
    for bar, phrase in calls:
        x = loops.read(phrases[phrase]['path']).astype(np.float32)
        put(y[VOICE], x, (bar-1)*4, .92 if phrase=='Club' else 1.)
    activity = ndimage.uniform_filter1d(abs(y[VOICE]).mean(axis=1), size=round(.025*SR))
    clearance = 1-.16*np.clip(activity/.025,0,1)
    for r in ['09 Chicago Stab','10 House Keys']: y[r] *= clearance[:,None]

    for bar in (40,80):
        for r in ['01 Kick','02 Sub Bass','03 Clap','04 Closed Hat','05 Open Hat',
                  '06 Percussion','07 Chicago Top Loop']:
            silence(y[r], (bar-1)*4+3.5, bar*4, .015)
    for bar in (56,96):
        for z in y.values(): silence(z,(bar-1)*4+3,bar*4,.025)
    assets=[]
    for role,z in y.items():
        assert np.isfinite(z).all() and np.max(abs(z))<.85,(role,np.max(abs(z)))
        for bar in CHAPTERS:
            chunk=edges(z[sample((bar-1)*4):sample((bar+7)*4)],.001,.003)
            if np.max(abs(chunk))<1e-7: continue
            path=OUT/f'{bar:03d}_{role}.wav'
            sf.write(path,chunk,SR,subtype='PCM_24')
            assets.append(dict(track=role,path=str(path),bar=bar,beats=32,
                               name=role+' | '+('pulso e expectativa' if bar in (41,49,81,89) else 'motivo e bounce')))
    midi.write(str(OUT/'Sub Bounce - phrase development.mid'), [('Sub Bounce',0,notes)],BPM)
    midi.write(str(OUT/'Stab Keys - evolving shared cell.mid'),
               [(r,i,[[71,e['beat'],e['duration_s']/BEAT,min(127,round(e['gain']/.195*100))]
                      for e in events if e['role']==r]) for i,r in enumerate(['S','K'])],BPM)
    # Source-domain checks are not a master render. Verify continuity and mono
    # independently of loudness/FX, without interrupting Live for a recording.
    rms=lambda z:float(20*np.log10(max(np.sqrt(np.mean(z.astype(np.float64)**2)),1e-12)))
    continuity=[]
    for bar in (37,41,45,49,53,57,77,81,85,89,93,97):
        a,z=sample((bar-1)*4),sample((bar+3)*4)
        continuity.append(dict(bar=bar,kick_rms_db=rms(y['01 Kick'][a:z]),
                               bass_rms_db=rms(y['02 Sub Bass'][a:z]),
                               harmony_rms_db=rms(y['09 Chicago Stab'][a:z]+y['10 House Keys'][a:z])))
    assert all(v['bass_rms_db']>-45 for v in continuity)
    assert all(v['kick_rms_db']>-38 for v in continuity if v['bar'] not in (53,93))
    assert np.array_equal(y['02 Sub Bass'][:,0],y['02 Sub Bass'][:,1])
    dump('source-checks.json',dict(continuity=continuity,bass_mono=True,
         note='Source audio checks only; no claim of final master loudness or subjective groove.'))
    dump('arrangement.json',dict(bpm=BPM,key='B minor',assets=assets,events=events,
         bass_pattern=BASS,core=CORE,spoken_calls=calls,spoken_sources=phrases,
         sources=dict(hf.SOURCES,**ss.SOURCES),no_master_recording=True))
    print('PREPARED',len(assets),'clips; source continuity',continuity,flush=True)


def stage():
    state=json.loads((OUT/'before.json').read_text());plan=json.loads((OUT/'arrangement.json').read_text())
    song=client.call('get_song');assert song['tempo']==BPM
    assert VOICE not in [t['name'] for t in song['tracks']]
    # Preflight every replacement before the first range mutation.
    for role in ROLES:
        t=client.call('get_track',dict(track=role,clips=True));old=state['tracks'][role]
        assert [(c['start'],c['file'],c['gain_db']) for c in t['clips']]==[(c['start'],c['file'],c['gain_db']) for c in old['clips']],role
    C('transport',action='stop');C('set_loop',on=False)
    for role in ROLES:
        C('delete_clips_in_range',track=role,start_bar=1,end_bar=130)
        for a in plan['assets']:
            if a['track']==role:
                C('create_audio_clip',track=role,path=a['path'],bar=a['bar'],name=a['name'],warp=False,gain_db=0)
        print('LIVE',role,flush=True)
    C('create_track',kind='audio',name=VOICE)
    C('set_track',track=VOICE,volume_db=-1,pan=0,arm=False,monitoring='off')
    C('set_track_input',track=VOICE,source='No Input')
    C('set_send',track=VOICE,send=2,db=-24)
    for a in plan['assets']:
        if a['track']==VOICE:
            C('create_audio_clip',track=VOICE,path=a['path'],bar=a['bar'],name='Spoken | frases completas do pack',warp=False,gain_db=0)
    for bar,name in [(13,'MOTIVO - primeiras pistas'),(25,'TEMA - conversa revelada'),
                     (41,'BREAK I - pulso continua'),(45,'BREAK I - meio tempo e resposta'),
                     (49,'BUILD I - motivo abre'),(53,'TENSAO - sub suspenso, corpo continua'),
                     (57,'DROP I - peso e resposta'),(81,'BREAK II - groove mantido'),
                     (89,'BUILD II - conversa cresce'),(93,'TENSAO - prepara o peso'),
                     (97,'DROP II - tema completo')]:C('set_cue',bar=bar,name=name)
    for role in ROLES+[VOICE]:
        t=client.call('get_track',dict(track=role,clips=True))
        assert t['n_clips']==sum(a['track']==role for a in plan['assets']),role
        assert all(abs(c['length']-32)<.01 for c in t['clips']),role
    dump('after.json',client.call('get_song'))
    print('READY - audition Live bars 37-65 and 77-105; no recording started',flush=True)


if __name__=='__main__':
    stage() if len(sys.argv)>1 and sys.argv[1]=='stage' else prepare()
