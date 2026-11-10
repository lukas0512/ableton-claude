"""Human-readable previews and execution receipts derived from actual tool data."""

LABELS = {
    'quick_groove': 'Groove rápido no Live', 'quick_groove_remove': 'Remover groove rápido',
    'create_track': 'Criar faixa', 'create_midi_clip': 'Criar parte MIDI',
    'create_audio_clip': 'Adicionar áudio', 'set_track': 'Ajustar faixa',
    'set_tempo': 'Ajustar tempo', 'load_device': 'Carregar instrumento ou efeito',
    'set_param': 'Ajustar parâmetro', 'set_device_on': 'Ativar ou desativar efeito',
    'set_clip': 'Ajustar clip', 'duplicate_clip': 'Copiar clip',
    'fill_range': 'Desenvolver arranjo', 'trim_clip': 'Recortar clip',
    'mute_clips_in_range': 'Silenciar ou restaurar clips', 'set_cue': 'Marcar seção',
    'delete_track': 'Remover faixa', 'delete_clip': 'Remover clip',
    'delete_clips_in_range': 'Remover clips do intervalo',
    'set_track_input': 'Ajustar entrada', 'set_track_output': 'Ajustar saída',
    'set_device_input': 'Ajustar sidechain', 'set_send': 'Ajustar envio',
    'transport': 'Controlar reprodução', 'set_loop': 'Definir intervalo de escuta',
    'record_master': 'Gravar o master', 'render_start': 'Renderizar trecho',
    'groove_loop': 'Criar loop com o groove aprendido',
    'mix_toward_genre': 'Aproximar mix das referências',
    'live_undo': 'Desfazer no Live', 'revert_changes': 'Reverter ajustes',
}


def project_state(overview):
    """Compare observable project structure, excluding moving transport fields.

    Live exposes no set ID. This guards detectable changes, not project identity or
    edits to MIDI/device values absent from the overview.
    """
    if not isinstance(overview, dict) or 'error' in overview:
        raise ValueError('Não foi possível conferir o projeto antes de aplicar a proposta.')
    return {key: overview[key] for key in ('tempo', 'signature', 'tracks', 'returns', 'master', 'cues') if key in overview}


def actions(call):
    name, args = call['name'], call['args']
    if name == 'ableton_batch':
        return args['commands']
    if name == 'ableton_command':
        return [args]
    return [{'cmd': name, 'args': args}]


def preview(call):
    items = []
    for action in actions(call):
        cmd, args = action['cmd'], action.get('args') or {}
        details = []
        for field, label in [('track', 'Faixa'), ('name', 'Nome'), ('bar', 'Compasso'),
                             ('beat', 'Beat'), ('start_bar', 'Início'), ('end_bar', 'Fim'),
                             ('bpm', 'BPM'), ('volume_db', 'Volume (dB)'), ('pan', 'Pan'),
                             ('mute', 'Mute'), ('solo', 'Solo'), ('device', 'Dispositivo'),
                             ('param', 'Parâmetro'), ('value', 'Valor'), ('display', 'Valor exibido'),
                             ('db', 'dB'), ('query', 'Busca'), ('path', 'Arquivo'),
                             ('length', 'Duração (beats)'), ('clip', 'Clip'), ('action', 'Ação')]:
            if field in args:
                details.append(f'{label}: {args[field]}')
        if isinstance(args.get('notes'), list):
            details.append(f"{len(args['notes'])} notas MIDI")
        items.append({'title': LABELS.get(cmd, f'Ação: {cmd}'), 'detail': ' · '.join(details)})
    return items


def failed(value):
    if isinstance(value, dict):
        return 'error' in value or value.get('ok') is False
    return isinstance(value, list) and any(failed(item) for item in value)


def receipt(call, value, skipped=False):
    """A success is execution evidence, never proof of musical quality."""
    descriptions = preview(call)
    values = value if call['name'] == 'ableton_batch' and isinstance(value, list) else [value]
    items = []
    for index, description in enumerate(descriptions):
        result = value if skipped else values[index] if index < len(values) else {'error': 'Resultado não informado.'}
        status = 'skipped' if skipped or (isinstance(result, dict) and result.get('skipped')) else 'failed' if failed(result) else 'applied'
        item = dict(description, status=status)
        if isinstance(result, dict):
            if result.get('error'):
                item['error'] = str(result['error'])
            change_id = result.get('change_id')
            if change_id is None and isinstance(result.get('result'), dict):
                change_id = result['result'].get('change_id')
            if change_id is not None:
                item['change_id'] = change_id
        items.append(item)
    return items
