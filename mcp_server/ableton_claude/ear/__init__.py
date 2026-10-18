"""The ear: turn audio into what a producer hears.

A finished track is split into stems (drums, bass, other, vocals), put on a beat and
bar grid, and transcribed: drum hits on the 16-step grid with their microtiming and
accents, bass notes as MIDI, chords per bar, and which element plays in which bar.
From that come a listening report in words, MIDI parts, a groove file Live can load,
and, over a folder of references, the principles a genre follows.

Heavy models (Demucs, Beat This) are imported lazily, so the MCP server starts fast.
"""
EAR_VERSION = 3
