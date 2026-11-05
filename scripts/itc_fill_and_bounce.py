"""In the City: fill without clutter. The City synth without its pad, bass presence, texture, a 16th layer that fits.

His note (2026-11-05): "tirar o pad do fundo do synth city ... fica um pouco vazio ... mais textura, mais presença do
baixo, mais sub ... falta movimento, bounce, call & response ... aquela textura de fundo".
Measured against dub_house_streets: bass harmonics -15 dB (refs -10..-7), noisiness .10 (.14-.20), high-mid 2.1 %
(3-3.4), high 1 % (2.3-3.2), hat level -22.8 (-18..-16), no 16th layer. Sub share already above the refs.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
HAT = 'HAT 16ths DCW'
HAT_SAMPLE = 'user_library/Samples/Claude/Murder Kit/DCW_Closed_Hat_04.wav'
TAPE = 'TEXTURE tape'
TAPE_FILE = ('/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples/Loops/Texture/'
             'Noise Tape Floor.wav')
POCKET = 0.0225
HAT_SPANS = ((9, 49), (65, 88), (89, 97), (121, 144), (145, 177))     # relief only: out in breaks, builds, kick-outs
ACCENT = {0: 76, 1: 62, 2: 92, 3: 68}                                 # the "and" up, ghosts between (refs: xgXg)


def city_pad():
    for name, kw in (('Threshold', {'display': '-25.0 dB'}), ('Floor', {'display': '-36.0 dB'}),
                     ('Hold', {'display': '30.0 ms'}), ('Release', {'display': '80.0 ms'})):
        C('set_param', {'track': 'CITY SYNTH', 'device': 'Gate', 'param': name, **kw})


def eq_band(track, freq_text):
    p = {x['name']: x['display'] for x in C('get_device', {'track': track, 'device': 'EQ Eight'})['params']}
    return next(b for b in range(1, 9) if p[f'{b} Filter On A'] == 'On' and p[f'{b} Frequency A'] == freq_text)


def bass():
    C('set_param', {'track': 'BASS', 'device': 'EQ Eight', 'param': f"{eq_band('BASS', '843 Hz')} Frequency A", 'display': '1.60 kHz'})
    C('set_param', {'track': 'BASS', 'device': 'EQ Eight', 'param': f"{eq_band('BASS', '50.0 Hz')} Gain A", 'value': -1.0})
    C('set_param', {'track': 'BASS', 'device': 'EQ Eight', 'param': f"{eq_band('BASS', '180 Hz')} Gain A", 'value': 0.0})
    C('set_param', {'track': 'BASS', 'device': 'Saturator', 'param': 'Dry/Wet', 'value': 0.6})


def texture():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if TAPE not in names:
        C('create_track', {'kind': 'audio', 'name': TAPE})
        C('set_track_input', {'track': TAPE, 'source': 'No Input'})
        C('set_track_output', {'track': TAPE, 'dest': 'MUSIC BUS'})
        C('set_track', {'track': TAPE, 'color_index': 21, 'volume_db': -8.0})
        C('create_audio_clip', {'track': TAPE, 'path': TAPE_FILE, 'beat': 0.0, 'name': 'tape', 'warp': True,
                                'warp_mode': 'texture', 'beats': 16})
        print(C('fill_range', {'track': TAPE, 'src_start_bar': 1, 'src_end_bar': 5, 'start_bar': 5, 'end_bar': 185}, timeout=60.0))
    C('set_track', {'track': 'TEXTURE vinyl', 'volume_db': -15.0})
    C('set_send', {'track': 'MURDER BUS - drop', 'send': 2, 'db': -18.0})   # the riff and the City share the atmos


def hat():
    names = [t['name'] for t in C('get_song', {})['tracks']]
    if HAT not in names:
        C('create_track', {'kind': 'midi', 'name': HAT})
        C('load_device', {'track': HAT, 'path': HAT_SAMPLE}, timeout=40.0)
        C('load_device', {'track': HAT, 'query': 'EQ Eight'}, timeout=30.0)
    C('set_track_output', {'track': HAT, 'dest': 'TOPS'})
    C('set_track', {'track': HAT, 'color_index': 17, 'volume_db': -14.0})
    C('set_send', {'track': HAT, 'send': 3, 'db': -24.0})
    for name, kw in (('Volume', {'display': '-12.0 dB'}), ('Vol < Vel', {'value': 0.35})):
        C('set_param', {'track': HAT, 'device': 0, 'param': name, **kw})
    for name, kw in (('1 Filter On A', {'value': 1.0}), ('1 Filter Type A', {'value': 1.0}), ('1 Frequency A', {'display': '300 Hz'})):
        C('set_param', {'track': HAT, 'device': 'EQ Eight', 'param': name, **kw})
    if not C('get_track', {'track': HAT, 'clips': True}).get('clips'):
        notes = []
        for a, z in HAT_SPANS:
            for k in range(int((a - 1) * 16), int((z - 1) * 16)):
                bar_i, slot = k // 16, k % 16
                if slot == 7 and bar_i % 2:      # a pocket every 2nd bar
                    continue
                vel = ACCENT[slot % 4] + ((k * 7) % 5) - 2       # a steady hand: +-2, repeatable
                notes.append([60, k * 0.25 + (POCKET if k % 2 else 0.0), 0.1, float(vel)])
        C('create_midi_clip', {'track': HAT, 'bar': 1, 'length': 736, 'name': 'hat 16ths', 'notes': notes}, timeout=120.0)
        C('apply_groove', {'track': HAT, 'groove': 'Swing 16ths 66'})
        print(' hat notes', len(notes))


def riff_answers():
    # the riff steps back further while the voice speaks, and fills the gaps it leaves
    C('set_param', {'track': 'MURDER BUS - drop', 'device': 'Compressor', 'param': 'Threshold', 'display': '-28.0 dB'})
    C('set_param', {'track': 'MURDER BUS - drop', 'device': 'Compressor', 'param': 'Ratio', 'display': '4.00 : 1'})
    C('set_param', {'track': 'MURDER BUS - drop', 'device': 'Compressor', 'param': 'Release', 'display': '220 ms'})


if __name__ == '__main__':
    steps = {'city': city_pad, 'bass': bass, 'texture': texture, 'hat': hat, 'riff': riff_answers}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
