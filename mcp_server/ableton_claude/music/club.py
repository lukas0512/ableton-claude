"""Seeded, sparse club motifs. Recipes are creative starting points, not trend data."""
import math
import random

from .groove import swing_offset
from .theory import Scale


def motif(part="bass", tonic="G", mode="minor", bars=8, swing=54., seed=7,
          density="normal", articulation="short", development="restrained", octave=None):
    """Related two-bar bass/hook cells, with space and an ending variation."""
    if part not in ("bass", "hook"):
        raise ValueError("part must be bass or hook")
    if type(bars) is not int or not 2 <= bars <= 64 or bars % 2:
        raise ValueError("bars must be an even integer from 2 to 64")
    if not math.isfinite(swing) or not 50 <= swing <= 66:
        raise ValueError("swing must be finite and from 50 to 66")
    if density not in ('sparse', 'normal', 'busy') or articulation not in ('short', 'sustained') or development not in ('restrained', 'evolving'):
        raise ValueError("density: sparse/normal/busy; articulation: short/sustained; development: restrained/evolving")
    octave = (1 if part == 'bass' else 4) if octave is None else octave
    if type(octave) is not int or not 0 <= octave <= 6:
        raise ValueError("octave must be an integer from 0 to 6")
    scale = Scale(tonic, mode)
    rng = random.Random(seed)
    # Keep kick downbeats free; the hook answers the bass in a higher register.
    bass_cells = rng.choice([((2, 5, 7, 10, 14), (2, 6, 9, 14)),
                             ((2, 6, 11, 14), (2, 5, 10, 15))])
    cells = bass_cells if part == "bass" else ((3, 8, 12), (0, 7, 11))
    if density == 'sparse':
        cells = tuple(tuple(step for i, step in enumerate(cell) if i % 2 == 0) for cell in cells)
    elif density == 'busy':
        extra = (3, 7, 11, 15) if part == 'bass' else (2, 6, 10, 14)
        cells = tuple(tuple(sorted(set(cell) | set(extra))) for cell in cells)
    root = (octave + 1) * 12 + scale.tonic
    tones = [root, scale.step(root, 2), scale.step(root, 4)]
    phrase = []
    for bar, steps in enumerate(cells):
        for i, step in enumerate(steps):
            pitch = root if i < 2 else rng.choice(tones)
            phrase.append((bar, step, pitch, rng.randint(88, 108)))
    notes = []
    for cycle in range(bars // 2):
        for bar, step, pitch, velocity in phrase:
            absolute_bar = cycle * 2 + bar
            if development == 'evolving' and cycle % 2 and bar == 1 and step == cells[bar][-1]:
                pitch = tones[2]
                velocity = min(116, velocity + 4)
            # One turnaround, retaining the motif instead of re-randomising every bar.
            if absolute_bar == bars - 1 and step == cells[bar][-1]:
                pitch = tones[1] if part == "bass" else root
                velocity = min(116, velocity + 5)
            onset = absolute_bar * 4 + step / 4 + swing_offset(step, swing)
            duration = 0.16 if part == "bass" else 0.22
            notes.append([pitch, round(onset, 4), duration, velocity])
    if articulation == 'sustained':
        for i, note in enumerate(notes):
            next_onset = notes[i + 1][1] if i + 1 < len(notes) else bars * 4
            # Bass gates leave a small gap before each kick; synth release still needs audition.
            boundary = min(next_onset, math.floor(note[1]) + 1) if part == 'bass' else next_onset
            note[2] = round(max(.04, min(.85, boundary - note[1] - .04)), 4)
    return {"notes": notes, "length_beats": bars * 4, "part": part,
            "assumptions": {"tonic": tonic, "mode": mode, "swing_pct": swing,
                            "style": "tech_house", "seed": seed, "meter": "4/4", "octave": octave,
                            "density": density, "articulation": articulation, "development": development},
            "performance": "Seed preserves motif; phrase-ending development is structured. No independent timing jitter. "
                           "Density/gates do not determine bass gain, filter openness or audible synth release.",
            "sound_design": ({"oscillator": "mono sub plus quiet saw/pulse mid layer",
                              "envelope": ("short decay/release; tune duration against kick tail" if articulation == 'short'
                                           else "controlled sustain/release; audition tails and leave space for kick"),
                              "processing": "add harmonics only as needed; audition low end in mono"}
                             if part == "bass" else
                             {"oscillator": "short FM pluck or filtered saw stab",
                              "envelope": ("fast attack, short decay; filter/velocity accents" if articulation == 'short'
                                           else "held note with controlled release; filter/velocity accents"),
                              "processing": "short ambience; leave room for vocal; vary timbre per phrase"}),
            "verification": "Discover available instruments/presets, audition and compare with chosen references. "
                            "MIDI alone does not establish sound quality or current style."}
