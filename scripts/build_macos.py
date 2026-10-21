"""Build a standalone native macOS .pkg; a drag-to-install .dmg is optional.

Run: python3 scripts/build_macos.py
Requires Xcode Command Line Tools and uv on the build machine only.
Intel Macs (macOS 13+): python3 scripts/build_macos.py --arch x86_64 --dmg. On Apple Silicon this
needs Rosetta (softwareupdate --install-rosetta); it freezes a Python 3.12 / torch 2.2.2 backend from
desktop/intel/requirements.txt, since PyTorch publishes no newer Intel Mac builds.
Optional: --sign-identity 'Developer ID Application: …' --installer-identity 'Developer ID Installer: …'
This script never modifies /Applications or a user's Ableton/AI configuration.
"""
import argparse
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "macos"
DIST = ROOT / "dist"
APP_NAME = "Ableton Claude"
VERSION = "1.2.1"
INTEL_REQUIREMENTS = ROOT / "desktop" / "intel" / "requirements.txt"
# Compiled packages must come as wheels built for macOS 13 or older (see the requirements header).
INTEL_BINARY_ONLY = ("numpy,scipy,torch,torchaudio,cryptography,soundfile,lameenc,pydantic-core,cffi,"
                     "pyyaml,rpds-py,jiter,charset-normalizer,markupsafe,pyinstaller")
# Swift deployment target and the app's minimum macOS, per architecture.
TARGETS = {"arm64": ("14.0", "26.0"), "x86_64": ("13.0", "13.0")}


