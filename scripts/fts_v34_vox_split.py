"""From The Streets v34: one channel per vocal role, each with its own energy.

His note: "separar em canais diferentes os vocais que são diferentes... e dá pra dar energia".
Roles (all into VOX BUS, the same plate send, so one atmosphere):
  VOX CITY - calls   the theme "City to City" (his one-bar cuts and the pick-up call)
  VOX CITY - hooks   hook A, hook B, hook C and the hook line before drop 1
  VOX CITY - radio   the band-passed far versions
  VOX MURDER - trades  the Murder lines answering the City in drop 2
Each new channel gets its source channel's chain (EQ, compressor, saturator copied), then:
  hooks  a parallel Glue (4:1, 50 % wet) and 1 dB more saturation: denser, closer
  calls  +1.5 dB saturation drive: the theme cuts through the drop
A clip moves by being rebuilt on the new channel (file, syllable warp, markers, gain, mode,
looping) and deleted from the old one.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mcp_server'))
from ableton_claude import client, server

R = Path.home() / 'Desktop/TRACKS 2027/From the streets/Remix 122'
LOG_PATH = R / 'live-changes-v34_vox_split.json'
LOG = []


def C(cmd, **args):
    r = server._journaled(cmd, args)
    LOG.append(dict(cmd=cmd, args=args, result=r))
    LOG_PATH.write_text(json.dumps(LOG, indent=2, default=str))
    print(cmd, args.get('track', ''), str(r)[:100], flush=True)
    return r


def clips(track):
    return client.call('get_track', {'track': track, 'markers': True, 'max_clips': 400})['clips']


def role(c):
    n, f = c['name'], Path(c.get('file') or '').name
    if 'radio' in n.lower() or 'radio' in f.lower():
        return 'VOX CITY - radio'
    if 'call' in n.lower() and 'hook' not in n.lower():
        return 'VOX CITY - calls'
    return 'VOX CITY - hooks'


def make_channel(name, source, after):
    names = [t['name'] for t in client.call('get_song')['tracks']]
    C('create_track', kind='audio', name=name, index=names.index(after) + 1)
    C('set_track_input', track=name, source='No Input')
    C('set_track_output', track=name, dest='VOX BUS')
    src = client.call('get_track', {'track': source, 'clips': False})
    C('set_track', track=name, volume_db=src['vol_db'])
    for k, db in enumerate(src['sends_db']):
        if db > -60:
            C('set_send', track=name, send=k, db=db)
    have = [d['name'] for d in client.call('get_track', {'track': name, 'clips': False})['devices']]
    if 'EQ Eight' not in have:
        C('load_device', track=name, query='EQ Eight')
    C('copy_device', src_track=source, src_device='EQ Eight', track=name, device='EQ Eight')
    for dev in ('Compressor', 'Saturator'):
        C('load_device', track=name, query=dev)
        C('copy_device', src_track=source, src_device=dev, track=name, device=dev)


def move(c, src_track, dst_track):
    at = c['start']
    wm = client.call('warp_markers', {'track': src_track, 'clip': {'at': at}}) if c.get('warping') else None
    C('create_audio_clip', track=dst_track, path=c['file'], beat=at, name=c['name'],
      warp=bool(c.get('warping')), gain_db=c.get('gain_db', 0.0),
      **({'warp_mode': {6: 'complex_pro', 4: 'complex', 0: 'beats', 1: 'tones', 2: 'texture', 3: 'repitch'}
          .get(c.get('warp_mode'), 'complex_pro')} if c.get('warping') else {}))
    if wm:
        C('set_warp_markers', track=dst_track, clip={'at': at},
          markers=[[m['beat'], m['sample_s']] for m in wm['markers']
                   if m['sample_s'] <= wm['sample_s'] - 0.001] or [[0.0, 0.0]])
    C('set_clip', track=dst_track, clip={'at': at}, looping=bool(c.get('looping')),
      loop_end=c['loop_end'], end_marker=c['end_marker'])
    C('set_clip', track=dst_track, clip={'at': at}, loop_start=c['loop_start'],
      start_marker=c['start_marker'])
    new = next(x for x in clips(dst_track) if abs(x['start'] - at) < 1e-3)
    if new['end'] > c['end'] + 1e-3:
        C('trim_clip', track=dst_track, clip={'at': at}, end_beat=c['end'])
    C('delete_clip', track=src_track, clip={'at': at})


def main():
    assert not LOG_PATH.exists(), 'inspect the partial receipt before a retry'
    city = [c for c in clips('VOX CITY') if c['type'] == 'audio']
    roles = {}
    for c in city:
        roles.setdefault(role(c), []).append(c)
    print({k: [round(c['start'] / 4 + 1, 3) for c in v] for k, v in roles.items()})
    after = 'VOX CITY'
    for name in ('VOX CITY - calls', 'VOX CITY - hooks', 'VOX CITY - radio'):
        if roles.get(name):
            make_channel(name, 'VOX CITY', after)
            after = name
            for c in roles[name]:
                move(c, 'VOX CITY', name)
    trades = [c for c in clips('VOX MURDER') if 'trade' in c['name']]
    if trades:
        make_channel('VOX MURDER - trades', 'VOX MURDER', 'VOX MURDER')
        for c in trades:
            move(c, 'VOX MURDER', 'VOX MURDER - trades')

    # energy per role
    C('load_device', track='VOX CITY - hooks', query='Glue Compressor')
    for p, kw in [('Threshold', {'display': '-24'}), ('Ratio', {'item': '4'}), ('Attack', {'item': '1'}),
                  ('Release', {'item': '0.2'}), ('Dry/Wet', {'display': '50'}), ('Makeup', {'display': '3'})]:
        try:
            C('set_param', track='VOX CITY - hooks', device='Glue Compressor', param=p, **kw)
        except Exception as e:
            print('skip', p, str(e)[:80])
    sat = {q['name']: q for q in client.call('get_device', {'track': 'VOX CITY - hooks', 'device': 'Saturator'})['params']}
    drive = float(sat['Drive']['display'].split()[0])
    C('set_param', track='VOX CITY - hooks', device='Saturator', param='Drive', display=str(drive + 1))
    sat = {q['name']: q for q in client.call('get_device', {'track': 'VOX CITY - calls', 'device': 'Saturator'})['params']}
    drive = float(sat['Drive']['display'].split()[0])
    C('set_param', track='VOX CITY - calls', device='Saturator', param='Drive', display=str(drive + 1.5))


if __name__ == '__main__':
    main()
