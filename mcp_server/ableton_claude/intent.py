"""Explicit musical language → independent production hypotheses, without model calls.

This is a small bilingual vocabulary, not sentiment classification. Unknowns stay
unknown; the original request and contextual listening outrank a keyword match.
"""
import re
import unicodedata


def _plain(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if not unicodedata.combining(c))


AXES = {
    "bass_amount": {
        "light": r"\b(pouco (?:bass|graves?)|menos (?:bass|graves?)|(?:baixo|bass) (?:leve|discreto)|light bass|less bass|subtle bass)\b",
        "heavy": r"\b(muito (?:bass|graves?)|mais (?:bass|graves?)|heavy bass|more bass|bass pesado|baixo pesado|grave pesado|baixo mais presente)\b",
    },
    "bass_openness": {
        "closed": r"\b(fechad[oa]|aveludad[oa]|abafad[oa]|closed|muted|mellow)\b",
        "open": r"\b(abert[oa]|rasgad[oa]|brilhante|open|bright|growly)\b",
    },
    "bass_density": {
        "sparse": r"\b(poucas notas|menos notas|espacad[oa]|sparse|fewer notes)\b",
        "busy": r"\b(muitas notas|mais notas|rolling|busy|rolante)\b",
    },
    "bass_articulation": {
        "short": r"\b(curto|curtinho|staccato|short|plucky)\b",
        "sustained": r"\b(sustentado|longo|legato|sustained|long)\b",
    },
    "bass_width": {
        "mono": r"\b(mono|centralizado|centred|centered)\b",
        "wide": r"\b(estereo|stereo|wide|largo)\b",
    },
}
TRANSLATION = {
    "bass_amount": "Change bass/drum balance, register and low-end allocation; do not assume more notes or brighter harmonics.",
    "bass_openness": "Change oscillator harmonics, filter cutoff/envelope and articulation; do not confuse opening the filter with stereo widening or volume.",
    "bass_density": "Change rests and rhythmic occupancy while retaining the motif; do not assume bass weight must increase.",
    "bass_articulation": "Tune MIDI gates AND synth amp/filter release against kick decay; MIDI duration alone does not control audible tails.",
    "bass_width": "Inspect low-band mono loss; if width is wanted, test upper harmonics separately from the sub.",
}
MOODS = {
    "hypnotic": (r"\b(hipnotic\w*|hypnotic|hipnose)\b", "Stable anchor motif, restrained pitch changes, evolving accents/timbre; avoid new notes every bar."),
    "euphoric": (r"\b(euforic\w*|euphoric|euforia)\b", "Test upward contour, harmonic lift and a widening upper register through the phrase; preserve low-end headroom."),
    "melancholic": (r"\b(melancolic\w*|melanchol\w*|saudade|triste|sad)\b", "Test expressive contour, suspended/resolving tones and space; minor mode alone does not establish sadness."),
    "tense": (r"\b(tens[oa]|tensao|tense|tension)\b", "Establish an expectation, delay its fulfilment, and plan an audible release; dissonance is one option."),
    "intimate": (r"\b(intim[oa]|intimate|delicad\w*|delicate)\b", "Test fewer foreground voices, close/dry presence and gentle articulation; keep the rhythmic anchor when needed."),
    "dark": (r"\b(sombri\w*|dark|obscur\w*)\b", "Test lower-register harmony and restrained upper harmonics, while keeping the hook legible; do not automatically low-pass the whole mix."),
}


def _negated(text, start):
    prefix = text[max(0, start - 32):start]
    return bool(re.search(r"\b(nao|not|without|sem|evitar|avoid)\s+(?:\w+\s+){0,2}$", prefix))


def interpret(prompt):
    text = _plain(prompt)
    directions, moods, avoid, conflicts = [], [], [], []
    # Keep section instructions separate, including 'closed in break, open in drop'.
    clauses = re.split(r"[,;.!?]|\bmas\b|\bbut\b", text)
    for clause in clauses:
        scopes = list(re.finditer(r"\b(break(?:down)?|drop|intro|outro)\b", clause))
        has_bass = bool(re.search(r"\b(bass|baixo|grave|sub)\b", clause))
        for axis, values in AXES.items():
            if axis != 'bass_amount' and not has_bass:
                continue
            for value, pattern in values.items():
                for match in re.finditer(pattern, clause):
                    scope = min(scopes, key=lambda s: abs(s.start() - match.start())).group() if scopes else 'track'
                    scope = 'break' if scope == 'breakdown' else scope
                    cue = {"axis": axis, "value": value, "scope": scope, "cue": match.group()}
                    (avoid if _negated(clause, match.start()) else directions).append(cue)
        for mood, (pattern, hypothesis) in MOODS.items():
            for match in re.finditer(pattern, clause):
                if _negated(clause, match.start()):
                    avoid.append({"mood": mood, "cue": match.group()})
                else:
                    moods.append({"mood": mood, "cue": match.group(), "hypothesis": hypothesis})
    for axis in AXES:
        for scope in {d['scope'] for d in directions if d['axis'] == axis}:
            found = {d['value'] for d in directions if d['axis'] == axis and d['scope'] == scope}
            if len(found) > 1:
                conflicts.append({"axis": axis, "scope": scope, "values": sorted(found)})
    return {"directions": directions, "moods": moods, "avoid": avoid, "conflicts": conflicts,
            "translation": {axis: TRANSLATION[axis] for axis in {d['axis'] for d in directions}},
            "status": "explicit cue hypotheses; original request/context and audition take priority",
            "unknowns": ["Listener emotion is not inferred from keywords or audio features.",
                         "Unspecified bass axes retain the project/reference character."]}


def plan(prompt, genre=None):
    intent = interpret(prompt)
    return {"intent": intent, "genre": genre,
            "decision_process": [
                "Inspect the hook, phrase, routing and available instruments, plus the selected references. Record creative assumptions.",
                "Translate the desired feeling into a phrase story: establish → withhold/transform → release → settle. Keep a recognisable anchor.",
                "Consider two coherent alternatives differing on one meaningful axis. Explain expected audible differences; do not score unheard candidates.",
                "Develop the strongest motif through rests, gates, accents and timbre; preserve kick/backbeat anchors. Random timing is not a substitute for groove.",
                "Audition the short loop, then the break→drop context, then full sections. Change a few related decisions and compare at matched levels.",
                "Separate source balance from mastering. Keep/revert using actual audio evidence and listener feedback; stop when evidence is missing or changes regress.",
            ],
            "completion_evidence": {"structural": "notes/devices/sections read back after editing",
                                    "technical": "rendered peaks, dynamics, low-end mono and section contrast",
                                    "aesthetic": "user audition: hook, feeling, groove and whether the drop releases the intended tension"}}
