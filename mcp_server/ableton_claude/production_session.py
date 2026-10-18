"""User-controlled musical milestones; applying tools never approves musical taste."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import threading
import uuid

STAGES = ('loop', 'groove', 'arrangement')
LABELS = {'loop': 'Loop', 'groove': 'Groove', 'arrangement': 'Arranjo'}
READ_COMMANDS = {'get_song', 'get_track', 'get_device', 'get_notes', 'browse', 'grooves',
                 'warp_markers', 'track_routing', 'device_inputs', 'record_status'}
TRACK_EDITS = {'load_device', 'set_param', 'set_device_on', 'set_track', 'set_send', 'set_clip',
               'add_notes', 'create_midi_clip', 'create_audio_clip', 'duplicate_clip', 'trim_clip',
               'fill_range', 'mute_clips_in_range', 'apply_groove', 'set_warp_markers'}


class ProductionSession:
    def __init__(self, data_dir, writer):
        self.path = Path(data_dir) / 'Production' / 'session.json'
        self.writer = writer
        self.lock = threading.RLock()
        self.value = {'active': False}
        try:
            saved = json.loads(self.path.read_text())
            if saved.get('active') and saved.get('stage') in (*STAGES, 'existing') and all(k in saved for k in
                    ('id', 'bars', 'start_bar', 'end_bar', 'beats_per_bar', 'tracks', 'revision', 'approvals', 'track_prefix')):
                saved.setdefault('mode', 'new')
                saved.setdefault('label', 'Ideia ' + saved['id'].upper())
                self.value = saved
                # Live has no reliable project identifier in our overview: rebind explicitly.
                self.value['needs_resume'] = True
                self.value['auditioned'] = False
        except (OSError, ValueError, AttributeError):
            pass

    def status(self):
        with self.lock:
            return json.loads(json.dumps(self.value))

    def projects(self):
        folder = self.path.parent / 'Projects'
        results = []
        paths = sorted(folder.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in paths[:100]:
            try:
                value = self._load_project(path)
                results.append({key: value.get(key) for key in ('id', 'label', 'mode', 'stage', 'updated_at', 'completed', 'goal')})
            except (OSError, ValueError, AttributeError):
                continue
        return results

    @staticmethod
    def _load_project(path):
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or value.get('stage') not in (*STAGES, 'existing') or not all(
                key in value for key in ('id', 'bars', 'tracks', 'start_bar', 'end_bar', 'beats_per_bar', 'revision', 'approvals', 'track_prefix')):
            raise ValueError('Este projeto salvo não contém as etapas necessárias para retomar.')
        return value

    def _archive(self):
        if self.value.get('active'):
            self.value['updated_at'] = datetime.now(timezone.utc).isoformat()
            self.writer(self.path.parent / 'Projects' / (self.value['id'] + '.json'), self.value)

    def _save(self):
        self._archive()
        self.writer(self.path, self.value)
        return self.status()

    def begin(self, song, bars=8, copy_confirmed=False, label=''):
        if not copy_confirmed:
            raise ValueError('Abra um set vazio ou uma cópia e confirme antes de iniciar uma ideia.')
        if bars not in (4, 8, 16):
            raise ValueError('Escolha um loop de 4, 8 ou 16 compassos.')
        numerator, denominator = map(int, song.get('signature', '4/4').split('/'))
        bpb = numerator * 4 / denominator
        if bpb <= 0:
            raise ValueError('A fórmula de compasso do projeto não é válida.')
        occupied = any(t.get('clips_active', 0) for t in song.get('tracks', []))
        start = math.ceil(float(song.get('song_length_beats', 0)) / bpb) + 9 if occupied else 1
        with self.lock:
            self.value = {'active': True, 'id': uuid.uuid4().hex, 'mode': 'new', 'stage': 'loop', 'bars': bars,
                          'start_bar': start, 'end_bar': start + bars, 'beats_per_bar': bpb,
                          'tracks': [], 'revision': 0, 'applied': False, 'auditioned': False,
                          'approvals': [], 'completed': False, 'needs_resume': False}
            self.value['label'] = self._label(label) or 'Ideia ' + self.value['id'][:6].upper()
            self.value['track_prefix'] = 'Ideia %s · ' % self.value['id'][:6].upper()
            return self._save()

    @staticmethod
    def _label(label):
        if not isinstance(label, str):
            raise ValueError('Informe um nome para o projeto.')
        return label.strip()[:100]

    def begin_existing(self, song, copy_confirmed=False, label='', goal='diagnosis'):
        if not copy_confirmed:
            raise ValueError('Abra uma cópia do projeto existente e confirme antes de continuar.')
        if goal not in {'diagnosis', 'groove', 'arrangement', 'mix'}:
            raise ValueError('Escolha diagnóstico, groove, arranjo ou mix.')
        if not song.get('tracks'):
            raise ValueError('Abra o projeto existente no Live antes de continuar.')
        numerator, denominator = map(int, song.get('signature', '4/4').split('/'))
        bpb = numerator * 4 / denominator
        end = max(2, math.ceil(float(song.get('song_length_beats', 0)) / bpb) + 1)
        with self.lock:
            self.value = {'active': True, 'id': uuid.uuid4().hex, 'mode': 'existing', 'stage': 'existing',
                          'label': self._label(label) or 'Projeto existente', 'goal': goal, 'bars': 8,
                          'start_bar': 1, 'end_bar': end, 'beats_per_bar': bpb, 'track_prefix': '',
                          'tracks': [t['name'] for t in song['tracks'][:12]], 'revision': 0,
                          'approvals': [], 'applied': True, 'auditioned': False, 'completed': False, 'needs_resume': False}
            return self._save()

    def candidate(self, project_id):
        if self.status().get('active'):
            raise ValueError('Guarde o projeto atual antes de retomar outro.')
        if not isinstance(project_id, str) or len(project_id) not in (6, 32) or any(c not in '0123456789abcdef' for c in project_id):
            raise ValueError('Selecione um projeto salvo válido.')
        value = self._load_project(self.path.parent / 'Projects' / (project_id + '.json'))
        if value['id'] != project_id:
            raise ValueError('A identificação do projeto salvo não corresponde à seleção.')
        return value

    def restore(self, candidate):
        with self.lock:
            self.value = dict(candidate, active=True, auditioned=False, needs_resume=False)
            return self._save()

    def resume(self):
        with self.lock:
            if not self.value.get("active"):
                raise ValueError("Não há uma ideia salva para retomar.")
            self.value['needs_resume'] = False
            self.value['auditioned'] = False
            return self._save()

    def end(self):
        with self.lock:
            self._archive()
            self.value = {'active': False}
            return self._save()

    def back(self):
        with self.lock:
            if not self.value.get("active") or self.value.get("needs_resume"):
                raise ValueError("Retome uma ideia antes de voltar uma etapa.")
            if self.value.get('mode') == 'existing':
                raise ValueError('Projetos existentes não precisam recomeçar pelas etapas do loop.')
            index = STAGES.index(self.value['stage'])
            if not index:
                raise ValueError('Você já está na etapa do loop.')
            self.value.update(stage=STAGES[index - 1], approvals=list(STAGES[:index - 1]),
                              auditioned=False, completed=False)
            return self._save()

    def prompt(self):
        state = self.status()
        if not state.get('active'):
            return ''
        if state.get('mode') == 'existing':
            return '\nEXISTING PROJECT WORKFLOW: ' + json.dumps(state, ensure_ascii=False) + '''
Continue the project currently open in Live, working on the user-confirmed copy. Do not rebuild it from scratch or require Loop/Groove milestone approval. Start with a concise read-only diagnosis of existing clips, devices, arrangement and relevant genre measurements; then propose one focused improvement for the user's chosen goal. Preserve the hook, musical identity, tempo and existing arrangement unless the user explicitly asks to change them. Reuse existing material before adding layers. All mutations still require proposal review. Explain what will change and where; after applying, invite listening and another focused iteration. A project created by this app is still an existing project when this mode is explicitly selected. Never claim the model saved or opened a Live set; the user opens the corresponding .als and saves through Live.
'''
        return '\nMUSICAL WORKFLOW (app-controlled, cannot be advanced by the model): ' + json.dumps(state, ensure_ascii=False) + """
