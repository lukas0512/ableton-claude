# Why `solo_levels(one_pass=True)` crashed Live

**Cause:** the bridge read `Track.available_input_routing_channels` while Live was still
rebuilding that list after `input_routing_type` changed. In that window, Live 12.4.6 walks the
old input's list and uses it to index the new input's shorter channel vector with no bounds
check. Whether that crashes depends on what sits past the end of the vector, so most passes
survived.

The earlier suspects do not fit. The objects in the faulting path look valid and the index is
the same every time, which points to a read past the end rather than a deleted track or a stale
routing object. Bursts of structural changes and `reload` may make a crash more likely by
changing what sits in memory there, but they are not the cause.

## Evidence

Seven crash reports, 2026-10-28 to 2026-11-05 (Live 12.4.6), share one stack. `record_tracks`
arrived on 2026-10-26. The reports are in `~/Library/Logs/DiagnosticReports/Live-*.ips` and in
the bundles in `~/Library/Application Support/Ableton/Live Reports/`.

| Report | Failure | `x21` (index) | `x24` (loop) | `x20` (selected input) |
|---|---|---|---|---|
| 10-28 19:24 | EXC_BAD_ACCESS, write to a read-only address | 4 | 3 | 33 |
| 10-28 19:47 | EXC_BAD_ACCESS, garbage pointer | 4 | 3 | 33 |
| 10-28 20:57 | EXC_BAD_ACCESS, write to a read-only address | 4 | 3 | 33 |
| 10-30 13:35 | EXC_BAD_ACCESS, garbage pointer | 4 | 3 | 4 |
| 11-03 19:30 | `abort()` deeper in the same getter (see note) | n/a | 3 | n/a |
| 11-05 15:56 | EXC_BAD_ACCESS, garbage pointer | 4 | 3 | 5 |
| 11-05 17:18 | EXC_BAD_ACCESS, garbage pointer | 4 | 3 | 5 |

Note: in the 11-03 report the registers are from the `abort()`, so only the stack is comparable.
Its `x24` is 3 like the others, but that may be coincidence.

What the disassembly of the Live binary (arm64, offsets from the image base) shows:

- **Which call:** the registration code passes the name `available_input_routing_channels` with
  thunk `0x3c27c64`, which tail-calls `0x34119f4`. That function is crash frame 2.
- **The fault:** frame 0 (`0x267a4fc`) is `x9 = entry->vector[index]; x9->refcount++`, with no
  bounds check. The fault is on that refcount access at `0x267a50c` or `0x267a514`.
- **The mismatch:** frame 1 (`0x2667b60`) takes `entry` from the *selected input* and `index` from
  a separate list-to-channel map. Frame 2 loops over the list items and filters out
  `"Configure..."`.
- **The Python side:** the frames read as a property get under three nested generator resumes,
  called from `update_display`. That matches `tick → _advance → record_tracks → _start_record →
  setup`. The stack identifies only the structure, because Live's Python has no symbols here.

**Inferred, not observed:** the old list is the fresh track's Ext. In list. The log shows 2 input
channels, so item 3 may be `"Configure..."`, mapped to channel 4 of a source track that has fewer
channels. The old code's own comment recorded the stale list ("keeps the old input's channels
for a few ticks"), and the old loop read it from the first tick after setting the type. Live's
memory cannot be inspected from a crash report, so the list contents are not confirmed.

## The fix (bridge 0.8.1)

`_start_record` no longer reads the channel list until it is safe:

1. It creates every tap and sets its input type, with a listener on the channel list.
2. It waits once for all taps, after the last structural change, until every listener has fired
   and 5 ticks have passed with no further notification.
3. Only then does it read each list once and set the channel, and then arm.

The wait is capped at 50 ticks (about 5 s). At the cap it **refuses**: nothing is recorded, the
taps are removed and the arm states restored, and the error points to `one_pass=False`. A refusal
costs a soloed pass; a crash costs the producer's unsaved work.

**Not yet verified against Live:** the fix assumes the listener fires when the list has actually
been rebuilt. If it never fires, every `one_pass` call refuses (safe, but no use). If it fires
early, the 5 quiet ticks are the only margin. The steps below check this.

## Steps to reproduce and verify

Always in a **new empty Live set**, never the producer's. The script refuses a set with more than
6 tracks or while a render is running. Save the producer's set first, because a crash on the old
code takes down the whole of Live.

Verify the fix:

```bash
scripts/install_remote_script.sh
```

Send `reload`, check `ping` reports bridge `0.8.1`, then:

```bash
cd mcp_server && uv run python ../scripts/smoke_taps.py --loops 20 --reload
```

Pass: every loop prints `ok`, Live survives, and no `tap` tracks are left. A `refused:` error
means the listener did not fire as assumed, so one-pass stays unavailable until that is resolved.

See the crash on the old code (not deterministic: it depends on memory layout, and has not been
reproduced on demand). Put the old file in place, using the commit before this fix:

```bash
git show fc7a289:remote_script/ClaudeBridge/handlers.py > "$HOME/Music/Ableton/User Library/Remote Scripts/ClaudeBridge/handlers.py"
```

Send `reload`, then loop until Live dies. To confirm, compare the new report's top frames with
`0x267a50c`/`0x267a514`, `0x2667c6c`, `0x3411a80`, `0x3c4653c`:

```bash
cd mcp_server && uv run python ../scripts/smoke_taps.py --loops 200
```

The offsets are only valid for this Live build (12.4.6, 2026-09-10_0de5c8fa9a). Afterwards run
`scripts/install_remote_script.sh` and `reload` again.

Offline, `mcp_server/tests/test_record_tracks_channels.py` models the stale window and counts
stale reads; the same test against the old code reports reads for both taps.

## Same hazard elsewhere, not changed

`set_track_input(channel=...)`, `set_track_output(channel=...)` and `set_device_input` read a
channel list in the same tick they change the type. No crash report ties them to this bug, and
`set_device_input` (the only one of the three the repo's scripts pass a channel to) reads a
Device's list through a different binding, not shown to reach the same native code. The order of
operations is the same, so treat it as a risk rather than a known crash.
