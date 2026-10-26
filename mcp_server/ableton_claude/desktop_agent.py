"""In-app producer chat using the app's MCP session and authenticated model access.

Read tools run automatically. Changes are queued for explicit review in the app.
Credentials stay in memory for a request and are never included in saved settings.
"""
import json
import threading

import httpx
from .storage import json_safe
from . import producer_intelligence as intelligence
from . import proposals

READ_TOOLS = {"producer_brief", "ableton_status", "list_genres", "genre_knowledge", "genre_plan_structure",
              "analyze_audio", "analyze_reference", "compare_to_genre", "analyze_timbre", "analyze_tension",
              "analyze_sample", "analyze_bassline", "music_chords", "music_progression", "music_call_and_response",
              "production_intent", "production_review", "music_drum_pattern", "music_pocket_sketch", "music_club_motif", "remix_plan", "music_build_roll", "library_search", "library_midi", "change_log",
              "producer_tools", "genre_principles", "validate_against_genre", "compare_to_reference",
              "compare_by_ear", "listen", "render_wait", "extract_groove", "heard_midi", "find_samples",
              "split_elements_status", "solo_levels_status", "taste_report"}
READ_COMMANDS = {"get_song", "get_track", "get_device", "get_notes", "browse", "grooves",
                 "warp_markers", "track_routing", "device_inputs", "record_status"}
EXCLUDED = {"study_references", "study_status", "learn_genres", "learn_genres_status", "reference_study"}


def read_only(name, args):
    if name == "split_elements":      # a file split writes stems, never the project
        return not args.get("track")
    return name in READ_TOOLS or (name == "ableton_command" and args.get("cmd") in READ_COMMANDS)


def stream_chatgpt(key, payload, transport=None, on_delta=None):
    """Plan requests are SSE only; never treat a partial response as success."""
    errors = {
        "subscription_sharing_usage_limit_exceeded": "O limite de uso do plano ou deste app foi atingido. Gerencie o uso nas configurações do ChatGPT.",
        "subscription_sharing_usage_unavailable": "O uso do plano não está disponível para este app. Confira o acesso nas configurações do ChatGPT.",
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(90, connect=15), transport=transport) as client:
            with client.stream("POST", "https://api.openai.com/v1/responses", headers={"Authorization": "Bearer " + key}, json=payload) as response:
                if response.status_code in (401, 403):
                    raise ValueError("Sua conta precisa ser reconectada. Continue com ChatGPT nas configurações.")
                if response.status_code == 429:
                    raise ValueError(errors["subscription_sharing_usage_limit_exceeded"])
                if response.is_error:
                    raise ValueError("O ChatGPT não aceitou este pedido (HTTP %s). Confira o modelo e o acesso ao plano." % response.status_code)
                data, completed_items = [], {}
                for line in response.iter_lines():
                    if line.startswith("data:"):
                        data.append(line[5:].lstrip())
                    elif not line and data:
                        raw, data = "\n".join(data), []
                        if raw == "[DONE]":
                            continue
                        event = json.loads(raw)
                        kind = event.get("type")
                        if kind == "response.output_item.done":
                            index, item = event.get('output_index'), event.get('item')
                            if isinstance(index, int) and 0 <= index < 128 and isinstance(item, dict):
                                completed_items[index] = item
                        if kind == "response.output_text.delta" and on_delta:
                            on_delta(event.get("delta", ""))
                        if kind in ("response.failed", "response.incomplete", "error"):
                            code = event.get("code") or ((event.get("response") or {}).get("error") or {}).get("code")
                            raise ValueError(errors.get(code, "A resposta foi interrompida. Faça um pedido menor ou tente novamente."))
                        if kind == "response.completed":
                            result = event.get("response", {})
                            if result.get("status") != "completed":
                                raise ValueError("A resposta não foi concluída.")
                            # Plan streams may omit the output from the terminal envelope.
                            # Final item events also carry the complete encrypted reasoning.
                            output = dict(enumerate(result.get('output') or []))
                            output.update(completed_items)
                            result['output'] = [output[i] for i in sorted(output)]
                            return result
                raise ValueError("A conexão terminou antes da resposta completa. Tente novamente.")
    except httpx.HTTPError:
        raise ValueError("A conexão com o ChatGPT foi interrompida. Confira a internet e tente novamente.") from None


