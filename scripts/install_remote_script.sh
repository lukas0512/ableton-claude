#!/usr/bin/env bash
# Copy ClaudeBridge into Live's User Library. After the first install, select
# "ClaudeBridge" as a Control Surface in Live > Settings > Link, Tempo & MIDI.
# Later installs only need `ableton_reload_bridge` (handlers.py) — edits to
# __init__.py still require re-selecting the control surface or restarting Live.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
dest="${ABLETON_USER_LIBRARY:-$HOME/Music/Ableton/User Library}/Remote Scripts/ClaudeBridge"
mkdir -p "$dest"
cp "$here/remote_script/ClaudeBridge/"*.py "$dest/"
rm -rf "$dest/__pycache__"
echo "installed -> $dest"
