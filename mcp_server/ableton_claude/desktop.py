"""Desktop JSON-lines API and standalone MCP entry point for the macOS bundle."""
import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

from . import client, genres, knowledge
from .storage import DATA_DIR, json_safe

_SETTINGS_LOCK = threading.RLock()
_MCP = None
_AGENT = None
_AUTH = None
_PRODUCTION = None


def chatgpt_auth():
    global _AUTH
    with _SETTINGS_LOCK:
        if _AUTH is None:
            from .desktop_auth import ChatGPTAuth
            _AUTH = ChatGPTAuth(DATA_DIR)
        return _AUTH


def mcp_connection():
    global _MCP
    with _SETTINGS_LOCK:
        if _MCP is None:
            from .desktop_mcp import LocalMCP
            _MCP = LocalMCP(backend_command(), DATA_DIR)
        _MCP.start()
        return _MCP


def producer_agent():
    global _AGENT
    with _SETTINGS_LOCK:
        if _AGENT is None:
            from .desktop_agent import ProducerAgent
            _AGENT = ProducerAgent(mcp_connection(), production=production_session())
        return _AGENT


def production_session():
    global _PRODUCTION
    with _SETTINGS_LOCK:
        if _PRODUCTION is None:
            from .production_session import ProductionSession
            _PRODUCTION = ProductionSession(DATA_DIR, write_json)
        return _PRODUCTION


def update_settings(values):
    with _SETTINGS_LOCK:
        settings = load_settings()
        settings.update(values)
        write_json(Path(DATA_DIR) / "app.json", settings)
        return settings