Stay in the current stage. First build a small 4/8/16-bar idea, with one memorable motif and a coherent foundation. Loop: choose good sounds and a simple musical idea; no long arrangement, fills or mastering. Groove: develop the approved motif through kick/bass pocket, hats/percussion, velocity and subtle variation inside the SAME short interval. Arrangement: unfold the approved groove into sections, entries/exits and energy contrast, reusing the approved clips rather than recomposing the hook. When expanding from a scratch interval after existing material, archive the workshop loop muted so it does not become an extra section at the end.
Create separate tracks using track_prefix and exact names; only these workshop tracks may be edited. Existing material can be inspected and reused as inspiration, never overwritten. Place loops in start_bar..end_bar; length is in beats, not bars. Preserve the project's time signature and tempo. Discover instruments/samples before loading them. Build a playable candidate with reviewed tool calls, not just a textual plan. Batch independent reads into one model response. Once a candidate is applied, stop and invite the user to Ouvir and Aprovar the musical stage. Applying a proposal, text like 'yes', and listening are NOT milestone approvals; only the app's approval button advances the stage. Use no new model call to announce an approval. Don't expand to a full song before both Loop and Groove approvals. Never approve your own work.
"""

    def filter_tools(self, catalog):
        state = self.status()
        if state.get('active') and state.get('mode') != 'existing' and state['stage'] != 'arrangement':
            return [t for t in catalog if t['name'] not in {'genre_plan_structure', 'music_build_roll', 'mix_toward_genre', 'analyze_tension'}]
        return catalog

    def check(self, name, args, planned_tracks=()):
        state = self.status()
        if not state.get('active'):
            return
        if state.get('needs_resume'):
            raise ValueError('Retome a ideia no projeto correto antes de continuar.')
        if state.get('mode') == 'existing':
            return
        if name == 'ableton_batch':
            created = list(planned_tracks)
            for command in args.get('commands', []):
                self.check('ableton_command', command, created if command.get('cmd') == 'create_track' else ())
                if command.get('cmd') == 'create_track':
                    created.append(command['args']['name'])
            return
        if name == 'render_start':
            if state['stage'] != 'arrangement' and (args.get('start_bar') != state['start_bar'] or args.get('end_bar') != state['end_bar']):
                raise ValueError('Nesta etapa, renderize apenas o loop selecionado.')
            return
        if name != 'ableton_command':
            if name in {'mix_toward_genre', 'live_undo', 'revert_changes'}:
                raise ValueError('Nesta ideia, preserve o projeto: ajuste apenas as faixas do loop.')
            return
        cmd, values = args.get('cmd'), args.get('args') or {}
        if cmd in READ_COMMANDS:
            return
        if cmd == 'create_track':
            if not isinstance(values.get('name'), str) or not values['name'].startswith(state['track_prefix']) or values['name'] in state['tracks'] + list(planned_tracks) or len(state['tracks']) + len(planned_tracks) >= 12:
                raise ValueError('Crie até 12 faixas com o prefixo desta ideia, preservando as faixas originais.')
            return
        if cmd in {'transport', 'set_loop', 'record_status'}:
            return
        if cmd not in TRACK_EDITS or values.get('track') not in state['tracks'] + list(planned_tracks):
            raise ValueError('A proposta só pode editar as faixas criadas para esta ideia.')
        if cmd == 'set_track' and 'name' in values:
            raise ValueError('Mantenha os nomes das faixas desta ideia durante o processo.')
        if state['stage'] == 'arrangement':
            return
        start, end, bpb = state['start_bar'], state['end_bar'], state['beats_per_bar']
        def within(a, b):
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (a, b)) or not start <= a < b <= end:
                raise ValueError('Aprove o loop e o groove antes de expandir o arranjo. Use apenas o intervalo da ideia.')
        if cmd in {'create_midi_clip', 'create_audio_clip'}:
            at = values.get('bar') if 'bar' in values else self._bar(values.get('beat'), bpb)
            length = values.get('length')
            if not isinstance(length, (int, float)):
                raise ValueError('Informe a duração do clip em beats dentro do loop.')
            if not isinstance(at, (int, float)):
                raise ValueError('Informe a posição do clip em compassos ou beats.')
            within(at, at + length / bpb)
        elif cmd == 'duplicate_clip':
            raise ValueError('Use clips curtos com duração explícita antes de abrir o arranjo.')
        elif cmd in {'fill_range', 'mute_clips_in_range', 'apply_groove'}:
            within(values.get('start_bar', start), values.get('end_bar', end))
            if cmd == 'fill_range':
                within(values.get('src_start_bar'), values.get('src_end_bar'))
        elif cmd == 'trim_clip':
            boundary = values.get('end_bar') if 'end_bar' in values else self._bar(values.get('end_beat'), bpb)
            within(start, boundary)

    @staticmethod
    def _bar(beat, bpb):
        return beat / bpb + 1 if isinstance(beat, (int, float)) else None

    def observe(self, name, args, result):
        if not self.status().get('active') or (isinstance(result, dict) and 'error' in result):
            return
        if name == 'ableton_batch':
            for command, value in zip(args.get('commands', []), result if isinstance(result, list) else []):
                if value.get('ok'):
                    self.observe('ableton_command', command, value.get('result', {}))
            return
        if name != 'ableton_command' or args.get('cmd') in READ_COMMANDS | {'transport', 'set_loop'}:
            return
        with self.lock:
            if self.value.get('mode') == 'existing' and args.get('cmd') == 'set_track' and args.get('args', {}).get('name'):
                old, new = args['args'].get('track'), args['args']['name']
                self.value['tracks'] = [new if track == old else track for track in self.value['tracks']]
            if args.get('cmd') == 'create_track' and result.get('name') not in self.value['tracks']:
                self.value['tracks'].append(result['name'])
            self.value.update(revision=self.value['revision'] + 1, auditioned=False, completed=False)
            if args.get('cmd') in {'create_midi_clip', 'create_audio_clip', 'add_notes', 'fill_range'}:
                self.value['applied'] = True
            self._save()

    def fingerprint(self, connection):
        state = self.status()
        evidence, material, first, last = [], False, float('inf'), 0
        for name in state.get('tracks', [])[:12]:
            limit = 128 if state['stage'] == 'arrangement' else 32
            track = connection.call('ableton_command', {'cmd': 'get_track', 'args': {'track': name, 'max_clips': limit}})
            if track.get('n_clips', 0) > limit:
                raise ValueError('Esta ideia tem clips demais para verificar de uma vez. Simplifique as faixas antes de aprovar.')
            clips = []
            for clip in track.get('clips', [])[:limit]:
                in_range = clip.get('start', 0) < (state['end_bar'] - 1) * state['beats_per_bar'] and clip.get('end', 0) > (state['start_bar'] - 1) * state['beats_per_bar']
                if not track.get('mute') and not clip.get('muted') and (in_range or state['stage'] == 'arrangement'):
                    entry = dict(clip)
                    first, last = min(first, clip.get('start', 0)), max(last, clip.get('end', 0))
                    if clip.get('type') == 'midi':
                        entry['notes'] = connection.call('ableton_command', {'cmd': 'get_notes', 'args': {'track': name, 'clip': clip['i']}})
                        material = material or bool(entry['notes'])
                    else:
                        material = True
                    clips.append(entry)
            evidence.append({'track': name, 'volume': track.get('vol_db'), 'mute': track.get('mute'),
                             'devices': track.get('devices'), 'clips': clips})
        if not material:
            raise ValueError('Aplique primeiro uma proposta com material musical no intervalo desta ideia.')
        if state['stage'] == 'arrangement' and last - first < 2 * state['bars'] * state['beats_per_bar']:
            raise ValueError('Desenvolva o groove em seções antes de aprovar o arranjo; um loop sozinho ainda não é um arranjo.')
        return {'hash': hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest(),
                'start_bar': first / state['beats_per_bar'] + 1 if state['stage'] == 'arrangement' else state['start_bar'],
                'end_bar': last / state['beats_per_bar'] + 1 if state['stage'] == 'arrangement' else state['end_bar']}

    def audition(self, connection):
        with self.lock:
            if not self.value.get('active') or self.value.get('needs_resume'):
                raise ValueError('Inicie ou retome uma ideia antes de ouvir.')
            fingerprint = self.fingerprint(connection)
            connection.call('ableton_command', {'cmd': 'set_loop', 'args': {'on': True,
                            'start_bar': fingerprint['start_bar'], 'end_bar': fingerprint['end_bar']}})
            result = connection.call('ableton_command', {'cmd': 'transport', 'args': {'action': 'play', 'bar': fingerprint['start_bar']}})
            if not result.get('playing'):
                raise ValueError('O Live não iniciou a reprodução. Confira o dispositivo de áudio.')
            self.value.update(auditioned=True, fingerprint=fingerprint['hash'], audition_start_bar=fingerprint['start_bar'], audition_end_bar=fingerprint['end_bar'])
            return self._save()

    def approve(self, connection):
        with self.lock:
            if not self.value.get('active') or self.value.get('needs_resume') or not self.value.get('auditioned'):
                raise ValueError('Ouça o resultado desta etapa antes de aprovar e avançar.')
            if self.fingerprint(connection)['hash'] != self.value.get('fingerprint'):
                self.value['auditioned'] = False
                self._save()
                raise ValueError('O material mudou desde a reprodução. Ouça novamente antes de aprovar.')
            if self.value.get('mode') == 'existing':
                raise ValueError('Projetos existentes usam revisão de propostas, sem etapas obrigatórias de aprovação.')
            stage = self.value['stage']
            if stage not in self.value['approvals']:
                self.value['approvals'].append(stage)
            if stage == 'arrangement':
                self.value['completed'] = True
            else:
                self.value.update(stage=STAGES[STAGES.index(stage) + 1], auditioned=False)
            return self._save()
