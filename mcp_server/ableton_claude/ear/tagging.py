"""What is sounding, second by second: AudioSet tags from PANNs Cnn14.

A stem from a separator is not one thing: the "vocals" stem of a rap record carries the
rap, the hook singing, the DJ's scratches and the reverb tails together. Cnn14
(Kong et al. 2020, MIT code, weights on Zenodo record 3987831, CC BY 4.0) tags 527
AudioSet classes, including "Scratching (performance technique)", "Rapping",
"Reverberation" and "Crowd", in windows along the file, so a stem can be cut where its
content changes and each piece named for what it is.

Measured on City 2 City's stems (2026-10-26): vocals, bass ("Bass guitar"), guitar and
keys stems tag right; single drum parts do not (a soloed snare reads "Clock", "Tick"):
DrumSep's own stem names are the better label there. A reverb tail split off by the
dereverb model still tags as the voice it came from: ambience is a separation, not a tag.

Only the network is defined here; the spectrogram is torch.stft and the mel matrix is
the checkpoint's own (logmel_extractor.melW), so no librosa or torchlibrosa is needed.
The weights (~330 MB) download on first use into <data>/Models/panns.
"""
import csv
import urllib.request
from pathlib import Path

import numpy as np
from scipy import signal

from ..storage import DATA_DIR

SR = 32000
CKPT_URL = "https://zenodo.org/record/3987831/files/Cnn14_mAP%3D0.431.pth?download=1"
CKPT_NAME = "Cnn14_mAP=0.431.pth"
LABELS = Path(__file__).parent / "data" / "audioset_labels.csv"

# AudioSet labels -> the roles a producer names. The first matching role wins in order,
# so the specific ones (scratch, rap) come before the generic (vocal, music).
ROLES = [
    ("scratch", ["Scratching (performance technique)", "Scratch"]),
    # an isolated rap reads as Speech far more than as Rapping (City 2 City's vocal stem:
    # Speech 0.37-0.43, Rapping under 0.15), so rap and speech share one role
    ("rap_or_speech", ["Rapping", "Speech", "Male speech, man speaking",
                       "Female speech, woman speaking", "Narration, monologue",
                       "Conversation", "Shout", "Yell", "Laughter"]),
    ("sung_vocal", ["Singing", "Male singing", "Female singing", "Child singing", "Choir",
                    "Chant", "A capella", "Vocal music", "Humming", "Synthetic singing"]),
    ("crowd", ["Crowd", "Cheering", "Applause", "Hubbub, speech noise, speech babble"]),
    ("fx", ["Sound effect", "Whoosh, swoosh, swish", "Siren", "Gunshot, gunfire",
            "Explosion", "Telephone", "Car", "Beep, bleep"]),
    ("ambience", ["Reverberation", "Echo"]),
    ("noise", ["Noise", "Static", "Hum"]),
    ("drums", ["Drum machine", "Drum kit", "Drum", "Snare drum", "Bass drum", "Hi-hat",
               "Cymbal", "Tambourine", "Maraca", "Cowbell", "Clapping", "Finger snapping",
               "Percussion", "Rimshot", "Drum roll"]),
    ("bass", ["Bass guitar"]),
    ("keys", ["Piano", "Electric piano", "Organ", "Hammond organ", "Keyboard (musical)",
              "Vibraphone", "Marimba, xylophone", "Bell", "Steelpan"]),
    ("synth", ["Synthesizer", "Sampler", "Theremin", "Sine wave"]),
    ("guitar", ["Guitar", "Electric guitar", "Acoustic guitar"]),
    ("strings_brass", ["String section", "Violin, fiddle", "Brass instrument", "Trumpet",
                       "Saxophone", "Flute"]),
]
ROLE_MIN_P = 0.15      # a role is present in a window when one of its labels reaches this
GENERIC = {"Music", "Silence", "Electronic music", "Hip hop music", "House music",
           "Techno", "Funk", "Disco", "Soul music", "Rhythm and blues", "Pop music",
           "Dance music", "Electronica", "Musical instrument"}

_MODEL = None


def labels():
    with open(LABELS, newline="") as f:
        return [r[2] for r in list(csv.reader(f))[1:]]


def checkpoint_path():
    d = Path(DATA_DIR) / "Models" / "panns"
    d.mkdir(parents=True, exist_ok=True)
    p = d / CKPT_NAME
    if not p.exists():
        tmp = p.with_suffix(".part")
        urllib.request.urlretrieve(CKPT_URL, tmp)
        tmp.rename(p)
    return p