def api_request(provider, key, endpoint, payload=None, transport=None, on_delta=None):
    if provider not in ("anthropic", "openai", "chatgpt"):
        raise ValueError("Escolha Claude ou OpenAI.")
    if provider == "chatgpt" and payload is not None:
        return stream_chatgpt(key, payload, transport, on_delta)
    base = "https://api.anthropic.com/v1" if provider == "anthropic" else "https://api.openai.com/v1"
    headers = ({"x-api-key": key, "anthropic-version": "2023-06-01"} if provider == "anthropic"
               else {"Authorization": "Bearer " + key})
    try:
        with httpx.Client(timeout=httpx.Timeout(90, connect=15), transport=transport) as client:
            response = (client.get(base + endpoint, headers=headers) if payload is None else
                        client.post(base + endpoint, headers=headers, json=payload))
        if response.status_code in (401, 403):
            raise ValueError("A chave não tem acesso. Confira sua chave e as permissões da API.")
        if response.status_code == 429:
            raise ValueError("O provedor informou limite de uso ou saldo. Confira sua conta de API.")
        if response.is_error:
            raise ValueError("O provedor não aceitou este pedido (HTTP %s). Confira o modelo e tente novamente." % response.status_code)
        return response.json()
    except httpx.HTTPError:
        raise ValueError("Não foi possível alcançar o provedor. Confira sua conexão e tente novamente.") from None


def available_models(provider, key, transport=None):
    result = api_request(provider, key, "/models", transport=transport)
    models = result.get("data", [])
    if provider == "openai":
        models = [m for m in models if m.get("id", "").startswith("gpt-") and
                  not any(s in m["id"] for s in ("audio", "realtime", "image", "transcribe", "tts", "codex"))]
    return [{"id": m["id"], "name": m.get("display_name", m["id"])} for m in models[:100]]


