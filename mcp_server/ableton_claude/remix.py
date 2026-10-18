"""Evidence-based remix preparation; no Live edits or assumed stem files."""
import math

from .ear.listen import reliability
from .music.theory import pc


def plan(report, genre, target_bpm, target_tonic=None):
    if not math.isfinite(target_bpm) or not 20 <= target_bpm <= 400:
        raise ValueError("target_bpm must be finite and between 20 and 400")
    g = report["grid"]
    source_bpm = g["bpm"]
    if not math.isfinite(source_bpm) or source_bpm <= 0:
        raise ValueError("source grid has no valid BPM")
    evidence = reliability(report)
    warnings = list(evidence["warnings"])
    ratio = target_bpm / source_bpm
    if abs(ratio - 1) > 0.15:
        warnings.append("Large tempo change: audition vocal consonants, sustained notes and drum transients for artifacts.")
    transpose = None
    if target_tonic is not None:
        target_pc = pc(target_tonic)
        source_pc = report["harmony"].get("tonic_pc")
        if evidence["key_usable_for_transpose"] and source_pc is not None:
            transpose = (target_pc - source_pc + 6) % 12 - 6
        else:
            warnings.append("Transpose withheld until the source key is verified.")
    candidates = []
    for section in report["arrangement"]["sections"]:
        roles = [r for r in ("vocals", "other") if r in section["elements"]]
        if not roles:
            continue
        first = section["start_bar"]
        bars = min(8, section["end_bar"] - first + 1)
        start = g["first_downbeat"] + (first - 1) * 4 * g["period"]
        end = min(report["duration_s"], start + bars * 4 * g["period"])
        if end <= start:
            continue
        candidates.append({"source_start_bar": first, "bars": bars,
                           "source_seconds": [round(start, 4), round(end, 4)],
                           "roles": roles, "section": section["label"],
                           "status": "activity candidate; audition to identify the actual hook"})
    return {"source": {"file": report["file"], "id": report["id"], "bpm": source_bpm,
                       "key": report["key"], "first_downbeat_s": g["first_downbeat"]},
            "target": {"genre": genre, "bpm": target_bpm, "tonic": target_tonic},
            "tempo_ratio": round(ratio, 5), "transpose_semitones": transpose,
            "hook_candidates": candidates[:8], "warnings": warnings,
            "stem_status": "Ear separation is in memory; no importable stems were exported. Use discovered original stems or explicitly export separation first.",
            "workflow": [
                "Audition candidates and preserve one recognisable vocal/hook; keep original stem alignment and source offset.",
                "Verify first downbeat and tempo at start, middle and end; pitch-preserving warp changes tempo independently of pitch.",
                "Audition Beats for drums, Tones for mono material, Complex/Complex Pro for full mix or polyphonic stems; choose by artifacts.",
                "Build a new kick/bass pocket around the retained hook, then answer with sparse synth motifs in compatible harmony.",
                "Resequence phrases, create a contrasting break/drop and leave gaps for the vocal; do not stack the full original mix under new low end.",
                "Render a representative drop and transition; level-match references, fix source balance and separation artifacts before mastering.",
                "After final limiting, measure exported true peak, dynamics, mono/low end and full-song transitions; audition before claiming completion.",
            ]}
