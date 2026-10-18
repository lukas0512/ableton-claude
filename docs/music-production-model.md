# Musical intention, perception and evidence

The goal is to make deliberate musical choices from simple requests, preserve a
recognisable idea and evaluate the resulting audio in context. The current system
offers symbolic composition, source-separated measurements and a model-guided workflow.
It does not infer a listener's feelings or certify professional quality from a score.

## What the research supports

- [Witek et al., 2014, PLOS ONE](https://doi.org/10.1371/journal.pone.0094446)
  studied syncopated drum breaks and listener ratings. Intermediate syncopation received
  higher movement/pleasure ratings in that experiment. This supports exploring a
  balance between a stable pulse and rhythmic interest, not a universal optimal pattern
  or a quality metric for complete tech-house productions.
- [Musical Tension Associated With Violations of Hierarchical Structure, 2020](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2020.578112/full)
  investigates structural expectation and tension. Applying expectation/release to
  electronic arrangement is a production hypothesis; this study does not validate our
  drop metrics as an emotion detector.
- [Ableton, Fuzzy Boundaries](https://makingmusic.ableton.com/fuzzy-boundaries)
  describes staggered changes across section boundaries. We use this as a craft reason
  to evolve phrases and avoid identical block changes at every boundary; it is not a
  prescribed sequence of moves.
- [Ableton, Plucked Bass](https://learningsynths.ableton.com/recipes/plucked-bass)
  demonstrates amp decay and a modulated filter. This grounds the distinction between
  note rhythm, amplitude envelope and changing brightness. Our spectral ratio does not
  recover the original cutoff frequency, oscillator or plugin settings.
- [Ableton Limiter reference](https://www.ableton.com/en/manual/live-audio-effect-reference/#limiter)
  explains gain, dynamics and true-peak mode. Final rendered output and listening are
  necessary; a limiter drive estimate does not establish transient quality.

## Independent musical controls

| Intention | Decisions to test | Audio evidence | Limits |
|---|---|---|---|
| More/less bass weight | Source balance, register, kick/bass allocation | Bass/drums stereo RMS by section | Separation bleed; RMS is not perceived loudness |
| Closed/open bass | Oscillator harmonics, filter and envelope movement | 180–2000 Hz / 25–180 Hz bass power | Depends on register, pitch and source content; not measured filter cutoff |
| Sparse/rolling | Rests, syncopation, repeated rhythmic cell | Notes per bar and union of note durations | Transcription errors; more notes are not automatically more drive |
| Short/sustained | Gates, amp/filter release, tail interaction | Occupancy plus contextual listening | MIDI length is not audible release; reverb can outlast the note |
| Centre/width | Oscillator phase, upper-harmonic width | Bass low-band mono/stereo power ratio | Mono loss can be deliberate; review rather than automatically repair |
| Drop impact | Withheld/restored pulse, low end, space, timbre, transients | Local LUFS and stem-level changes, low-power share, element entries, attack/tail ratio | No single cue proves release or emotion |

Ratios use average stereo-channel power before mono summing, so antiphase bass does
not disappear from the amount measurement. Silence yields unavailable ratios, not
invented targets. Harmonic balance is level invariant. Bass occupancy merges overlaps
and carries sustained tails into following bars. Attack/tail compares fixed beat windows;
it is a transient proxy affected by drum envelopes and other percussion.

Timbre and transient ratios are withheld for bars over 30 dB below that separated
stem's peak-bar power. This explicit activity heuristic reduces interpretation of
separation residue during absent parts; it is not a calibrated source-presence model.
Raw stem-level changes and inferred element entries remain separate evidence.

Section medians stay separate by role. Training pools one median per track per metric,
so a long track or one containing many drops does not dominate the reference profile.
Direct-reference profiles show that they contain only one track. Differences outside
the middle half remain differences, never automatic defects. Historical profiles need
retraining for ear v3 perception fields; stale reports do not become compatible data.
File IDs hash all audio bytes in bounded chunks. Identical introductions with changed
drops therefore get different analysis IDs. Older cache files are preserved.

## Deliberate production loop

1. Inspect the source, hook, phrase, project and selected references. Establish actual
   tempo/key confidence and available sounds. State missing evidence or assumptions.
2. Translate the intended feeling into an audible phrase story. Explicit words are cues,
   not psychological measurements. Preserve unspecified bass dimensions.
3. Consider two coherent alternatives differing on a meaningful axis. Explain audible
   consequences. Do not assign unheard candidates a professional/emotional score.
4. Preserve an anchor motif; develop rests, gates, accents, timbre and phrase endings.
   Keep drum anchors. Avoid independent timing and pitch jitter as a naturalness rule.
5. Review/apply a short candidate, audition, then assess the break/drop in context.
   A loud build can release through space and a returning groove without a LUFS jump.
6. Compare tone/groove at matched levels and transition contrast within each track.
   Fix source selection/balance before mastering. Render again after final limiting.
7. Keep/revert based on measured evidence and the listener's response. Structural
   execution, technical checks and aesthetic approval remain separate outcomes.

This process adds no artificial waiting and no hidden provider/model switch. Stage
approvals remain in the app. The vocabulary parser is intentionally limited; the
original request and conversational context outrank it. It can miss indirect phrasing,
sarcasm, complex negation and context-dependent emotional language.

## Validation

`tests/test_expression.py` uses known signals and symbolic fixtures to check independent
amount/openness, antiphase loss, silence, sustained occupancy, all local drop transitions,
equal-loudness contrast, reference weighting, intent uncertainty and MIDI invariants.
These checks validate signal-processing and integration behaviour; they cannot validate
whether a new composition feels emotional, current, human or release-ready. That requires
representative reference audio and repeated contextual listening.

Full-song review tool responses disclose omitted sections/findings/comparison rows.
Use `start_bar` / `end_bar` to inspect a transition; the tool selects whole detected
sections intersecting that range and reports their actual boundaries. Cached analysis
is reused. This avoids silently losing late-song evidence to desktop context limits.
