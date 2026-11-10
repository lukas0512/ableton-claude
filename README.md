# MOTRA

Turn musical ideas into MIDI, groove and arrangements inside Ableton Live with an integrated assistant using your ChatGPT plan. MOTRA is the product name; the repository and internal bridge retain their existing identifiers.

```
Native app chat ──MCP──▶ mcp_server (Python) ──TCP 9878──▶ ClaudeBridge (Remote Script, inside Live)
                     │                                  │
                     ├─ music: theory, voice leading,   └─ Live Object Model: tracks, arrangement
                     │  call & response, grooves,          clips, MIDI, presets, devices, clip
                     │  sample understanding               envelopes, locators, transport,
                     ├─ arranger: songs from phrases       master render (Resampling)
                     └─ analysis: LUFS, true peak, bands, stereo, per section
```

## Pieces

| Path | What |
|---|---|
| `remote_script/ClaudeBridge/__init__.py` | Control surface: TCP server and inbox. Almost never changes. |
| `remote_script/ClaudeBridge/handlers.py` | Every command and the main loop. Hot-reloaded by `reload` (it re-installs the main loop on the running control surface, so no Live restart). |
| `mcp_server/ableton_claude/server.py` | MCP tools. |
| `mcp_server/ableton_claude/music/` | `theory` (scales, chords, roman numerals, voice leading), `harmony` (progressions with anticipation, swing), `melody` (call and response), `groove` (swung patterns, build rolls), `samples` (key, tempo, swing, role, bass notes). |
| `mcp_server/ableton_claude/arranger.py` | Builds an arrangement from a library of phrases stashed past the song. |
| `mcp_server/ableton_claude/analysis.py` | Objective mix measurements and technical flags. |
| `mcp_server/ableton_claude/references.py` | Learns a genre from reference tracks: tempo (0.02 BPM), bass-anchored key, swing, loudness, 1/3-octave shape, and structure (kick on the beats vs bass on the off-beats, per bar). |
| `mcp_server/ableton_claude/knowledge.py` | Curated genre conventions (deep house, tech house, minimal, UK garage, soulful, disco) plus measured profiles; plans section lengths. |
| `mcp_server/ableton_claude/elements.py` | `split_elements`: opens a mix, loop or sample into one track per element (kick, snare, toms, hats, ride, crash, bass, music, lead/backing vocal, dry voice/reverb) under the source, same positions and warp, revertible. |
| `mcp_server/ableton_claude/ear/separate.py` | Separation by task through python-audio-separator (htdemucs_ft, DrumSep, RoFormer karaoke and dereverb); models download on first use into `~/Music/Ableton Claude/Models/separation`. |
| `mcp_server/ableton_claude/ear/tagging.py` | PANNs Cnn14 AudioSet tags along a file: rap or speech, singing, scratch, crowd, fx, keys, guitar... |
| `mcp_server/ableton_claude/mixing.py` | Turns a profile comparison into a few broad, capped EQ bands and limiter drive, and applies them on the Live master. |
| `~/Music/Ableton Claude/knowledge/genres/*.profile.json` | Per-user measured genre profiles (built from your own reference folders). Repository profiles are development examples, not loaded into the app. |
| `scripts/build_deep_house.py` | Worked example: rebuilds a project into a 6-minute deep house track with a story. |
| `scripts/render_and_analyze.py` | Renders a bar range and measures it per locator section. |
| `scripts/smoke_live.py` | Integration test against a running Live. |
| `scripts/repair_clip_time.py` | Repairs clips whose `Time` disagrees with `CurrentStart` in an `.als`. |
| `scripts/build_profile.py` | `build_profile.py <folder> <genre>`: builds a genre profile (cached, resumable). |
| `scripts/mix_to_profile.py` | `mix_to_profile.py <render> <genre> [--apply]`: compares a mix with a genre and moves the master toward it. |

## Setup

### macOS app and installer