def run(args, **kwargs):
    print("→ " + " ".join(str(x) for x in args), flush=True)
    subprocess.run([str(x) for x in args], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sign-identity")
    parser.add_argument("--installer-identity")
    parser.add_argument("--dmg", action="store_true", help="also generate a drag-to-install image (without duplicating the .pkg inside)")
    parser.add_argument("--keep-build", action="store_true", help="retain staging files for debugging or --skip-backend; otherwise remove after success")
    parser.add_argument("--skip-backend", action="store_true", help="reuse the previously frozen backend")
    parser.add_argument("--arch", choices=sorted(TARGETS), default=platform.machine(),
                        help="x86_64 builds the Intel installer (macOS 13+)")
    options = parser.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("Build this installer on macOS.")
    global BUILD
    arch = options.arch
    if arch != "arm64":
        BUILD = ROOT / "build" / ("macos-" + arch)
    swift_target, min_macos = TARGETS[arch]
    prefix = ["arch", "-" + arch] if arch != platform.machine() else []
    if prefix and subprocess.run(prefix + ["/usr/bin/python3", "-c", ""], capture_output=True).returncode:
        raise SystemExit("Building for %s on this Mac needs Rosetta: softwareupdate --install-rosetta" % arch)
    BUILD.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(exist_ok=True)
    if shutil.disk_usage(ROOT).free < 3 * 1024 ** 3:
        raise SystemExit("Free at least 3 GiB before packaging; staging needs temporary disk space.")
    if options.skip_backend and not (BUILD / "frozen" / "ableton-claude-backend").is_dir():
        raise SystemExit("No frozen backend to reuse. Build without --skip-backend, or retain a previous build with --keep-build.")
    python = ROOT / "mcp_server" / ".venv" / "bin" / "python"
    if arch == "x86_64":
        python = BUILD / "venv" / "bin" / "python"
    if not options.skip_backend:
        if arch == "x86_64":
            if not python.exists():
                run(["uv", "venv", "--python", "cpython-3.12-macos-x86_64-none", BUILD / "venv"])
            run(["uv", "pip", "install", "--python", python, "-r", INTEL_REQUIREMENTS,
                 "--only-binary", INTEL_BINARY_ONLY, "--python-platform", "x86_64-apple-darwin"],
                env=dict(os.environ, MACOSX_DEPLOYMENT_TARGET=min_macos))
        else:
            run(["uv", "sync", "--directory", ROOT / "mcp_server", "--frozen", "--group", "build"])
        run(prefix + [python, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
             "--name", "ableton-claude-backend", "--distpath", BUILD / "frozen",
             "--workpath", BUILD / "pyinstaller", "--specpath", BUILD,
             "--paths", ROOT / "mcp_server", "--hidden-import", "ableton_claude.server",
             "--collect-submodules", "ableton_claude", "--collect-submodules", "mcp.server",
             "--collect-submodules", "mcp.client", "--copy-metadata", "mcp",
             "--collect-submodules", "anyio", "--collect-all", "beat_this", "--collect-all", "demucs",
             "--collect-all", "torchaudio", "--collect-all", "imageio_ffmpeg",
             "--copy-metadata", "torch", "--copy-metadata", "demucs", "--copy-metadata", "beat-this",
             "--add-data", str(ROOT / "mcp_server" / "ableton_claude" / "briefs") + ":ableton_claude/briefs",
             ROOT / "desktop" / "backend_entry.py"])
    app = BUILD / "product" / (APP_NAME + ".app")
    if app.exists():
        shutil.rmtree(app)
    contents = app / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    macos.mkdir(parents=True)
    resources.mkdir()
    shutil.copytree(BUILD / "frozen" / "ableton-claude-backend", resources / "backend", symlinks=True)
    shutil.copytree(ROOT / "remote_script" / "ClaudeBridge", resources / "ClaudeBridge",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    run(["xcrun", "swiftc", "-O", "-parse-as-library", "-target", arch + "-apple-macosx" + swift_target,
         ROOT / "desktop" / "AppModel.swift", ROOT / "desktop" / "AbletonClaude.swift", "-o", macos / "AbletonClaude"])
    run(["xcrun", "swift", ROOT / "desktop" / "MakeIcon.swift", BUILD / "AppIcon.iconset"])
    run(["iconutil", "-c", "icns", BUILD / "AppIcon.iconset", "-o", resources / "AppIcon.icns"])
    info = {"CFBundleName": APP_NAME, "CFBundleDisplayName": APP_NAME,
            "CFBundleIdentifier": "studio.abletonclaude.desktop", "CFBundleExecutable": "AbletonClaude",
            "CFBundleIconFile": "AppIcon",
            "CFBundlePackageType": "APPL", "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": "100", "LSMinimumSystemVersion": min_macos,
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "Ableton Claude contributors",
            "NSAppleMusicUsageDescription": "Selecionar referências de áudio para treinar seus gêneros.",
            "NSDocumentsFolderUsageDescription": "Acessar as referências e a User Library selecionadas por você.",
            "NSDesktopFolderUsageDescription": "Acessar referências de áudio selecionadas por você."}
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump(info, f)
    identity = options.sign_identity or "-"
    run(["codesign", "--force", "--deep", "--sign", identity, app])
    run(["codesign", "--verify", "--deep", "--strict", app])
    test_data = BUILD / "self-test-data"
    run(prefix + [resources / "backend" / "ableton-claude-backend", "--self-test"],
        env=dict(os.environ, ABLETON_CLAUDE_DATA=str(test_data)))
    pkg = DIST / ("Ableton-Claude-" + VERSION + "-" + arch + ".pkg")
    component_plist = BUILD / "components.plist"
    run(["pkgbuild", "--analyze", "--root", app.parent, component_plist])
    with component_plist.open("rb") as f:
        components = plistlib.load(f)
    for component in components:
        component["BundleIsRelocatable"] = False
    with component_plist.open("wb") as f:
        plistlib.dump(components, f)
    args = ["pkgbuild", "--root", app.parent, "--component-plist", component_plist, "--install-location", "/Applications",
            "--identifier", "studio.abletonclaude.desktop", "--version", VERSION]
    if options.installer_identity:
        args += ["--sign", options.installer_identity]
    run(args + [pkg])
    if not options.dmg:
        if not options.keep_build:
            clean_staging()
        print("\nInstaller: " + str(pkg) + "\nStaging retained: " + str(options.keep_build), flush=True)
        return
    image = BUILD / "image"
    if image.exists():
        shutil.rmtree(image)
    image.mkdir()
    shutil.copytree(app, image / app.name, symlinks=True)
    (image / "Applications").symlink_to("/Applications")
    (image / "Comece aqui.txt").write_text(
        "ABLETON CLAUDE\n\n1. Arraste Ableton Claude para Aplicativos.\n"
        "2. Abra o app em Aplicativos e siga o onboarding guiado.\n"
        "   Na primeira vez o macOS bloqueia (build não notarizado): Ajustes do Sistema →\n"
        "   Privacidade e Segurança → Abrir Mesmo Assim.\n"
        "3. Clique em Preparar ponte. Depois feche (Cmd+Q) e reabra o Ableton Live: ele só\n"
        "   encontra a ponte ao abrir. Selecione ClaudeBridge em Settings → Link, Tempo &\n"
        "   MIDI → Control Surface (Input/Output: None).\n"
        "4. Clique em Conectar ao Claude Desktop e em Escolher pasta de samples.\n"
        "5. Encerre (Cmd+Q) e reabra o Claude Desktop: as ferramentas ableton-claude aparecem.\n"
        "   Trabalhe numa cópia do seu projeto; o Live não tem API de salvar, salve com Cmd+S.\n\n"
        "O primeiro treino baixa os modelos de áudio. Internet é necessária para esses downloads.\n"
        "Dados por usuário: ~/Music/Ableton Claude/\n"
        "Este build local usa assinatura ad hoc e ainda não foi notarizado pela Apple.\n"
        "Compatibilidade deste build: macOS " + min_macos.split(".")[0] + "+, " + ("Intel" if arch == "x86_64" else "Apple Silicon") + ".\n", encoding="utf-8")
    dmg = DIST / ("Ableton-Claude-" + VERSION + "-" + arch + ".dmg")
    if dmg.exists():
        dmg.unlink()
    run(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", image, "-format", "UDZO", dmg])
    shutil.rmtree(image)
    if not options.keep_build:
        clean_staging()
    print("\nInstaller: " + str(pkg) + "\nDisk image: " + str(dmg) +
          "\nStaging retained: " + str(options.keep_build), flush=True)


def clean_staging():
    """Only generated staging folders; release archives and user data are untouched."""
    for name in ("frozen", "product", "pyinstaller", "image", "AppIcon.iconset", "self-test-data"):
        path = BUILD / name
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)


if __name__ == "__main__":
    main()
