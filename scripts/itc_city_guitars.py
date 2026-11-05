"""In the City: the City call & response on guitars, trance effects, in the groove, at house levels.

His note (2026-11-05): "não gostei nada dos timbres, tem que ser algo mais perto da guitarra que era nossa ref,
colocar uns efeitos de trance, encaixar no groove, arrumar a mix que estão muito altos, timbrar bem no padrão house".

Timbre, 1/3-octave-ish bands 100 Hz-12.8 kHz against the reference isolated in drop 1 (set minus the set without
City), mean band distance: Guitar Electric Clean (sampled guitar) 1.6 dB on the call; Strat Bright 3.3; Clean Chorus
3.7. Every muted guitar read 13-15 dB dark at 3-6 kHz against the reference guitar's hits, so the response is the same
sampled guitar played short, brighter, with its own effects.

The CITY SYNTH bus EQ was cut for the old sample (HP 400, -5 dB at 2.05 kHz, -3 at 3.33 kHz, shelf -2, LP 7 kHz): on a
new guitar it only dulled it. House standard instead: HP 280, -4.5 at 350 (mud), high shelf +3 at 4.5 kHz, +2.5 at 3 kHz (the reference guitar's
presence: the sampled guitar read 6-8 dB dark at 1.6-6.4 kHz), LP 11 kHz, and the
bus compressor keyed by the KICK so the guitars and their delays pump with the groove.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client

C = client.call
BUS = 'CITY SYNTH'
CALL, RESP = 'CITY CALL (synth 1)', 'CITY RESPONSE (synth 2)'
GUITAR = 'sounds/Guitar & Plucked/Guitar Electric Clean.adg'
GROOVE = 'Swing 16ths 66'


def p(track, device, name, **kw):
    C('set_param', {'track': track, 'device': device, 'param': name, **kw})


def sounds():
    for t in (CALL, RESP):
        devs = C('get_track', {'track': t})['devices']
        if not devs or devs[0]['name'] != 'Guitar Electric Clean':
            for d in reversed(devs):
                C('delete_device', {'track': t, 'device': d['i']})
            C('load_device', {'track': t, 'path': GUITAR}, timeout=40.0)
        p(t, 0, 'Reverb', value=0.0)                       # space comes from the sends, ducked by the kick
    p(CALL, 0, 'Release', display='1.20 s')
    p(RESP, 0, 'Release', display='400 ms')                 # short hits
    p(RESP, 0, 'Phaser', value=0.0)


def delay(track, l16, r16, feedback, wet, freq):
    if not any(d['name'] == 'Delay' for d in C('get_track', {'track': track})['devices']):
        C('load_device', {'track': track, 'path': 'audio_effects/Delay'}, timeout=30.0)
    for name, kw in (('Link', {'value': 0.0}), ('Ping Pong', {'value': 1.0}), ('L Sync', {'value': 1.0}),
                     ('R Sync', {'value': 1.0}), ('L 16th', {'display': str(l16)}), ('R 16th', {'display': str(r16)}),
                     ('Feedback', {'display': f'{feedback} %'}), ('Filter On', {'value': 1.0}),
                     ('Filter Freq', {'display': freq}), ('Filter Width', {'display': '5.00'}),
                     ('Dry/Wet', {'display': f'{wet} %'})):
        p(track, 'Delay', name, **kw)


def fx():
    delay(RESP, 3, 4, 38, 24, '2.00 kHz')                  # trance throw: dotted 8th left, quarter right
    delay(CALL, 3, 3, 22, 12, '1.50 kHz')
    C('set_send', {'track': CALL, 'send': 2, 'db': -14.0})  # C-Atmos
    C('set_send', {'track': CALL, 'send': 4, 'db': -20.0})  # E-Plate
    C('set_send', {'track': RESP, 'send': 0, 'db': -16.0})  # A-Reverb
    C('set_send', {'track': RESP, 'send': 2, 'db': -18.0})


def bus():
    for b, on, kind, freq, gain, q in ((1, 1, None, '280 Hz', None, None), (2, 1, None, '350 Hz', -4.5, '1.00'),
                                       (3, 1, None, '3.00 kHz', 2.5, '0.80'), (4, 0, None, None, None, None),
                                       (5, 0, None, None, None, None), (6, 0, None, None, None, None),
                                       (7, 1, None, '4.50 kHz', 3.0, None), (8, 1, None, '11.0 kHz', None, None)):
        p(BUS, 'EQ Eight', f'{b} Filter On A', value=float(on))
        if freq:
            p(BUS, 'EQ Eight', f'{b} Frequency A', display=freq)
        if gain is not None:
            p(BUS, 'EQ Eight', f'{b} Gain A', value=gain)
        if q:
            p(BUS, 'EQ Eight', f'{b} Q A', display=q)
    C('set_device_input', {'track': BUS, 'device': 'Compressor', 'source': 'KICK', 'channel': 'Post Mixer'})
    for name, kw in (('Threshold', {'display': '-28.0 dB'}), ('Ratio', {'display': '4.00 : 1'}),
                     ('Attack', {'display': '1.00 ms'}), ('Release', {'display': '140 ms'})):
        p(BUS, 'Compressor', name, **kw)


def groove():
    for t in (CALL, RESP):
        print(t, C('apply_groove', {'track': t, 'groove': GROOVE}))


def level(call_db=2.5, resp_db=0.0):
    # at -9/-10 the riff read -34.7 LUFS alone in drop 1, the sample -20.8: aim ~4 dB under the sample
    C('set_track', {'track': CALL, 'volume_db': call_db})
    C('set_track', {'track': RESP, 'volume_db': resp_db})


if __name__ == '__main__':
    steps = {'sounds': sounds, 'fx': fx, 'bus': bus, 'groove': groove, 'level': level}
    for name in sys.argv[1:] or steps:
        print(name)
        steps[name]()
