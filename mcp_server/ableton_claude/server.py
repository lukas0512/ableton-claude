"""MCP server exposing Ableton Live (via ClaudeBridge) and audio analysis to Claude."""
import time

from mcp.server.fastmcp import FastMCP

from . import analysis, client

INSTRUCTIONS = """\
Drives Ableton Live through the ClaudeBridge Remote Script (127.0.0.1:9878).

Start with `ableton_status`. Use `ableton_command` for any bridge command and
`ableton_batch` to run many in one Live tick (much faster for building arrangements).

Addressing: track = index | exact name | unique name fragment | "master" | "return:<i|name>".
Clip (arrangement) = index in time order | {"at": beat} | clip name.
Times: pass `beat` (quarter notes from song start, 0-based) or `bar` (1-based).

Bridge commands (args):
  ping | get_song | get_track(track, clips=True) | get_device(track, device)
  get_notes(track, clip)
  set_tempo(bpm) | create_track(kind=midi|audio, name, index=-1) | delete_track(track)
  set_track(track, name, volume_db, pan, mute, solo, arm, monitoring=in|auto|off)
  set_send(track, send, db)
  create_midi_clip(track, length, notes=[[pitch,start,dur,vel],...], name, beat|bar, loop)
  add_notes(track, clip, notes, replace=False)
  create_audio_clip(track, path, beat|bar, name, warp, gain_db, pitch)
  set_clip(track, clip, name, muted, pitch, gain_db, looping, loop_start, loop_end, warping)
  mute_clips_in_range(track, muted, start_bar, end_bar)
  duplicate_clip(track, clip, beat|bar) | delete_clip(track, clip)
  create_*_clip(..., envelopes=[{param, device, points:[[beat_in_clip, v],...], unit:raw|db}])
  clip_envelope(track, slot, points, param="volume"|"pan"|
                "send:0"|<param>, device, unit)  -- Session clips only (Live API limit)
  browse(query, roots=[instruments,audio_effects,midi_effects,drums,sounds,plugins,
         user_library,samples,packs]) | load_device(track, path|query)
  set_param(track, device, param, value|display|db) | set_device_on(track, device, on)
  delete_device(track, device)
  set_cue(name, beat|bar) | delete_cue(name|beat|bar) | clear_cues | transport(action=play|stop|continue|locate, beat|bar)
  set_loop(on, start_bar, end_bar)
  record_master(start_bar, end_bar, name) | record_status | record_abort

Rendering records the master in real time into a new track via Resampling, so a
render takes as long as the music it captures.
"""

mcp = FastMCP("ableton-claude", instructions=INSTRUCTIONS)


@mcp.tool()
def ableton_status() -> dict:
    """Song overview: tempo, cues, every track (kind, volume, devices, clip counts, bar span),
    returns and master chain."""
    return client.call("get_song")


@mcp.tool()
def ableton_command(cmd: str, args: dict | None = None) -> object:
    """Run one ClaudeBridge command. See the server instructions for the command list."""
    return client.call(cmd, args or {})


@mcp.tool()
def ableton_batch(commands: list[dict]) -> list:
    """Run many commands in one Live main-thread tick.
    commands: [{"cmd": "create_midi_clip", "args": {...}}, ...]. Each result has ok/result
    or ok/error; a failure does not stop the rest."""
    return client.batch(commands)


@mcp.tool()
def ableton_reload_bridge() -> dict:
    """Hot-reload the handlers module inside Live after it was reinstalled."""
    return client.call("reload")


@mcp.tool()
def render_start(start_bar: float, end_bar: float, name: str = "Claude Render") -> dict:
    """Start recording the master bus (bars [start_bar, end_bar)) into a new audio track.
    Runs in real time. Poll with render_wait."""
    return client.call("record_master",
                       {"start_bar": start_bar, "end_bar": end_bar, "name": name})


@mcp.tool()
def render_wait(timeout_s: float = 540, analyze: bool = True, target: str = "club",
                sections: list[dict] | None = None, delete_track: bool = True) -> dict:
    """Wait for the running render, then analyze the recorded WAV.
    sections: [{"name", "start_bar", "end_bar"}] relative to the render start (bar 1).
    delete_track removes the render track from the set (the WAV file stays on disk)."""
    deadline = time.time() + timeout_s
    st = client.call("record_status")
    while st["state"] in ("recording", "finalizing") and time.time() < deadline:
        time.sleep(1.0)
        st = client.call("record_status")
    if st["state"] != "done":
        return {"status": st}
    out = {"status": st}
    if analyze:
        tempo = client.call("get_song")["tempo"]
        out["analysis"] = analysis.analyze(st["file"], target=target, sections=sections,
                                           tempo=tempo)
    if delete_track:
        try:
            client.call("delete_track", {"track": st["name"]})
        except client.BridgeError as e:
            out["delete_error"] = str(e)
    return out


@mcp.tool()
def analyze_audio(path: str, target: str = "club", sections: list[dict] | None = None,
                  tempo: float | None = None) -> dict:
    """Measure a WAV/AIFF: LUFS, true peak, crest, band balance, tilt, stereo, and flags.
    target: club (-8 LUFS) | streaming (-14 LUFS)."""
    return analysis.analyze(path, target=target, sections=sections, tempo=tempo)


@mcp.tool()
def compare_to_reference(path: str, reference_path: str) -> dict:
    """Loudness-matched band-by-band comparison of a mix against a reference track."""
    return analysis.compare(path, reference_path)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
