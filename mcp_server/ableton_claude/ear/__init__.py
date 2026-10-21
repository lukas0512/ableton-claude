"""The ear: turn audio into what a producer hears.

A finished track is split into stems (drums, bass, other, vocals), put on a beat and
bar grid, and transcribed: drum hits on the 16-step grid with their microtiming and
accents, bass notes as MIDI, chords per bar, and which element plays in which bar.
From that come a listening report in words, MIDI parts, a groove file Live can load,
and, over a folder of references, the principles a genre follows.

Heavy models (Demucs, Beat This) are imported lazily, so the MCP server starts fast.
"""
EAR_VERSION = 3


def torch_device():
    """Apple GPU on Apple Silicon, CPU elsewhere. Intel Macs with AMD GPUs also report MPS,
    but their torch (2.2.2, the last Intel build) lacks MPS FFT and fails in the
    spectrogram. ABLETON_CLAUDE_DEVICE=cpu|mps overrides."""
    import os, platform
    import torch
    forced = os.environ.get("ABLETON_CLAUDE_DEVICE")
    if forced in ("cpu", "mps"):
        return forced
    if platform.machine() == "arm64" and torch.backends.mps.is_available():
        return "mps"
    return "cpu"
