"""Build a small native development app using this checkout's Python environment.

Run with python3 scripts/build_desktop_dev.py. This is for local testing, not
distribution: the app depends on the checkout and its existing .venv. It uses the
same user data as the installed app unless ABLETON_CLAUDE_DATA is set at launch.
"""
from pathlib import Path
import platform
import plistlib
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'darwin':
        raise SystemExit('This development app requires macOS.')
    python = ROOT / 'mcp_server' / '.venv' / 'bin' / 'python'
    if not python.is_file():
        raise SystemExit('Prepare mcp_server/.venv with uv sync before building.')
    subprocess.run([str(python), '-c', 'import ableton_claude.desktop'],
                   cwd=ROOT / 'mcp_server', check=True)
    app = ROOT / 'build' / 'desktop-dev' / 'Ableton Claude Dev.app'
    contents = app / 'Contents'
    binary = contents / 'MacOS' / 'AbletonClaude'
    backend = contents / 'Resources' / 'backend' / 'ableton-claude-backend'
    binary.parent.mkdir(parents=True, exist_ok=True)
    backend.parent.mkdir(parents=True, exist_ok=True)
    backend.write_text('#!/bin/sh\nexport PYTHONPATH=' + shlex.quote(str(ROOT / 'mcp_server')) +
                       '\nexec ' + shlex.quote(str(python)) + ' -m ableton_claude.desktop "$@"\n')
    backend.chmod(0o755)
    # Copy current bridge source; signing rejects links outside an app bundle.
    bridge = contents / 'Resources' / 'ClaudeBridge'
    if bridge.is_symlink():
        bridge.unlink()
    shutil.copytree(ROOT / 'remote_script' / 'ClaudeBridge', bridge, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    subprocess.run(['xcrun', 'swiftc', '-O', '-parse-as-library', '-target',
                    platform.machine() + '-apple-macosx14.0', str(ROOT / 'desktop' / 'AppModel.swift'),
                    str(ROOT / 'desktop' / 'AbletonClaude.swift'), '-o', str(binary)], check=True)
    with (contents / 'Info.plist').open('wb') as file:
        plistlib.dump({'CFBundleName': 'Ableton Claude Dev',
                      'CFBundleDisplayName': 'Ableton Claude Dev',
                      'CFBundleIdentifier': 'studio.abletonclaude.desktop.dev',
                      'CFBundleExecutable': 'AbletonClaude', 'CFBundlePackageType': 'APPL',
                      'CFBundleShortVersionString': '1.0.0', 'CFBundleVersion': '100',
                      'LSMinimumSystemVersion': '26.0', 'NSHighResolutionCapable': True}, file)
    subprocess.run(['codesign', '--force', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--strict', str(app)], check=True)
    print(f'Development app: {app}\nRequires this checkout and .venv; not a standalone release.')


if __name__ == '__main__':
    main()
