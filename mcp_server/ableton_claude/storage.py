"""Per-user writable data, independent of the connector installation."""
import functools
import math
import os
import threading

DATA_DIR = os.path.abspath(os.path.expanduser(os.environ.get(
    "ABLETON_CLAUDE_DATA", "~/Music/Ableton Claude")))

# Analysis shares a cache and expensive models. Serialize learning jobs and studies.
ANALYSIS_LOCK = threading.RLock()
_LOCAL = threading.local()


def json_safe(value):
    """Preserve Live's silence values using valid JSON, readable by native clients."""
    if isinstance(value, float) and not math.isfinite(value):
        return None if math.isnan(value) else "-Infinity" if value < 0 else "Infinity"
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def serialized_analysis(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        with ANALYSIS_LOCK:
            if getattr(_LOCAL, "active", False) or os.name != "posix":
                return fn(*args, **kwargs)
            import fcntl
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(os.path.join(DATA_DIR, "analysis.lock"), "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                _LOCAL.active = True
                try:
                    return fn(*args, **kwargs)
                finally:
                    _LOCAL.active = False
                    fcntl.flock(lock, fcntl.LOCK_UN)
    return wrapped