def detect_library(home=None):
    home = Path(home or Path.home())
    configs = list((home / "Library" / "Preferences" / "Ableton").glob("Live */Library.cfg"))
    for path in sorted(configs, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            project = ET.parse(path).find(".//UserLibrary/LibraryProject")
            root = project.find("ProjectPath").get("Value")
            name = project.find("ProjectName").get("Value", "User Library")
            candidate = Path(root) / name
            if candidate.is_dir():
                return str(candidate)
        except (OSError, ET.ParseError, AttributeError, TypeError):
            continue
    return str(home / "Music" / "Ableton" / "User Library")


def preview_genres(folder):
    from . import study
    root, folders = genres.discover(folder)
    entries = []
    for name, path in folders:
        files = study.audio_files(path)
        entries.append({"genre": name, "files": len(files), "examples": [Path(p).name for p in files[:4]],
                        "folder": path})
    return {"folder": root, "genres": entries, "total_files": sum(g["files"] for g in entries)}


def prepare_genre(name, files):
    from . import references
    name = name.strip()
    if not name or any(c in name for c in '/\\:\n\r\x00') or name in (".", "..") or not knowledge.key_of(name):
        raise ValueError("Dê um nome ao gênero, sem caracteres de caminho.")
    sources = [Path(p).expanduser().resolve() for p in files]
    if not sources:
        raise ValueError("Adicione pelo menos uma referência de áudio; recomendamos 3 a 5 faixas.")
    for p in sources:
        if not p.is_file() or not str(p).lower().endswith(references.AUDIO_EXT):
            raise ValueError("Referência de áudio indisponível: %s" % p.name)
    root = Path(DATA_DIR) / "Genre References"
    root.mkdir(parents=True, exist_ok=True)
    dest = root / name
    for folder in root.iterdir():
        if folder.is_dir() and knowledge.key_of(folder.name) == knowledge.key_of(name):
            dest = folder
            break
    dest.mkdir(exist_ok=True)
    import hashlib
    for p in sources:
        link = dest / p.name
        if link.exists() and link.resolve() == p:
            continue
        if os.path.lexists(link):
            link = dest / (p.stem + "-" + hashlib.sha256(str(p).encode()).hexdigest()[:8] + p.suffix)
        if not os.path.lexists(link):
            link.symlink_to(p)
    update_settings({"genre_source": str(root)})
    return preview_genres(str(root))


def resources():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parents[1]
    return Path(__file__).resolve().parents[2]


def backend_command():
    if getattr(sys, "frozen", False):
        return {"command": sys.executable, "args": ["--mcp"]}
    return {"command": sys.executable, "args": ["-m", "ableton_claude.desktop", "--mcp"]}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def backup(path):
    path = Path(path)
    if not path.exists():
        return None
    dest = Path(DATA_DIR) / "Backups" / (path.name + "." + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir():
        shutil.copytree(path, dest)
    else:
        shutil.copy2(path, dest)
    return str(dest)


def load_settings():
    path = Path(DATA_DIR) / "app.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError("app.json must be an object")
    return value


def install_bridge(library):
    root = Path(library).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Selecione a pasta User Library existente do Ableton.")
    source = resources() / "ClaudeBridge"
    if not source.is_dir():
        source = resources() / "remote_script" / "ClaudeBridge"
    if not (source / "__init__.py").is_file() or not (source / "handlers.py").is_file():
        raise FileNotFoundError("ClaudeBridge não foi incluído no app.")
    target = root / "Remote Scripts" / "ClaudeBridge"
    saved = backup(target)
    target.mkdir(parents=True, exist_ok=True)
    for name in ("__init__.py", "handlers.py"):
        shutil.copy2(source / name, target / name)
    # Compiled files from a previous Live version must not shadow the new script.
    if (target / "__pycache__").exists():
        shutil.rmtree(target / "__pycache__")
    update_settings({"user_library": str(root)})
    activated = False
    try:
        if root == Path(detect_library()).resolve():
            activated = bool(client.call("reload", timeout=3).get("reloaded"))
    except client.BridgeError:
        pass
    return {"message": ("Ponte atualizada e conexão recarregada. Você pode continuar." if activated else
                        "Ponte instalada. Selecione ClaudeBridge uma vez em Settings → Link, Tempo & MIDI → Control Surface. Input e Output: None. O app detecta a conexão automaticamente."),
            "installed": str(target), "backup": saved, "activated": activated}


CLAUDE_CONFIG = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"


def claude_status(path=None, apps=None):
    """Whether Claude Desktop is installed and points at this backend."""
    path = Path(path or CLAUDE_CONFIG)
    apps = apps if apps is not None else [Path("/Applications/Claude.app"), Path.home() / "Applications" / "Claude.app"]
    configured = False
    try:
        with path.open(encoding="utf-8") as f:
            entry = json.load(f).get("mcpServers", {}).get("ableton-claude")
        configured = isinstance(entry, dict) and entry.get("command") == backend_command()["command"]
    except (OSError, ValueError, AttributeError):
        pass
    return {"installed": any(Path(a).is_dir() for a in apps), "configured": configured}


def configure_claude(path=None):
    path = Path(path or CLAUDE_CONFIG)
    config = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            config = json.load(f)
    if not isinstance(config, dict) or not isinstance(config.get("mcpServers", {}), dict):
        raise ValueError("Configuração do Claude inválida; o arquivo foi preservado.")
    saved = backup(path)
    config.setdefault("mcpServers", {})["ableton-claude"] = backend_command()
    write_json(path, config)
    return {"message": "Conector configurado. Encerre e reabra o Claude Desktop para carregar as ferramentas.",
            "config": str(path), "backup": saved}


def index_samples(folders):
    """Index the user's sample folders so the AI's library_search/find_samples see them."""
    from . import library
    roots = [str(Path(f).expanduser()) for f in folders if Path(f).expanduser().is_dir()]
    if not roots:
        raise ValueError("Escolha uma pasta de samples existente.")
    idx = library.build_index(roots)
    if not idx["n"]:
        raise ValueError("Nenhum arquivo de áudio encontrado nessas pastas.")
    update_settings({"sample_folders": roots, "sample_count": idx["n"]})
    return {"message": "%d samples indexados. No Claude, peça por exemplo: \"procure um hat crocante nos meus samples\"." % idx["n"],
            "n": idx["n"], "roots": roots}


def bridge_status():
    try:
        result = client.call("get_song", timeout=2)
        return {"connected": True, "tempo": result.get("tempo"),
                "tracks": len(result.get("tracks", [])), "song": result}
    except (client.BridgeError, ValueError, KeyError):
        return {"connected": False}


def dispatch(method, params):
    if method == "snapshot":
        settings = load_settings()
        bridge = bridge_status()
        render = {}
        if bridge["connected"]:
            try:
                render = client.call("record_status", timeout=2)
            except client.BridgeError:
                pass
        return {"data_dir": DATA_DIR, "genres": knowledge.trained_genres(),
                "context": knowledge.genre_context(), "bridge": bridge, "render": render,
                "job": genres.status(params["folder"]) if params.get("folder") else None,
                "user_library": settings.get("user_library", detect_library()),
                "last_folder": settings.get("genre_source", ""),
                "settings": settings, "claude": claude_status(), "connection": mcp_connection().status(), "chat": producer_agent().status(),
                "auth": chatgpt_auth().status(), "production": production_session().status(), "production_projects": production_session().projects(),
                "mcp": {"mcpServers": {"ableton-claude": backend_command()}},
                "codex": '[mcp_servers.ableton-claude]\ncommand = ' + json.dumps(backend_command()["command"]) + '\nargs = ["--mcp"]\n'}
    if method.startswith('production_'):
        agent_state = producer_agent().status()
        if agent_state['state'] == 'running' or agent_state['pending']:
            raise ValueError('Termine ou descarte a proposta atual antes de mudar a etapa musical.')
        if method == 'production_end':
            result = production_session().end()
            producer_agent().reset()
            return result
        if client.call('record_status', timeout=2).get('state') in ('recording', 'finalizing'):
            raise ValueError('Espere o render terminar antes de mudar a etapa musical.')
        flow = production_session()
        if method in ('production_begin', 'production_existing'):
            if flow.status().get('active'):
                raise ValueError('Encerre a ideia atual antes de começar outra.')
            song = mcp_connection().call('ableton_status')
            result = (flow.begin(song, params.get('bars', 8), params.get('copy_confirmed') is True, params.get('label', ''))
                      if method == 'production_begin' else flow.begin_existing(song, params.get('copy_confirmed') is True, params.get('label', ''), params.get('goal', 'diagnosis')))
            producer_agent().reset()
            return result
        if method in ('production_resume', 'production_restore'):
            if params.get('project_confirmed') is not True:
                raise ValueError('Confirme que o projeto correto está aberto para retomar.')
            candidate = flow.candidate(params.get('project_id')) if method == 'production_restore' else flow.status()
            for track in candidate.get('tracks', []):
                mcp_connection().call('ableton_command', {'cmd': 'get_track', 'args': {'track': track, 'clips': False}})
            result = flow.restore(candidate) if method == 'production_restore' else flow.resume()
            producer_agent().reset()
            return result
        if method == 'production_audition':
            return flow.audition(mcp_connection())
        if method == 'production_approve':
            return flow.approve(mcp_connection())
        if method == 'production_back':
            return flow.back()
        raise ValueError('Etapa musical desconhecida.')
    if method == "learn":
        try:
            if client.call("record_status", timeout=2).get("state") in ("recording", "finalizing"):
                raise ValueError("Espere o render terminar antes de treinar gêneros.")
        except client.BridgeOffline:
            pass
        result = genres.start(params["folder"])
        update_settings({"genre_source": result["folder"]})
        return result
    if method == "prepare_genre":
        return prepare_genre(params["name"], params["files"])
    if method == "preview_genres":
        return preview_genres(params["folder"])
    if method == "save_settings":
        allowed = {"onboarding_step", "onboarding_complete", "active_genre", "provider", "model", "assistant"}
        return {"settings": update_settings({k: v for k, v in params.items() if k in allowed})}
    if method == "api_models":
        from .desktop_agent import available_models
        return {"models": available_models(params["provider"], params["key"])}
    if method in ("auth_begin", "auth_logout", "auth_select"):
        state = producer_agent().status()
        if state["state"] == "running" or state["pending"]:
            raise ValueError("Termine a conversa ou descarte a proposta antes de mudar a conta.")
        producer_agent().reset()
        if method == "auth_begin":
            return chatgpt_auth().begin(params.get("new_account", False))
        if method == "auth_logout":
            return chatgpt_auth().logout()
        return chatgpt_auth().select(params["account_id"])
    if method == "auth_cancel":
        chatgpt_auth().cancel()
        return chatgpt_auth().status()
    if method == "auth_models":
        return chatgpt_auth().models()
    if method == "auth_acknowledge":
        return chatgpt_auth().acknowledge()
    if method == "chat":
        if params.get("provider") == "chatgpt":
            account = chatgpt_auth().status()
            if params["model"] not in {m["id"] for m in account["models"]}:
                raise ValueError("Selecione um modelo disponível na sua conta ChatGPT.")
            return producer_agent().start(params.get("text", ""), "chatgpt", params["model"],
                  chatgpt_auth().access_token(), params.get("genre", ""), approve=params.get("approve"))
        return producer_agent().start(params.get("text", ""), params["provider"], params["model"],
                                      params["key"], params.get("genre", ""), approve=params.get("approve"))
    if method == "reset_chat":
        return producer_agent().reset()
    if method == "mcp_call":
        allowed = {"ableton_status", "producer_brief", "list_genres", "genre_knowledge", "genre_plan_structure",
                   "analyze_audio", "compare_to_genre", "change_log", "ableton_command", "render_start"}
        name = params["tool"]
        if name not in allowed:
            raise ValueError("Esta ferramenta não está disponível no painel.")
        if name == "ableton_command" and params.get("args", {}).get("cmd") not in ("transport", "get_track", "record_status"):
            raise ValueError("Comando não disponível no painel.")
        if name == "render_start" and any(j["state"] in ("queued", "running") for j in genres._JOBS.values()):
            raise ValueError("Espere o aprendizado terminar antes de renderizar.")
        if name in ("analyze_audio", "compare_to_genre"):
            try:
                if client.call("record_status", timeout=2).get("state") in ("recording", "finalizing"):
                    raise ValueError("Espere o render terminar antes de analisar áudio.")
            except client.BridgeOffline:
                pass
        return {"data": mcp_connection().call(name, params.get("args", {}))}
    if method == "install_bridge":
        return install_bridge(params["library"])
    if method == "configure_claude":
        return configure_claude()
    if method == "index_samples":
        return index_samples(params["folders"])
    raise ValueError("Unknown method: %s" % method)


def setup_runtime():
    """Make bundled codecs discoverable, and keep downloaded models in user data."""
    os.environ.setdefault("TORCH_HOME", str(Path(DATA_DIR) / "Models" / "torch"))
    try:
        import imageio_ffmpeg
        ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
        bin_dir = Path(DATA_DIR) / "Runtime" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        link = bin_dir / "ffmpeg"
        if not link.is_symlink() or os.readlink(link) != str(ffmpeg):
            temp = bin_dir / ("ffmpeg.%s" % os.getpid())
            try:
                temp.symlink_to(ffmpeg)
                os.replace(temp, link)
            finally:
                if temp.is_symlink():
                    temp.unlink()
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    except ImportError:
        pass


def main():
    import multiprocessing
    multiprocessing.freeze_support()
    setup_runtime()
    if "--mcp" in sys.argv:
        from .server import main as mcp_main
        # MCP closes its stream wrappers. Keep the bootloader's original handles alive
        # so PyInstaller can flush them cleanly when the interpreter exits.
        original_input, original_output = sys.stdin, sys.stdout
        sys.stdin = open(os.dup(original_input.fileno()), "r", encoding="utf-8")
        sys.stdout = open(os.dup(original_output.fileno()), "w", encoding="utf-8", buffering=1)
        try:
            mcp_main()
        finally:
            sys.stdin, sys.stdout = original_input, original_output
        return
    if "--self-test" in sys.argv:
        from .server import producer_brief
        import imageio_ffmpeg
        import soundfile
        import torch
        import demucs
        import beat_this
        print(json.dumps({"ok": True, "data_dir": DATA_DIR,
                          "ffmpeg": os.path.isfile(imageio_ffmpeg.get_ffmpeg_exe()),
                          "soundfile": soundfile.__libsndfile_version__, "torch": torch.__version__,
                          "prompt": "GENRE CONTEXT:" in producer_brief()}))
        return
    if "--desktop" not in sys.argv:
        raise SystemExit("Use --desktop or --mcp")
    # Third-party logs must never corrupt the line protocol.
    output = sys.stdout
    sys.stdout = sys.stderr
    output_lock = threading.Lock()
    def respond(line):
        req = {}
        try:
            req = json.loads(line)
            result = dispatch(req["method"], req.get("params", {}))
            response = {"id": req["id"], "result": result}
        except Exception as e:
            response = {"id": req.get("id") if isinstance(req, dict) else None,
                        "error": "%s: %s" % (type(e).__name__, e)}
        with output_lock:
            output.write(json.dumps(json_safe(response), ensure_ascii=False, allow_nan=False) + "\n")
            output.flush()
    try:
        mcp_connection()
        with ThreadPoolExecutor(max_workers=4) as pool:
            for line in sys.stdin:
                pool.submit(respond, line)
    finally:
        if _AUTH:
            _AUTH.cancel()
        if _MCP:
            _MCP.stop()


if __name__ == "__main__":
    main()
