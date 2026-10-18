"""Learn all immediate genre subfolders, with persistent per-user profiles."""
import os
import threading
import time

from . import knowledge, study
from .storage import serialized_analysis

_JOBS = {}
_LOCK = threading.Lock()


def discover(pasta):
    root = os.path.abspath(os.path.expanduser(pasta))
    if not os.path.isdir(root):
        raise ValueError("not a folder: %s" % root)
    folders, keys = [], {}
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if name.startswith(".") or not os.path.isdir(path):
            continue
        key = knowledge.key_of(name)
        if not key:
            raise ValueError("invalid genre folder name: %s" % name)
        if key in keys:
            raise ValueError("genre folders %r and %r resolve to the same profile" % (keys[key], name))
        keys[key] = name
        folders.append((name, path))
    if not folders:
        raise ValueError("no genre subfolders in %s; create one subfolder per genre" % root)
    return root, folders


@serialized_analysis
def _run(job, folders, on_done):
    job["state"] = "running"
    for name, folder in folders:
        job["current_genre"] = name
        try:
            if not study.audio_files(folder):
                raise ValueError("no audio files in this genre folder")
            brief = study.run(name, folder, log=job["log"].append,
                              brief_folder=study.folder_of(name), kind="genre")
            job["completed"].append({"genre": name, "n_tracks": brief["n_references"],
                                     "profile": knowledge.profile_path(name)})
            on_done()
        except Exception as e:
            job["errors"].append({"genre": name, "error": "%s: %s" % (type(e).__name__, e)})
    job["current_genre"] = None
    job["state"] = ("partial" if job["completed"] else "failed") if job["errors"] else "done"


def start(pasta, on_done=lambda: None):
    root, folders = discover(pasta)
    with _LOCK:
        job = _JOBS.get(root)
        if job and job["state"] in ("queued", "running"):
            return status(root)
        job = {"state": "queued", "started": time.time(), "folder": root,
               "genres": [name for name, _ in folders], "current_genre": None,
               "completed": [], "errors": [], "log": []}
        _JOBS[root] = job
        threading.Thread(target=_run, args=(job, folders, on_done),
                         name="learn-genres", daemon=True).start()
    return status(root)


def status(pasta):
    root = os.path.abspath(os.path.expanduser(pasta))
    job = _JOBS.get(root)
    if not job:
        return {"error": "no learning job for %s in this session" % root,
                "trained_genres": knowledge.trained_genres()}
    return {k: list(v) if isinstance(v, list) else v for k, v in job.items()
            if k not in ("log", "started")} | {
        "elapsed_s": round(time.time() - job["started"]), "log": job["log"][-6:],
        "genre_context": knowledge.genre_context(),
        "next": "call learn_genres_status(pasta) for progress; producer_brief includes the saved genres"}
