"""Coordinated 4/4 sketches; musical hypotheses, never a quality score.

Keep a repeatable cell and compare subtraction with the same bass/anchor notes.
All timing is baked into MIDI; applying another swing will compound it.
"""
import math

from . import club, groove


def sketch(style="tech_house", tonic="G", mode="minor", bars=8, bpm=126.,
           swing=56., seed=7, drum_layers=4, clap_delay_ms=5., percussion_delay_ms=0.):
    """Return main/stripped note sets and factual MIDI diagnostics, without Live I/O."""
    style = style.strip().lower().replace(" ", "_")
    if style not in ("tech_house", "deep_house"):
        raise ValueError("style must be tech_house or deep_house")
    if type(bars) is not int or not 2 <= bars <= 64 or bars % 2:
        raise ValueError("bars must be an even integer from 2 to 64")
    if type(drum_layers) is not int or not 3 <= drum_layers <= 5:
        raise ValueError("drum_layers must be an integer from 3 to 5")
    for name, value, low, high in (("bpm", bpm, 60, 200), ("swing", swing, 50, 66),
                                  ("clap_delay_ms", clap_delay_ms, 0, 25),
                                  ("percussion_delay_ms", percussion_delay_ms, -15, 15)):
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{name} must be finite and from {low} to {high}")
    total = bars * 4
    # One hat voice, not simultaneous open and closed hats by default.
    parts = ["kick", "clap", "closed_hat", "rim", "shaker"][:drum_layers]
    drums = groove.pattern(style, bars, swing, humanize=0, seed=seed, parts=parts)
    bass = club.motif("bass", tonic, mode, bars, swing, seed, density="sparse")["notes"]
    # Guard low-end MIDI gates against the next anchor; audible release is separate.
    for note in bass:
        note[2] = round(min(note[2], math.floor(note[1]) + 1 - note[1] - .04), 4)
    bass_slots = {round(n[1] * 4) for n in bass}
    rim_slots = {round(n[1] * 4) for n in drums.get("rim", [])}
    removed = 0
    for part, notes in drums.items():
        delay = (clap_delay_ms if part == "clap" else
                 percussion_delay_ms if part in ("closed_hat", "rim", "shaker") else 0)
        kept = []
        for note in notes:
            slot = round(note[1] * 4)
            # Optional percussion answers the bass; shaker and rim share no slots.
            overlap = part in ("rim", "shaker") and slot in bass_slots
            overlap |= part == "shaker" and slot in rim_slots
            # A single rest in the closing beat, without a new layer or fill.
            ending_rest = part in ("rim", "shaker") and note[1] >= total - 1
            if overlap or ending_rest:
                removed += 1
                continue
            note[1] = round(max(0., note[1] + delay * bpm / 60000.), 4)
            note[2] = round(min(note[2], total - note[1]), 4)
            kept.append(note)
        drums[part] = kept
    main = {**drums, "bass": bass}
    # Identical anchors and bass make the subtraction comparison interpretable.
    stripped = {part: [n[:] for n in notes if part != "closed_hat" or n[3] >= 95]
                for part, notes in main.items() if part not in ("rim", "shaker")}
    counts = {part: len(notes) for part, notes in main.items()}
    return {
        "main": main, "stripped": stripped, "length_beats": total,
        "assumptions": {"style": style, "bass_recipe": "sparse club motif; audition for selected style",
                        "tonic": tonic, "mode": mode, "bpm": bpm, "swing_pct": swing,
                        "seed": seed, "meter": "4/4", "drum_layers": drum_layers,
                        "clap_delay_ms": clap_delay_ms, "percussion_delay_ms": percussion_delay_ms},
        "midi_diagnostics": {"notes_per_part": counts, "support_hits_removed": removed,
                             "main_notes": sum(counts.values()),
                             "stripped_notes": sum(map(len, stripped.values()))},
        "intent": "Stable kick and backbeat, repeating bass identity, one hat voice, "
                  "support percussion in bass rests and one subtractive phrase ending.",
        "timing": "Swing and role offsets are baked into MIDI. Do not apply another groove "
                  "unless deliberately replacing or adjusting this timing. No independent jitter.",
        "verification": ["Discover Drum Rack pads and instruments before assigning pitches.",
                         "Audition main and stripped with identical sounds and matched perceived level; "
                         "keep the leaner version if the musical idea survives.",
                         "Check bass release against kick decay in mono; MIDI gates do not prove acoustic separation.",
                         "Compare with dated, relevant references. This recipe does not establish current style or mix quality."],
    }
