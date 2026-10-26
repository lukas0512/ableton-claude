"""Separation by task: one model per question, through python-audio-separator (UVR,
MDX23C and RoFormer checkpoints from the ZFTurbo / UVR community).

`ear/stems.py` keeps htdemucs in memory for listening to references; this module writes
stems to disk for putting them on tracks: a loop or a whole song opened into one channel
per element (kick, snare, hats, lead vocal, backing vocal, the reverb apart from the dry
voice...).

Models download on first use into <data>/Models/separation (hundreds of MB each). The
published SDRs (dB, higher is cleaner) from the model list and the ZFTurbo table:
vocals 12.6 (htdemucs 8.4 on the same test), DrumSep kick 16.7 / snare 11.5 / toms 12.3
but hats 4.0 and cymbals 6.4: hats split badly, check them by ear.

Code is MIT; the community checkpoints mostly declare no license and the UVR authors ask
for credit. Download on demand, never ship them inside the app.
"""
import logging
import os
import time
from pathlib import Path

from ..storage import DATA_DIR

MODELS = {
    # task: (model file, {model stem name: our name})
    "stems": ("htdemucs_ft.yaml",
              {"vocals": "vocals", "drums": "drums", "bass": "bass", "other": "other"}),
    "vocals": ("vocals_mel_band_roformer.ckpt", {"vocals": "vocals", "other": "music"}),
    "drums": ("MDX23C-DrumSep-aufr33-jarredou.ckpt",
              {"kick": "kick", "snare": "snare", "toms": "toms", "hh": "hats",
               "ride": "ride", "crash": "crash"}),
    "karaoke": ("mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt",
                {"vocals": "lead_vocal", "instrumental": "backing_vocal"}),
    "dereverb": ("dereverb_mel_band_roformer_anvuew_sdr_19.1729.ckpt",
                 {"noreverb": "dry", "reverb": "reverb"}),
    "crowd": ("mel_band_roformer_crowd_aufr33_viperx_sdr_8.7144.ckpt",
              {"crowd": "crowd", "other": "no_crowd"}),
}

_SEPARATORS = {}


def model_dir():
    d = Path(DATA_DIR) / "Models" / "separation"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _separator(task, out_dir):
    from . import torch_device
    from audio_separator.separator import Separator
    sep = _SEPARATORS.get(task)
    if sep is None:
        if torch_device() == "cpu":
            os.environ.setdefault("AUDIO_SEPARATOR_FORCE_CPU", "1")
        sep = Separator(model_file_dir=str(model_dir()), output_dir=str(out_dir),
                        output_format="WAV", sample_rate=44100, log_level=logging.WARNING)
        sep.load_model(model_filename=MODELS[task][0])
        _SEPARATORS[task] = sep
    sep.output_dir = str(out_dir)
    if getattr(sep, "model_instance", None) is not None:
        sep.model_instance.output_dir = str(out_dir)
    return sep


def _stem_of(filename, names):
    """audio-separator names files '<input>_(<Stem>)_<model>.wav': find our stem name."""
    low = filename.lower()
    for theirs, ours in sorted(names.items(), key=lambda kv: -len(kv[0])):
        if "_(%s)" % theirs.lower() in low:
            return ours
    return None


def separate(path, task, out_dir, prefix=None):
    """Run one task's model on `path`; returns {our stem name: wav path} in `out_dir`.
    Files are named '<prefix> - <stem>.wav' (prefix defaults to the input's name)."""
    if task not in MODELS:
        raise ValueError("task: %s" % " | ".join(MODELS))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = prefix or Path(path).stem
    t0 = time.time()
    files = _separator(task, out_dir).separate(str(path))
    out = {}
    for f in files:
        p = Path(f) if os.path.isabs(f) else out_dir / f
        stem = _stem_of(p.name, MODELS[task][1])
        if stem is None:
            continue
        dest = out_dir / ("%s - %s.wav" % (prefix, stem))
        os.replace(p, dest)
        out[stem] = str(dest)
    if not out:
        raise RuntimeError("%s produced no recognised stems: %s" % (task, files))
    out["_seconds"] = round(time.time() - t0, 1)
    return out


def split(path, out_dir, drums=True, vocals=True, reverb=False, prefix=None, log=None):
    """Open a mix or loop into elements: vocals / drums / bass / other first, then the
    drums into kick, snare, toms, hats, ride, crash, and the vocals into lead and backing
    (and, with `reverb`, the lead into dry voice and its reverb). Returns
    {element: wav path, "_seconds": {task: s}}."""
    prefix = prefix or Path(path).stem
    out_dir = Path(out_dir)
    say = log or (lambda m: None)
    timing = {}
    say("stems")
    first = separate(path, "stems", out_dir, prefix)
    timing["stems"] = first.pop("_seconds")
    out = dict(first)
    if drums and "drums" in first:
        say("drums")
        parts = separate(first["drums"], "drums", out_dir / "drums", prefix)
        timing["drums"] = parts.pop("_seconds")
        out.update(parts)
    if vocals and "vocals" in first:
        say("karaoke")
        parts = separate(first["vocals"], "karaoke", out_dir / "vocals", prefix)
        timing["karaoke"] = parts.pop("_seconds")
        out.update(parts)
        if reverb and "lead_vocal" in parts:
            say("dereverb")
            wet = separate(parts["lead_vocal"], "dereverb", out_dir / "vocals",
                           prefix + " - lead")
            timing["dereverb"] = wet.pop("_seconds")
            out["lead_vocal_dry"] = wet["dry"]
            out["lead_vocal_reverb"] = wet["reverb"]
    out["_seconds"] = timing
    return out