class ProducerAgent:
    def __init__(self, connection, transport=None, production=None):
        self.connection = connection
        self.production = production
        self.transport = transport
        self.messages = []
        self.events = []
        self.pending = []
        self.state = "idle"
        self.error = None
        self.partial = ""
        self._history = []
        self._provider_model = None
        self._lock = threading.Lock()
        self._brief = None
        self._groups = set()
        self._results = {}
        self._next_result = 0
        self._turn_starts = []
        self._memory = []
        self._history_pruned = False
        self.efficiency = {}
        self.execution = []
        self._proposal_state = None

    def status(self):
        with self._lock:
            return {"state": self.state, "messages": list(self.messages), "events": self.events[-6:],
                    "pending": [dict({k: v for k, v in call.items() if k != "raw"}, preview=proposals.preview(call)) for call in self.pending],
                    "execution": list(self.execution),
                    "error": self.error, "partial": self.partial, "efficiency": dict(self.efficiency)}

    def start(self, text, provider, model, key, genre, approve=None):
        if not key or not model:
            raise ValueError("Conecte seu assistente nas configurações antes de enviar uma mensagem.")
        with self._lock:
            if self.state == "running":
                raise ValueError("O produtor está trabalhando. Espere a resposta antes de enviar outro pedido.")
            if self.pending and approve is None:
                raise ValueError("Aplique ou descarte a proposta atual antes de continuar.")
            if approve is not None and not self.pending:
                raise ValueError("Não há uma proposta pendente.")
            if approve is not None and self._provider_model != (provider, model):
                raise ValueError("Use o mesmo assistente da proposta ou inicie uma nova conversa.")
            if self._provider_model != (provider, model):
                self._history = []
                self._turn_starts = []
                self._memory = []
                self._history_pruned = False
                self._results = {}
                self._provider_model = (provider, model)
            if text:
                if len(text) > 8000:
                    raise ValueError("Reduza sua mensagem para até 8.000 caracteres.")
                self.messages.append({"role": "user", "text": text})
            self.state, self.error = "running", None
            self.partial = ""
        threading.Thread(target=self._work, args=(text, provider, model, key, genre, approve),
                         name="producer-agent", daemon=True).start()
        return self.status()

    def _event(self, text):
        with self._lock:
            self.events.append(text)

    def _delta(self, text):
        with self._lock:
            self.partial += text
            if len(self.partial) > 64000:
                raise ValueError("A resposta ficou extensa demais. Divida o pedido em etapas menores.")

    def _execute(self, call, approved=True):
        if not approved:
            return {"error": "O produtor descartou a proposta. Não aplique essas mudanças."}
        name, args = call["name"], call["args"]
        if self.production:
            try:
                self.production.check(name, args)
            except ValueError as error:
                return {'error': str(error)}
        if name == "producer_tools":
            requested = args.get("groups", [])
            if not isinstance(requested, list) or any(g not in intelligence.GROUPS for g in requested):
                return {"error": "Escolha grupos de ferramentas válidos."}
            self._groups.update(requested)
            available = intelligence.select_tools(self.connection.tools, self._groups)
            if self.production:
                available = self.production.filter_tools(available)
            return {"available_tools": [t["name"] for t in available]}
        # Python evaluation is intentionally never available to a model.
        commands = args.get("commands", []) if name == "ableton_batch" else [args] if name == "ableton_command" else []
        if any(command.get("cmd") == "api_probe" for command in commands):
            return {"error": "Use as ferramentas específicas do Live para esta operação."}
        if name == 'ableton_batch':
            if not isinstance(commands, list) or not 1 <= len(commands) <= 32 or any(
                    not isinstance(command, dict) or not isinstance(command.get('cmd'), str) or
                    not isinstance(command.get('args', {}), dict) for command in commands):
                return {'error': 'Divida a proposta em grupos de até 32 comandos válidos.'}
            # The bridge batch continues after errors. Desktop proposals instead run
            # each reviewed command in order and stop at the first failed operation.
            results, stopped = [], False
            for command in commands:
                if stopped:
                    results.append({'ok': False, 'skipped': True, 'error': 'Uma ação anterior falhou; esta mudança não foi aplicada.'})
                    continue
                value = self._execute({'name': 'ableton_command', 'args': command})
                stopped = proposals.failed(value)
                results.append({'ok': False, 'error': str(value.get('error', 'A ação falhou.'))} if stopped and isinstance(value, dict)
                               else {'ok': not stopped, 'result': value})
            return results
        if name == "render_start" or any(command.get("cmd") == "record_master" for command in commands):
            from . import genres
            if any(job["state"] in ("queued", "running") for job in genres._JOBS.values()):
                return {"error": "Espere o aprendizado terminar antes de renderizar."}
        if name in {"analyze_audio", "analyze_reference", "analyze_timbre", "analyze_tension", "compare_to_genre", "listen", "production_review", "remix_plan", "compare_by_ear",
                    "find_samples", "analyze_sample", "analyze_bassline", "extract_groove", "heard_midi", "validate_against_genre", "compare_to_reference",
                    "split_elements"}:
            from . import client
            try:
                if client.call("record_status", timeout=2).get("state") in ("recording", "finalizing"):
                    return {"error": "Espere o render terminar antes de analisar áudio."}
            except client.BridgeError:
                pass
        self._event("Consultando o projeto" if read_only(name, args) else proposals.preview(call)[0]['title'])
        try:
            result = self.connection.call(name, args)
            if self.production:
                self.production.observe(name, args, result)
            return result
        except Exception as e:
            return {"error": str(e)}

    def _tool_results(self, calls, provider, approved=True):
        results = []
        failed = False
        for call in calls:
            skipped = failed and not read_only(call['name'], call['args'])
            value = ({"error": "Uma ação anterior falhou; esta mudança não foi aplicada."}
                     if skipped else self._execute(call, approved))
            is_error = proposals.failed(value)
            if approved and not read_only(call['name'], call['args']):
                with self._lock:
                    self.execution.extend(proposals.receipt(call, value, skipped))
            if is_error and not read_only(call["name"], call["args"]):
                failed = True
            value = json_safe(value)
            if call['name'].startswith('music_') or call['name'] in {'library_midi', 'heard_midi', 'analyze_bassline'}:
                self._next_result += 1
                ref = 'material-%d' % self._next_result
                self._results[ref] = value
                if len(self._results) > 128:
                    del self._results[next(iter(self._results))]
                content = json.dumps({"result_ref": ref, "data": json.loads(intelligence.compact(value, 6500)),
                    "reuse": 'Use {"$result":"' + ref + '"} for complete data, or add "field":"notes" (or the returned part name) to reuse a field locally; nested parts use main.kick or stripped.bass.'}, ensure_ascii=False)
            else:
                content = intelligence.compact(value, 10000)
            if provider == "anthropic":
                results.append({"type": "tool_result", "tool_use_id": call["id"], "content": content,
                                "is_error": is_error})
            else:
                results.append({"type": "function_call_output", "call_id": call["id"], "output": content})
        return results

    def _append_results(self, results, provider):
        if provider == "anthropic":
            self._history.append({"role": "user", "content": results})
        else:
            self._history.extend(results)

    def _resolve_material(self, value):
        if isinstance(value, dict):
            if set(value) in ({'$result'}, {'$result', 'field'}):
                ref = value['$result']
                if not isinstance(ref, str) or ref not in self._results:
                    raise ValueError("O material musical expirou. Gere novamente antes de aplicar.")
                result = self._results[ref]
                if 'field' in value:
                    field = value['field']
                    if not isinstance(field, str) or not field:
                        raise ValueError("O campo solicitado não existe no material musical.")
                    # Prefer an exact key for compatibility; otherwise traverse dictionaries only.
                    if isinstance(result, dict) and field in result:
                        return result[field]
                    for key in field.split('.'):
                        if not isinstance(result, dict) or key not in result:
                            raise ValueError("O campo solicitado não existe no material musical.")
                        result = result[key]
                    return result
                return result
            return {k: self._resolve_material(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_material(v) for v in value]
        return value

    def _prepare_turn(self, text):
        # Prune only complete older user turns. Pending call/result pairs and encrypted
        # reasoning in the retained turns stay intact; pruning never happens on approval.
        if len(json.dumps(self._history, ensure_ascii=False)) > 24000 and len(self._turn_starts) > 2:
            cut = self._turn_starts[-2]
            self._history = self._history[cut:]
            self._turn_starts = [i - cut for i in self._turn_starts if i >= cut]
            self._history_pruned = True
            self._event("Contexto reduzido; os pedidos recentes e o projeto atual foram preservados")
        self._turn_starts.append(len(self._history))
        self._memory.append(text[:800])
        self._memory = self._memory[-8:]
        self._history.append({"role": "user", "content": text})

    def _record_usage(self, response, context_chars, tool_count):
        usage = response.get('usage') or {}
        with self._lock:
            self.efficiency['requests'] = self.efficiency.get('requests', 0) + 1
            for name in ('input_tokens', 'output_tokens'):
                if isinstance(usage.get(name), int):
                    self.efficiency[name] = self.efficiency.get(name, 0) + usage[name]
            details = usage.get('input_tokens_details') or {}
            if isinstance(details.get('cached_tokens'), int):
                self.efficiency['cached_tokens'] = self.efficiency.get('cached_tokens', 0) + details['cached_tokens']
            self.efficiency.update(context_characters=context_chars, available_tools=tool_count)

    def _work(self, text, provider, model, key, genre, approve):
        history_checkpoint = None
        try:
            if self._brief is None:
                self._brief = str(self.connection.call("producer_brief"))
            if approve is None:
                self._groups = intelligence.task_groups(text)
                with self._lock:
                    self.efficiency = {}
            if approve is not None:
                if approve and self._proposal_state is not None:
                    current = proposals.project_state(self.connection.call('ableton_status'))
                    if current != self._proposal_state:
                        raise ValueError('O projeto mudou desde a proposta. Descarte-a e peça uma nova avaliação antes de aplicar.')
                with self._lock:
                    self.execution = []
                self._append_results(self._tool_results(self.pending, provider, approved=approve), provider)
                with self._lock:
                    self.pending = []
                    self._proposal_state = None
            elif text:
                self._prepare_turn(text)
            overview = self.connection.call("ableton_status")
            genre = genre or intelligence.requested_genre(text)
            profile = self.connection.call("genre_knowledge", {"genre": genre}) if genre and any(t['name'] == 'genre_knowledge' for t in self.connection.tools) else {"note": "No selected learned profile available."}
            system = intelligence.system_prompt(genre, json_safe(overview), json_safe(profile), self._brief, self._groups,
                                                request=text or (self._memory[-1] if self._memory else ""))
            if self.execution:
                system += '\nLast execution receipt (tool acknowledgments, NOT musical verification): ' + intelligence.compact(self.execution, 5000)
            if self.production:
                flow = self.production.status()
                if flow.get('active'):
                    if flow.get('needs_resume'):
                        raise ValueError('Confirme o projeto e retome a ideia antes de continuar no chat.')
                    if flow.get('mode') != 'existing':
                        self._groups.update({'compose', 'verify', 'groove'} if flow['stage'] != 'arrangement' else {'arrange', 'compose', 'verify'})
                system += self.production.prompt()
            if self._history_pruned:
                system += '\nEarlier user request excerpts (historical, may be superseded; never evidence of current project): ' + intelligence.compact(self._memory[:-len(self._turn_starts)], 5000)
            for _ in range(8):
                catalog = intelligence.select_tools([t for t in self.connection.tools if t['name'] not in EXCLUDED], self._groups)
                if self.production:
                    catalog = self.production.filter_tools(catalog)
                context_chars = len(system) + len(json.dumps(self._history, ensure_ascii=False)) + len(json.dumps(catalog, ensure_ascii=False))
                if context_chars > 120000:
                    raise ValueError("Este pedido acumulou contexto demais. Divida a produção em etapas ou inicie uma nova conversa.")
                self._event("O produtor está preparando a resposta")
                history_checkpoint = len(self._history)
                if provider == "anthropic":
                    tools = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in catalog]
                    response = api_request(provider, key, "/messages", {
                        "model": model, "max_tokens": 4096, "system": system, "messages": self._history,
                        "tools": tools}, transport=self.transport)
                    blocks = response.get("content", [])
                    self._history.append({"role": "assistant", "content": blocks})
                    answer = "\n".join(b["text"] for b in blocks if b.get("type") == "text")
                    calls = [{"id": b["id"], "name": b["name"], "args": b["input"]}
                             for b in blocks if b.get("type") == "tool_use"]
                else:
                    tools = [{"type": "function", "name": t["name"], "description": t["description"],
                              "parameters": t["parameters"], "strict": False} for t in catalog]
                    payload = {
                        "model": model, "max_output_tokens": 4096, "instructions": system,
                        "input": self._history, "tools": tools, "store": False,
                        "include": ["reasoning.encrypted_content"]}
                    if provider == "chatgpt":
                        payload.pop("max_output_tokens")
                        payload["stream"] = True
                        payload["tools"] = [{"type": "namespace", "name": "ableton", "description": "Produção musical no projeto Live e medições locais.", "tools": tools}]
                    response = api_request(provider, key, "/responses", payload, transport=self.transport, on_delta=self._delta)
                    blocks = response.get("output", [])
                    self._history.extend(blocks)
                    answer = "\n".join(c["text"] for b in blocks if b.get("type") == "message"
                                       for c in b.get("content", []) if c.get("type") == "output_text")
                    refusals = [c.get('refusal', '') for b in blocks if b.get('type') == 'message'
                                for c in b.get('content', []) if c.get('type') == 'refusal']
                    if refusals and not answer:
                        answer = '\n'.join(refusals)
                    calls = [{"id": b["call_id"], "name": b["name"], "args": json.loads(b["arguments"])}
                             for b in blocks if b.get("type") == "function_call"]
                self._record_usage(response, context_chars, len(catalog))
                if len(calls) > 12:
                    raise ValueError("A proposta ficou grande demais. Peça uma etapa menor da produção.")
                allowed = {t['name'] for t in catalog}
                planned_tracks = []
                for call in calls:
                    if call['name'] not in allowed or not isinstance(call['args'], dict):
                        raise ValueError("O assistente solicitou uma ferramenta indisponível. Tente novamente com uma etapa menor.")
                    call['args'] = self._resolve_material(call['args'])
                    if self.production:
                        self.production.check(call['name'], call['args'], planned_tracks)
                        if call['name'] == 'ableton_command' and call['args'].get('cmd') == 'create_track':
                            planned_tracks.append(call['args']['args']['name'])
                    if call['name'] == 'ableton_batch':
                        commands = call['args'].get('commands')
                        if not isinstance(commands, list) or not 1 <= len(commands) <= 32 or any(
                                not isinstance(c, dict) or not isinstance(c.get('cmd'), str) or
                                not isinstance(c.get('args', {}), dict) for c in commands):
                            raise ValueError("Divida a proposta em grupos de até 32 comandos válidos.")
                changes = any(not read_only(c['name'], c['args']) for c in calls)
                # Keep the response checkpoint until the review snapshot succeeds.
                # A lost bridge here must not leave unmatched tool calls in history.
                baseline = proposals.project_state(self.connection.call('ableton_status')) if changes else None
                history_checkpoint = None
                if answer:
                    with self._lock:
                        self.messages.append({"role": "assistant", "text": answer})
                with self._lock:
                    self.partial = ""
                if not calls:
                    if not answer:
                        raise ValueError("O assistente encerrou sem uma resposta utilizável. Tente novamente ou escolha outro modelo na conexão.")
                    with self._lock:
                        self.state = "idle"
                    return
                if changes:
                    with self._lock:
                        self.pending = calls
                        self._proposal_state = baseline
                        self.state = "review"
                    return
                self._append_results(self._tool_results(calls, provider), provider)
            raise ValueError("O produtor chegou ao limite de etapas deste pedido. Faça um pedido menor ou inicie uma nova conversa.")
        except Exception as e:
            if history_checkpoint is not None:
                del self._history[history_checkpoint:]
            with self._lock:
                self.error = str(e).replace(key, "[chave protegida]") if key else str(e)
                self.state = "error"

    def reset(self):
        with self._lock:
            if self.state == "running":
                raise ValueError("Espere a operação atual terminar.")
            self._history, self.messages, self.events, self.pending = [], [], [], []
            self.state, self.error = "idle", None
            self.partial = ""
            self._turn_starts, self._memory, self._results = [], [], {}
            self._history_pruned = False
            self.efficiency = {}
            self.execution = []
            self._proposal_state = None
        return self.status()