Build the installer with `python3 scripts/build_macos.py --dmg` (current version **1.4.0**), then
open `dist/MOTRA-1.4.0-arm64.dmg` (or the `.pkg`) to install in **Applications**.
The build is ad-hoc signed, not notarized: on first launch macOS blocks it; allow it in
**System Settings → Privacy & Security → Open Anyway**.
An optional `.dmg` supports dragging **MOTRA** into Applications. This local build targets
**Apple Silicon and macOS 26+**. Python, MCP, FFmpeg and the audio dependencies are
included; end users do not need a terminal or another AI app.

**Intel Macs (macOS 13 Ventura or newer):** `python3 scripts/build_macos.py --arch x86_64 --dmg`
builds `MOTRA-<version>-x86_64.dmg`. PyTorch's last Intel Mac build is 2.2.2, so this
backend is frozen from `desktop/intel/requirements.txt` (Python 3.12, numpy 1.x, demucs 4.0.1)
in its own venv under `build/macos-x86_64/`. On Apple Silicon the build needs Rosetta
(`softwareupdate --install-rosetta`); on an Intel Mac it runs natively. The ear runs on the CPU
there (`ear.torch_device`): Intel Macs with AMD GPUs report MPS, but torch 2.2.2 has no MPS FFT.
The full test suite and a full `listen` on a 35-bar demo give identical results on both sets.

The installed Apple Silicon app currently occupies about 920 MiB, including PyTorch
for local musical analysis. The compressed `.pkg` is about 300 MiB
and can be removed after installation. Learned profiles, reference links and downloaded
audio models are separate under `~/Music/Ableton Claude/`; deleting release archives
does not delete them. The development Python environment is also separate from the app.
Default builds now generate only the `.pkg` and remove generated staging directories
after success. Use `--dmg` for a second distribution format and `--keep-build` for
debugging or subsequent `--skip-backend` builds. A `.dmg` contains only the app, without
another copy of the installer. Packaging requires at least 3 GiB of free temporary space;
larger optional builds or dependency downloads may require more. Old release archives
are retained unless deliberately cleaned, so avoid accumulating unnecessary versions.

The app guides you through six steps. Only connecting Live and choosing an assistant are
required; samples and genre learning can be skipped and done later.

1. **Welcome:** explains how references, the assistant and Live work together.
2. **Connect Live:** detects the User Library, installs ClaudeBridge with a backup,
   and verifies Live and the internal MCP connection. On first installation, quit and
   reopen Live (it scans Remote Scripts only at launch), then select
   ClaudeBridge in **Live Settings → Link, Tempo & MIDI → Control Surface**, with
   Input/Output None. Existing active bridges reload without restarting Live. The app
   owns its MCP connection and reconnects automatically.
3. **Your samples (optional):** pick one or more sample folders (packs, Splice, your
   collection). The app indexes names and headers only (role, loop/one-shot, key and BPM
   from file names) into `samples_index.json`, so `library_search` / `find_samples` use
   the user's own sounds. Files are not copied or uploaded.
4. **Choose your AI:** **Claude Desktop** or **ChatGPT in the app**.
   - *Claude Desktop:* the app checks Claude is installed (or links to claude.ai/download),
     registers the `ableton-claude` connector in `claude_desktop_config.json` (other
     connectors preserved, backup made) and reopens Claude to load the tools. The
     conversation then happens in Claude Desktop, on the user's Claude plan; Claude starts
     the connector itself (`--mcp`), so this app does not need to stay open. The final step lists first prompts to copy.
   - *ChatGPT:* see the account flow below.
