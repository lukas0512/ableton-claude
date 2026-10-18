"""Verify the packaged backend without Python, uv or ffmpeg on its PATH.

Run from mcp_server: uv run python ../scripts/smoke_desktop.py '/path/to/backend'
Only writes to a temporary test directory; never changes Live or client settings.
"""
import asyncio
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
import soundfile as sf
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def train(backend, root, env):
    folder = root / "References" / "Test Genre"
    folder.mkdir(parents=True)
    sr, seconds, bpm = 22050, 32, 120
    t = np.arange(sr * seconds) / sr
    beat = 60 / bpm
    x = np.zeros_like(t)
    for step in np.arange(0, seconds - 0.25, beat):
        local = t - step
        x += 0.45 * np.sin(2 * np.pi * 55 * local) * np.exp(-np.maximum(local, 0) / 0.05) * ((local >= 0) & (local < 0.2))
        hat = t - (step + beat / 2)
        x += 0.04 * np.sin(2 * np.pi * 6500 * hat) * np.exp(-np.maximum(hat, 0) / 0.02) * ((hat >= 0) & (hat < 0.08))
    x += 0.10 * np.sin(2 * np.pi * 65.406 * t)
    for hz in [261.626, 311.127, 391.995]:
        x += 0.025 * np.sin(2 * np.pi * hz * t)
    sf.write(folder / "reference.wav", np.column_stack((x, x)), sr)
    with (root / "training.log").open("w+") as logs:
        process = subprocess.Popen([backend, "--desktop"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=logs, text=True, env=env, cwd=root)
        def request(method, params):
            process.stdin.write(json.dumps({"id": 1, "method": method, "params": params}) + "\n")
            process.stdin.flush()
            line = process.stdout.readline()
            assert line, "training backend exited"
            return json.loads(line)
        try:
            result = request("learn", {"folder": str(folder.parent)})
            assert "result" in result, result
            deadline = time.monotonic() + 360
            latest = None
            while time.monotonic() < deadline:
                snapshot = request("snapshot", {"folder": str(folder.parent)})["result"]
                job = snapshot["job"]
                message = (job.get("log") or [job["state"]])[-1]
                if message != latest:
                    print(message, flush=True)
                    latest = message
                if job["state"] not in ("running", "queued"):
                    assert job["state"] == "done", job
                    profile = json.loads((Path(env["ABLETON_CLAUDE_DATA"]) / "knowledge" / "genres" / "test_genre.profile.json").read_text())
                    assert profile.get("ear"), {"job": job, "log": logs.read()}
                    print("Full genre training, neural beat tracking and Demucs: ok", flush=True)
                    return
                time.sleep(1)
            raise TimeoutError("full training did not finish within 6 minutes")
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)


async def check(backend, root, full_training=False):
    data = root / "User Data"
    profile_dir = data / "knowledge" / "genres"
    profile_dir.mkdir(parents=True)
    (profile_dir / "smoke_genre.profile.json").write_text(json.dumps({"genre": "Smoke Genre", "n_tracks": 2}))
    library = root / "User Library"
    library.mkdir()
    env = dict(os.environ, PATH="/usr/bin:/bin:/usr/sbin:/sbin", ABLETON_CLAUDE_DATA=str(data))
    requests = [{"id": 1, "method": "snapshot"},
                {"id": 2, "method": "install_bridge", "params": {"library": str(library)}},
                {"id": 3, "method": "mcp_call", "params": {"tool": "producer_brief"}}]
    process = subprocess.run([backend, "--desktop"],
                             input="".join(json.dumps(r) + "\n" for r in requests),
                             text=True, capture_output=True, env=env, cwd=root, timeout=40)
    assert process.returncode == 0, process.stderr[-1000:]
    results = {r["id"]: r for r in (json.loads(line) for line in process.stdout.splitlines())}
    assert results[1]["result"]["genres"][0]["genre"] == "Smoke Genre", results
    assert "installed" in results[2]["result"], results
    assert "Smoke Genre" in results[3]["result"]["data"], results
    assert (library / "Remote Scripts" / "ClaudeBridge" / "handlers.py").exists()

    sr = 44100
    t = np.arange(sr * 3) / sr
    wave = 0.12 * np.sin(2 * np.pi * 110 * t)
    audio = root / "test.wav"
    sf.write(audio, np.column_stack((wave, wave)), sr)
    params = StdioServerParameters(command=backend, args=["--mcp"], env=env, cwd=str(root))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {"learn_genres", "learn_genres_status", "list_genres", "producer_brief"} <= names
            assert "Smoke Genre" in (init.instructions or "")
            brief = await session.call_tool("producer_brief", {})
            assert not brief.isError and "Smoke Genre" in brief.content[0].text
            analysis = await session.call_tool("analyze_audio", {"path": str(audio)})
            assert not analysis.isError, analysis
            print(json.dumps({"desktop_protocol": "ok", "bridge_install": "ok",
                              "mcp_tools": len(names), "user_genre_context": "ok",
                              "bundled_audio_analysis": "ok"}))
    if full_training:
        train(backend, root, env)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="ableton-claude-smoke-") as folder:
        asyncio.run(check(str(Path(sys.argv[1]).resolve()), Path(folder), "--train" in sys.argv))