def _build():
    import torch
    from torch import nn
    import torch.nn.functional as F

    class Block(nn.Module):
        def __init__(self, cin, cout):
            super().__init__()
            self.conv1 = nn.Conv2d(cin, cout, 3, padding=1, bias=False)
            self.conv2 = nn.Conv2d(cout, cout, 3, padding=1, bias=False)
            self.bn1 = nn.BatchNorm2d(cout)
            self.bn2 = nn.BatchNorm2d(cout)

        def forward(self, x, pool):
            x = F.relu(self.bn1(self.conv1(x)))
            x = F.relu(self.bn2(self.conv2(x)))
            return F.avg_pool2d(x, pool)

    class Cnn14(nn.Module):
        def __init__(self):
            super().__init__()
            self.bn0 = nn.BatchNorm2d(64)
            chans = [1, 64, 128, 256, 512, 1024, 2048]
            for i in range(6):
                setattr(self, "conv_block%d" % (i + 1), Block(chans[i], chans[i + 1]))
            self.fc1 = nn.Linear(2048, 2048)
            self.fc_audioset = nn.Linear(2048, 527)
            self.register_buffer("melW", torch.zeros(513, 64))
            self.register_buffer("window", torch.hann_window(1024))

        def forward(self, wav):                      # (batch, samples) at 32 kHz
            spec = torch.stft(wav, 1024, 320, window=self.window, center=True,
                              pad_mode="reflect", return_complex=True).abs() ** 2
            mel = torch.matmul(spec.transpose(1, 2), self.melW)       # (b, t, 64)
            x = 10 * torch.log10(torch.clamp(mel, min=1e-10)).unsqueeze(1)
            x = self.bn0(x.transpose(1, 3)).transpose(1, 3)
            for i in range(6):
                x = getattr(self, "conv_block%d" % (i + 1))(x, (1, 1) if i == 5 else (2, 2))
            x = torch.mean(x, dim=3)
            x = torch.max(x, dim=2)[0] + torch.mean(x, dim=2)
            x = F.relu(self.fc1(x))
            return torch.sigmoid(self.fc_audioset(x))

    import torch as _t
    model = Cnn14()
    state = _t.load(checkpoint_path(), map_location="cpu", weights_only=False)["model"]
    state = {k: v for k, v in state.items() if not k.startswith("spectrogram_extractor")}
    state["melW"] = state.pop("logmel_extractor.melW")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if [m for m in missing if m != "window"] or unexpected:
        raise RuntimeError("Cnn14 weights do not match: %s %s" % (missing, unexpected))
    return model.eval()


def model():
    global _MODEL
    if _MODEL is None:
        _MODEL = _build()
    return _MODEL


def to_mono_32k(x, sr):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 2:
        x = x.mean(axis=1)
    if sr != SR:
        g = np.gcd(int(sr), SR)
        x = signal.resample_poly(x, SR // g, int(sr) // g).astype(np.float32)
    return x


def probabilities(mono32, window_s=2.0, hop_s=1.0, batch=16):
    """(starts_s, probs[n_windows, 527]) over windows of `window_s` every `hop_s`."""
    import torch
    w, h = int(window_s * SR), int(hop_s * SR)
    if len(mono32) < w:
        mono32 = np.pad(mono32, (0, w - len(mono32)))
    starts = list(range(0, len(mono32) - w + 1, h)) or [0]
    out = []
    m = model()
    with torch.no_grad():
        for i in range(0, len(starts), batch):
            chunk = np.stack([mono32[s:s + w] for s in starts[i:i + batch]])
            out.append(m(torch.from_numpy(chunk)).numpy())
    return [s / SR for s in starts], np.concatenate(out)


def roles_of(p, names, min_p=ROLE_MIN_P):
    """{role: strongest label probability} for one window's probabilities."""
    idx = {n: i for i, n in enumerate(names)}
    out = {}
    for role, labs in ROLES:
        best = max((float(p[idx[l]]) for l in labs if l in idx), default=0.0)
        if best >= min_p:
            out[role] = round(best, 2)
    return out


def tag(x, sr, window_s=2.0, hop_s=1.0, top=4, rms_floor_db=-50.0):
    """Tag audio along its length. Returns
    {"top": [[label, mean p]...] over the whole file (generic music labels left out),
     "roles": {role: seconds present}, "segments": [{start, end, roles, top}] where
     consecutive windows with the same leading role are merged}. Windows quieter than
     `rms_floor_db` (dBFS) are "silence" and get no roles."""
    names = labels()
    mono = to_mono_32k(x, sr)
    starts, probs = probabilities(mono, window_s, hop_s)
    w = int(window_s * SR)
    rows = []
    for s, p in zip(starts, probs):
        seg = mono[int(s * SR):int(s * SR) + w]
        rms = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12) if len(seg) else -120
        r = {} if rms < rms_floor_db else roles_of(p, names)
        lead = max(r, key=r.get) if r else ("silence" if rms < rms_floor_db else "music")
        order = np.argsort(-p)
        tops = [[names[i], round(float(p[i]), 2)] for i in order
                if names[i] not in GENERIC][:top]
        rows.append({"start": round(s, 2), "end": round(s + window_s, 2), "lead": lead,
                     "roles": r, "top": tops if r else []})
    segments = []
    for r in rows:
        if segments and segments[-1]["lead"] == r["lead"]:
            seg = segments[-1]
            seg["end"] = r["end"]
            for k, v in r["roles"].items():
                seg["roles"][k] = max(seg["roles"].get(k, 0), v)
        else:
            segments.append({"start": r["start"], "end": r["end"], "lead": r["lead"],
                             "roles": dict(r["roles"]), "top": r["top"]})
    mean = probs.mean(axis=0)
    order = np.argsort(-mean)
    seconds = {}
    for r in rows:
        for k in r["roles"]:
            seconds[k] = seconds.get(k, 0) + hop_s
    return {"top": [[names[i], round(float(mean[i]), 3)] for i in order
                    if names[i] not in GENERIC][:8],
            "roles": {k: round(v, 1) for k, v in sorted(seconds.items(), key=lambda kv: -kv[1])},
            "segments": segments}


def tag_file(path, **kw):
    import soundfile as sf
    x, sr = sf.read(str(path), dtype="float32", always_2d=False)
    return tag(x, sr, **kw)
