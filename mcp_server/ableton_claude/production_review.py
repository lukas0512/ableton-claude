"""Explain measured production choices without claiming to hear emotions."""
from . import intent
from .ear import perception


def review(report, prompt="", reference_profile=None, start_bar=None, end_bar=None):
    heard = report.get("perception")
    if not heard or heard.get("version") != perception.VERSION:
        raise ValueError("Listen again to obtain compatible section perception evidence")
    if (start_bar is not None and (type(start_bar) is not int or start_bar < 1)) or \
       (end_bar is not None and (type(end_bar) is not int or end_bar < 1)) or \
       (start_bar is not None and end_bar is not None and end_bar < start_bar):
        raise ValueError("bar range must be positive integers with end_bar >= start_bar")
    if start_bar is not None or end_bar is not None:
        a, b = start_bar or 1, end_bar or float('inf')
        heard = {**heard, 'sections': [s for s in heard['sections'] if s['end_bar'] >= a and s['start_bar'] <= b],
                 'transitions': [t for t in heard['transitions'] if a <= t['drop_bar'] <= b]}
    goals = intent.interpret(prompt)
    comparison = perception.compare(heard, reference_profile or {})
    findings = []
    for section in heard["sections"]:
        loss = section["metrics"].get("bass_low_mono_loss_db")
        if loss is not None and loss < -3:
            findings.append({"priority": "check", "axis": "low_end_mono", "bars": [section["start_bar"], section["end_bar"]],
                             "evidence": {"bass_low_mono_loss_db": loss, "heuristic_check_below_db": -3},
                             "next": "Audition bass in mono; inspect stereo oscillator phase/width before adding gain. Separation bleed can affect this measurement."})
    axis_metric = {'bass_amount': 'bass_vs_drums_db', 'bass_openness': 'bass_upper_to_low_db',
                   'bass_density': 'bass_notes_per_bar', 'bass_articulation': 'bass_occupancy_pct'}
    desired = {'heavy': 'above', 'light': 'below', 'open': 'above', 'closed': 'below',
               'busy': 'above', 'sparse': 'below', 'sustained': 'above', 'short': 'below'}
    # An ordinal request is not an absolute target; flag only opposite reference evidence.
    for direction in goals['directions']:
        axis, scope = direction['axis'], direction['scope']
        if any(c['axis'] == axis and c['scope'] == scope for c in goals['conflicts']):
            continue
        wanted = desired.get(direction['value'])
        if wanted is None:
            continue
        for row in comparison['rows']:
            if row['metric'] != axis_metric.get(axis) or (scope != 'track' and scope != row['section']):
                continue
            if row['position'] in ('within', wanted):
                continue
            findings.append({"priority": "audition", "axis": axis, "bars": row['bars'],
                             "request": direction, "evidence": row,
                             "next": goals['translation'][axis],
                             "limit": "Direction differs from reference evidence; this is not proof that the request is unmet."})
    return {"file": report['file'], "intent": goals, "findings": findings,
            "scope": {"requested_start_bar": start_bar, "requested_end_bar": end_bar,
                      "meaning": "Whole detected sections intersecting range; metrics retain their actual section boundaries."},
            "sections": heard['sections'],
            "section_comparison": comparison,
            "transitions": heard['transitions'],
            "reliability": report.get('reliability'),
            "assessment": "Measured proxies and listening hypotheses only; no professional/emotional quality score.",
            "next_audition": ["Level-match the reference to the mix before comparing tone/groove.",
                              "Listen from before the break through the first drop phrase, including first-hit impact and low-end return.",
                              "Check hook identity, bass weight versus openness, tail overlap, mono and fatigue, then keep/revert."]}