5. **Learn your sound (optional):** name a genre and select audio tracks; the app organizes the
   references. Alternatively, import a parent folder with one subfolder per genre.
   Follow analysis and listening progress, then review any failures. Keep the app open
   during learning. The first training downloads audio models into
   `~/Music/Ableton Claude/Models/torch/`; later runs reuse cached analysis.
   **ChatGPT account:** click **Continuar com ChatGPT**, sign in using
   the official OpenAI browser flow and authorize eligible ChatGPT plan usage for this
   app. Return to the app and choose an account-provided model. No API key is required.
   The app uses its own OAuth registration, PKCE and verified OpenID identity; it never
   extracts Codex, Claude or browser credentials. Sessions renew automatically and are
   stored under `Authentication/` with owner-only permissions. Saved registrations can
   be selected or signed out in settings. Usage shares the account's eligible plan or
   credits and limits; **Gerenciar uso** opens ChatGPT's usage settings.
6. **Enter the studio:** with ChatGPT, send prompts inside Ableton Claude. The assistant reads the
   project through MCP, shows its activity and presents changes for review. Apply or
   discard proposals in the app. The project panel shows tracks, transport and rendering;
   compare a render with your trained genre and discuss the measured result.

The studio first asks **Criar do zero** or **Continuar projeto**. Give the project
an optional name and confirm the empty set/project copy before entering the chat.

**Continuar projeto** supports both your own tracks and tracks created with this app.
Choose diagnosis, groove, arrangement or mix. The assistant starts from existing
material, preserves its identity and proposes focused changes for review; there are
no mandatory loop/groove milestones in this mode. A diagnosis starts with reads only.
You can ask for a different improvement in chat at any time.

**Guardar e trocar de projeto** keeps each session's name, mode, stages and approvals
in `Production/Projects/<id>.json` and clears the conversation for the next project.
Use **Retomar projetos recentes salvos pelo app** to select a saved session (the latest
100 appear), open its corresponding set/copy in Live and explicitly confirm it. The
app verifies expected tracks before switching; a failed check leaves the current
selection and saved milestones intact. Restoring a guided idea retains its exact
Loop/Groove/Arrangement stage. Reopening an app-made track through **Continuar projeto**
instead uses the flexible existing-project workflow. No audio or `.als` files are copied
into this metadata library. Save/open actual project files in Ableton; Live exposes
no reliable save/open-project API or unique project ID to the bridge.

For new music, the studio follows **Loop → Groove → Arrangement**:

1. Open an empty Live set or a project copy, choose 4, 8 or 16 bars and click
   **Começar ideia**. Existing material is preserved; workshop tracks get their own
   prefix, and occupied projects use a scratch interval after the existing song.
2. **Construir loop** proposes a motif and simple foundation. Review and apply the
   proposal, then click **Ouvir loop**. Ask for variations in chat until you like it.
   **Ouvi e aprovo · avançar** explicitly approves the musical result.
3. **Desenvolver groove** refines the approved motif with kick/bass pocket,
   percussion, velocity and variation in the same short interval. Listen and approve
   again. Tool review or a chat response never advances a musical milestone.
4. **Abrir arranjo** unfolds the approved groove into sections, entries, exits and
   energy contrast. Listen to the arrangement and approve it; a single unchanged loop
   cannot qualify as an arrangement. You can return to an earlier stage to refine it.

Stage controls run locally with no additional model request. Changes after audition
invalidate musical approval; approval rechecks clip metadata, MIDI notes and basic
track/device state. Session metadata is stored in `Production/session.json`, without
copying audio. After reopening the app, explicitly confirm that the same Live project
is open to resume. Live has no reliable project identifier in the bridge overview.
Guarding an idea clears the active workflow, archives its milestones and leaves its Live tracks in place.

**Groove rápido** (third starting point, no AI account needed, only Live): pick a vibe, an
optional reference you trained ("Inspirado em"), key, swing (reto, leve, padrão, forte), bass
style and loop length; a step grid shows the first bar of every part with the reasons. **Outra
variação** draws another one. **Colocar no Live** builds exactly the groove shown on five new
tracks (`G1 · KICK`, `CLAP`, `HATS`, `PERC`, `BASS`) with Live's 909 / Percussion Core Kits, a
stock bass sidechained to the kick and high-passes that leave the low end to kick and bass:
a looping 4/8/16-bar loop, or **Faixa pronta para a pista** (intro and outro of drums alone for
DJs, break, build, drop, locators). An empty set takes the groove's tempo; a set with music
keeps its tempo and gets the groove after its end. **Tirar o último groove do Live** deletes
those tracks, locators and the tempo change. It is a starting point to hear, not a verdict.

Work on a copy of your Live project. Chat and proposals belong to the current app
session; profiles, musical milestones and setup are persisted. Use **Meu som** to add genres and
**Conexão e IA** to update access. The built-in guide explains the production cycle.
Project information, text and tool measurements go to OpenAI;
reference analysis runs locally. With Claude Desktop, the conversation goes to Anthropic instead.

Proposal review shows the affected track, position, parameter values and MIDI note
count, with full tool arguments available for inspection. The producer is instructed
to explain the observed problem, intended audible result, creative assumptions and
verification before an edit. This is a decision summary; audio still has to demonstrate
the intended result. An independent execution receipt records applied, failed and
skipped actions, including available journal IDs, even if the next model response fails.
Desktop batches execute sequentially and stop on the first failure; successful earlier
changes remain applied. Discarding a proposal never runs its commands. Applying rechecks
the Live overview and blocks detectable changes since review. This check excludes moving
transport state and cannot identify an otherwise identical set or changes to individual
notes/device values absent from the overview; keep the intended project copy open.

The OpenAI sign-in integration is for locally hosted clients and follows the current
[official ChatGPT plan usage flow](https://developers.openai.com/siwc/token-sharing-open-source).
Its availability depends on account eligibility and permission to share plan usage.
The app uses streamed Responses requests with `store: false`, completes local MCP tools,
collects completed stream items (including final encrypted reasoning) even when the
terminal response omits output, and preserves the proposal review flow. No tool is run
until the entire response completes successfully; empty responses show recovery guidance.
It never falls back to separately billed API
keys. Limits and revoked sessions produce recovery guidance inside the app.

Claude subscription login is not offered: Anthropic requires specific authorization for
third-party apps to use Claude.ai subscription credentials. See its
[official authentication policy](https://code.claude.com/docs/en/legal-and-compliance).

The studio accepts simple requests such as **“Melhore o groove”**, **“Dê mais impacto
ao drop”** and **“Deixe minha faixa mais profissional”**. Local preparation supplies a
fresh project overview and the selected genre's conventions/measured ranges before
the first model request. The producer chooses a small first stage, preserves the hook,
states creative assumptions and asks only when a missing choice materially affects
the result. Audio quality still needs a representative render, comparison and listening;
the app does not label an unverified production professional.

To reduce context, the app caches the full brief locally and sends a compact working
contract plus relevant technical lessons. Tool groups load for the task; `producer_tools`
can unlock other groups without a Live edit. Generated MIDI is retained locally and
reused by result reference, with the exact notes expanded in the review proposal.
Large tool results include explicit omission counts instead of broken/truncated JSON.
Long chats discard complete older turns while retaining recent tool-call/result pairs,
encrypted reasoning and bounded historical request excerpts; this is not permanent
conversation memory. A fresh Live overview replaces stale assumptions every user turn.
**Uso deste pedido** shows actual reported input/output token totals across model calls,
or states when the provider did not report them. No extra model calls are used for
classification, context preparation or compression, and the app does not silently
switch the chosen model. Savings depend on the model, task and number of iterations.

Offline regression checks include local MIDI reuse, proposal review, measured genre
context, dynamic tool discovery and history pair preservation. For a repeatable context
size comparison without spending tokens: `cd mcp_server && uv run python
../scripts/benchmark_producer_context.py`. Its character counts are **not** billed tokens.


User profiles, references, caches, renders and logs live in `~/Music/Ableton Claude/`.
References selected in the app remain in their original location and are linked from
`Genre References/`; keep their source files available. `GENRE CONTEXT` is generated
from saved user profiles for each request. File locks serialize expensive analysis.
Logs are in `Logs/app.log`. To uninstall, delete the app; user data remains separate.

Build from source on a Mac with Xcode Command Line Tools and uv:

```bash
python3 scripts/build_macos.py
```

For local development testing without freezing another copy of the audio dependencies:

```bash
python3 scripts/build_desktop_dev.py
open "build/desktop-dev/Ableton Claude Dev.app"
```

This small native app requires this checkout and `mcp_server/.venv`; it is not a
standalone installer. It uses the installed app's user data by default. For isolated
testing, launch its executable with `ABLETON_CLAUDE_DATA` pointing to a test directory.
Its backend also supports `scripts/smoke_desktop.py`, which checks the desktop protocol,
temporary bridge installation, MCP tools and audio analysis without altering a Live set.

Outputs are the native `.app` in `build/macos/product/`, plus `.pkg` and `.dmg` in
`dist/`. The build freezes Python/dependencies, verifies the bundle signature and
runs an import/resource self-test before packaging. For a functional check of the
packaged desktop API and MCP protocol, run:

```bash
cd mcp_server
uv run python ../scripts/smoke_desktop.py "../build/macos/product/MOTRA.app/Contents/Resources/backend/ableton-claude-backend"
```

This local installer uses ad hoc signing and **is not Apple-notarized**. Public
distribution still needs valid Developer ID signing and Apple notarization. The
builder accepts `--sign-identity` and `--installer-identity` for signing; notarization
is a separate release step. Builds for Intel or earlier macOS versions require a
compatible Python/dependency runtime and testing on those targets.

### Development connector

1. `scripts/install_remote_script.sh`
2. Start Live. In **Settings → Link, Tempo & MIDI**, pick **ClaudeBridge** in a free
   Control Surface slot, Input and Output **None**.
3. `claude mcp add --scope user ableton-claude -- uv run --directory ~/dev/ableton-claude/mcp_server ableton-claude-mcp`

After editing `handlers.py`: `scripts/install_remote_script.sh`, then the `reload` command.

## MCP tools

| Tool | Does |
|---|---|
| `producer_brief` (also the `produce` prompt) | The method (`briefs/producer.md`) and the lessons from real tracks (`briefs/lessons.md`). Any AI reads it before changing a project. |
| `ableton_status`, `ableton_command`, `ableton_batch`, `ableton_reload_bridge` | Read and drive Live (the command list is in the server instructions). |
| `change_log`, `revert_changes`, `live_undo` | Every change is journaled with the value it replaced (`~/Music/Ableton Claude/journal.jsonl`) and can be put back exactly. |
| `render_start`, `render_wait`, `analyze_audio`, `compare_to_reference` | Record the master and measure it. |
| `music_chords` | Roman numerals → chord symbols in a key. |
| `music_progression` | Voice-led chord part (held common tones, anticipation). |
| `music_call_and_response` | Call that asks, response that answers, audited against the rules. |
| `music_drum_pattern`, `music_build_roll` | Swung deep house kit, build-up roll. |
| `analyze_sample`, `analyze_bassline` | Key, BPM, swing, role; bass notes per beat. |
| `genre_knowledge`, `genre_plan_structure` | What a genre is (conventions + measured numbers); a section plan for N minutes. |
| `learn_genres(pasta)`, `learn_genres_status(pasta)`, `list_genres` | Train one genre per immediate subfolder, follow background progress, and list the user's saved profiles. |
| `analyze_reference`, `compare_to_genre`, `mix_toward_genre` | Measure a reference; hold a mix against a genre; move the Live master toward it. |
| `analyze_timbre`, `find_samples`, `groove_loop` | Kick, bass, hats, clap and breakdown against the genre; rank a folder's one-shots by that timbre; place a one-shot on the references' per-16th feel as a loop. |
| `study_references`, `study_status`, `reference_study` | Study ~5 references chosen for this track (paths, a folder, or the set's REF tracks): measured and heard in the background, saved as a profile under the study's name (usable as `genre` everywhere) with a brief of what they share, where they disagree and a section plan. Audio stays where it is (`~/Music/Ableton Claude/References/<name>/` holds links and is also a drop-in inbox). |
| `validate_against_genre`, `analyze_tension` | Every measure at once; break depth, build and drop against the references. |
| `quality_gate` | Static checks of the open set before a version goes to the producer: leftover render tracks, overridden clip automation, hot Simplers, notes on empty pads, parts in different swing pockets, voices in different spaces, an unsafe master, fewer than two drops. With `render`/`previous`/`study`, also the aesthetics guard. |
| `aesthetics` | How good a render sounds to a model trained on human ratings (Meta audiobox-aesthetics, ~5 s a track): enjoyment, usefulness, complexity and production quality per 10 s, against the previous render (where it got worse) and a study's references. A guard and a ranker, not a tension meter. |
| `remix_plan` | Analyze an original for a remix: grid/key reliability, hook candidates, tempo ratio, safe transpose. |
| `rap_phrase` | Cut a phrase from a vocal stem and place it warped syllable by syllable: a marker on every source 16th, syllables moved 60 % onto the 16th plus the set's swing, half a beat of pre-roll. |
| `onset_chop` | Vocal chops that start at a real syllable attack, unwarped, placed so the attack lands on the beat. |
| `stem_loop`, `breakbeat_loop`, `place_loop` | A 2-bar loop from the original's 'other' stem (least vocal bleed, most typical window) or a drum break, warped per 16th into the set's pocket; laid out as one clip per section (tiled, odd/even bars, Auto Filter and volume envelopes). |
| `quick_groove`, `quick_groove_remove` | A whole groove in one call: crisp drums (kick, clap+snare, hats, percussion) and a bassline off the kick in one baked swing, per vibe (house, tech house, deep house, UK garage, afro house) or from a trained genre/study's tempo, key, swing, hats' per-16th feel and heard bass rhythms. `apply=True` builds it in Live with stock kits and bass (loop, or a DJ-friendly ~120-bar track with locators); `quick_groove_remove` takes it out. |
| `solo_levels`, `solo_levels_status` | In the background, each element soloed over the same bars, limiter off: integrated LUFS against the kick, 1/3-octave spectra and a masking report (elements within 6 dB of each band's loudest). Restores solos and the limiter, deletes its render tracks. |

## The ear

Short creation requests such as **“faça um tech house pista”** now load composition,
groove, arrangement, mix and verification tools together. With no genre selected, an
explicit style in the request supplies genre context. `music_drum_pattern` accepts
`style="tech_house"` (its existing default remains `deep_house`), and
`music_club_motif(part="bass"|"hook", tonic="G", mode="minor", bars=8, seed=7)` creates
related sparse MIDI motifs with a phrase turnaround and sound-design suggestions.
The desktop can reuse a result's notes using
`{"$result":"material-1","field":"notes"}`; drum parts use e.g. `"field":"kick"`.
All Live changes still pass through proposal review.

`production_intent(prompt, genre)` interprets explicit PT/EN musical cues as hypotheses,
keeping bass amount, harmonic openness, density, articulation and width independent.
“Heavy but closed bass” and “light but open bass” therefore produce different directions.
Section targets and simple negation are retained; unknown emotion stays unknown.
The desktop includes relevant cues in its working context without another model call.

`music_club_motif` also accepts `density="sparse|normal|busy"`,
`articulation="short|sustained"`, `development="restrained|evolving"` and `octave`.
Bass defaults to octave 1 (G1 = MIDI 31); hooks default to octave 4. Structured phrase
development keeps the motif identity; sustained bass gates leave room before kick
beats, while actual synth release still requires tuning and audition.

`production_review(path, prompt, genre, reference_path)` hears bass weight versus drums,
180–2000/25–180 Hz bass harmonic balance, low-band mono loss, note occupancy and drum
attack/tail proxies per section. It reports every detected drop's local loudness,
low-end/pulse return and element changes. An equal-LUFS drop is not automatically weak.
Direct references take priority over trained section distributions; each reference gets
one vote per metric. Neither a reference quartile nor a proxy is an aesthetic score.
Full-song review responses disclose omissions; `start_bar` / `end_bar` retrieve focused
section evidence from the cached analysis. Timbre proxies are withheld in near-silent
stem passages so separation residue is not treated as the intended bass sound.
The implementation and research limits are documented in
[the production model](docs/music-production-model.md).

`remix_plan(path, genre="tech house", target_bpm=128, target_tonic="A")` analyzes the
original, suggests activity regions to audition for a hook, preserves source bar/time
offsets and proposes tempo/transpose preparation. It withholds transpose on ambiguous
key evidence. It prepares a workflow; it does not export stems or create a completed
remix. The ear's separated stems remain in memory. The remix itself is built from the
demucs stems with `rap_phrase`, `onset_chop`, `stem_loop`/`breakbeat_loop` + `place_loop`,
then balanced with `solo_levels` (the methods of "From The Streets",
`scripts/build_from_the_streets.py`).

Ear v3 reports grid/key reliability (the key margin is a heuristic, not a probability),
invalidates caches when the supplied tempo hint changes and measures stem balance only
in the selected full sections, excluding intervening breaks. Existing ear caches are
rebuilt on the next listen; saved genre aggregates need retraining to use these fixes.
Audio cache IDs now hash the complete file in bounded chunks, so revisions with the
same intro and a changed drop cannot silently reuse the previous analysis. This changes
cache IDs; old cache files are retained, and current-version reports are used for pooling.
Master matching preflights an existing final Live Limiter or Pro-L 2 using exposed dB
controls before editing EQ, and stops limiter changes if EQ setup fails.

“Current” sound depends on relevant references, instrument selection and audition;
these patterns do not establish contemporary release trends. A finished mix/master
still requires rendered-audio comparison, dynamics/true-peak checks and listening.

Claude does not hear audio, so the connector translates it. `listen(path)` separates a
track into drums, bass, harmony and vocals (Demucs), puts it on a beat and bar grid
(Beat This), and transcribes it:

- drums on the 16-step grid, per instrument (kick, clap/perc, hats): which steps are
  played, accents, microtiming, swing measured against the hats' own on-beats;
- the bassline as MIDI: register, degrees, the typical bar, how often it lands with the kick;
- chords per beat with Roman numerals, pedal points as slash chords, key, harmonic rhythm;
- what plays in every bar, the sections that follow, and each layer's level and width
  against the drums.

The result is a listening report in words plus the heard MIDI, cached per file.
`scripts/listen_folder.py` hears a folder of references; `scripts/build_principles.py`
pools them into what the genre shares and why it works (`genre_principles`), and
`compare_by_ear` holds a render against them in producer terms. `extract_groove` turns a
reference's feel into a Live groove file (Groove Pool).

The user's sample packs are a resource too: `library_index` indexes them (role, loop or
one-shot, tempo and key from the names), `library_search` finds material in key and tempo,
`library_midi` reads royalty-free pack MIDI transposed to the song's key. A pack loop
carries its producer's feel and timbre together and a one-shot carries neither, so
`find_samples` picks the one-shot by the genre's measured timbre and `groove_loop` places
it with the references' per-16th micro-timing, accents and timing variation (pooled from
their ear reports into the genre's `ear.drums.<role>.template`), giving the genre's sound
with the genre's groove. Pack material can also be out of tune with itself: measure, then
`set_clip(warping=True, warp_mode="complex_pro", detune=cents)`.

Measured on our own tracks, where the truth is known: tempo, bars, form, entries, the
bassline (G1/D2 off the kick) and the hats' swing come out right; the chroma votes with
spectral peaks in 110-1500 Hz only, so a C minor organ and stab read Cm / Cm9 and the
finished mix reads C minor, Cm7 (summing every bin had turned the root's overtones into
"Cmaj9"). Chord roots in a busy breakdown are still right only about half the time.

## Teaching it a genre

Give `learn_genres(pasta)` a folder path, with one immediate subfolder per genre:

```text
My References/
  Jazz/
    album/track.wav
  Tech House/
    track.flac
  Ambient/
    track.mp3
```

`learn_genres("~/Music/My References")` scans audio recursively inside each genre,
without the 12-track limit of a project study. It measures tempo, key, loudness,
spectrum, structure, fingerprints, timbre and tension, and adds ear principles when
the optional ear dependencies are installed. Audio stays in the source folder.
Training runs in the background: call `learn_genres_status` with the same path for
progress, completed profiles and per-folder errors. Avoid rendering while training.
Calling it again resumes from the content cache; after restarting the server, use
`list_genres` to see saved profiles and call `learn_genres` again to resume training.

All connector-owned writable data defaults to `~/Music/Ableton Claude/`:
profiles in `knowledge/genres/`, analysis cache in `knowledge/cache.json`, ear reports
and heard MIDI in `knowledge/ear/`, library indexes/caches in `knowledge/`, study briefs
in `References/<name>/`, and the change journal in `journal.jsonl`.
Set `ABLETON_CLAUDE_DATA` to override the data root (existing journal/study overrides
still apply). Existing repository profiles and caches are not imported automatically;
copy any profiles you want to retain into the new `knowledge/genres/` folder.

The `GENRE CONTEXT` line in `producer_brief` and the `produce` prompt is filled from
the user's saved profiles on every call. Server instructions include that context at
startup and refresh after learning; an already-connected client may retain its initial
instructions, so read `producer_brief` again after training. A fresh installation has
no trained genres and invites the user to train their own references.

The single-genre development script remains available:

```bash
cd mcp_server
uv run python ../scripts/build_profile.py "/path/to/Tech House" "tech house"
```

Every track in the folder is measured once (cached by content in the user's `knowledge/cache.json`),
then aggregated into medians and middle-half ranges. The profile is statistics over real
records: it says where a mix or an arrangement is unusual for the genre, not whether it
is good. Where profile and conventions disagree on numbers, the profile wins.

## Things Live's API does not do, and the workarounds

| Limit | Workaround |
|---|---|
| No export / render | Record the master into a track through the **Resampling** input, in real time. |
| Arrangement clips cannot get new automation envelopes | Build the clip in Session with its envelopes, then `duplicate_clip_to_arrangement`. |
| No API for an arrangement clip's length (`end_marker` moves content only) | A clip dropped on another truncates it: drop a copy at the cut, delete the copy. |
| No track-level arrangement automation | Clip envelopes on the clips themselves. |
| Playhead moves apply a tick later, and `continue_playing` ignores them | Commands that move the playhead are generators that wait for Live; playback uses `start_playing`. |
| Frozen tracks play their old freeze file | Do not move clips on frozen tracks; unfreeze in Live first. |
| No save | Save in Live (`Cmd+S`). |

## Tests

```bash
cd mcp_server && uv run pytest -q                      # offline: music, analysis, bridge plumbing
uv run python ../scripts/smoke_live.py [--force]       # against a running Live
```

### Groove studies and coordinated sketches

`music_pocket_sketch` adds a coordinated house/tech-house drums+bass foundation with
shared swing, stable anchors, restrained support voices and a stripped A/B alternative.
It is available to the integrated assistant in composition and groove tasks; generation
is read-only and applying notes uses the existing proposal review. Timing is already
baked into MIDI. See [the applied study guide](docs/groove-study.md) for experiments,
research sources, reference selection and listening criteria. Source changes require
restarting the development backend or rebuilding the packaged app to become available.
