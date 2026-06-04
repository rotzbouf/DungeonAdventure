#!/usr/bin/env python3
"""
build.py — Package DungeonAdventure as a portable single-file executable.

Output
------
    dist/DungeonAdventure        (Linux / macOS)
    dist/DungeonAdventure.exe    (Windows)

Usage
-----
    python build.py              # build client
    python build.py --server     # build dedicated server instead
    python build.py --clean      # wipe build artefacts then build
    python build.py --clean-only # just wipe, don't build
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT      = os.path.dirname(os.path.abspath(__file__))
DIST_DIR  = os.path.join(ROOT, "dist")
BUILD_DIR = os.path.join(ROOT, "build")
SYSTEM    = platform.system()   # "Linux" | "Windows" | "Darwin"

if SYSTEM == "Windows":
    _venv_py = os.path.join(ROOT, "venv", "Scripts", "python.exe")
else:
    _venv_py = os.path.join(ROOT, "venv", "bin", "python")

PYTHON = _venv_py if os.path.exists(_venv_py) else sys.executable

# PyInstaller data-file separator is : on *nix, ; on Windows
_SEP = ";" if SYSTEM == "Windows" else ":"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str | os.PathLike], **kwargs) -> None:
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)


def _sizeof_fmt(path: str) -> str:
    size = os.path.getsize(path)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# ── Steps ─────────────────────────────────────────────────────────────────────

def clean() -> None:
    targets = [BUILD_DIR, DIST_DIR]
    for spec in ("DungeonAdventure.spec", "DungeonAdventure-Server.spec"):
        p = os.path.join(ROOT, spec)
        if os.path.exists(p):
            targets.append(p)
    for target in targets:
        if os.path.isdir(target):
            shutil.rmtree(target)
            print(f"  removed  {os.path.relpath(target, ROOT)}/")
        elif os.path.isfile(target):
            os.remove(target)
            print(f"  removed  {os.path.relpath(target, ROOT)}")
    for dirpath, dirnames, _ in os.walk(os.path.join(ROOT, "src")):
        for d in dirnames:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, d))


def ensure_pyinstaller() -> None:
    result = subprocess.run([PYTHON, "-c", "import PyInstaller"], capture_output=True)
    if result.returncode == 0:
        ver = subprocess.check_output(
            [PYTHON, "-c", "import PyInstaller; print(PyInstaller.__version__)"],
            text=True,
        ).strip()
        print(f"  PyInstaller {ver} — already installed")
    else:
        print("  Installing PyInstaller …")
        _run([PYTHON, "-m", "pip", "install", "--quiet", "pyinstaller"])


def build_client() -> str:
    """Build the game client.  Returns path to the executable."""
    exe_name = "DungeonAdventure"

    cmd: list[str] = [
        PYTHON, "-m", "PyInstaller",
        "--onefile",
        "--name", exe_name,
        "--collect-all", "pygame",   # SDL2 shared libs + all pygame submodules
        "--collect-all", "src",      # every src.* module (avoids manual listing)
        # Bundle the assets/ directory (sprites, tiles, town facades)
        "--add-data", f"assets{_SEP}assets",
    ]

    if SYSTEM in ("Linux", "Darwin"):
        cmd.append("--strip")

    if SYSTEM == "Windows":
        cmd.append("--noconsole")   # no cmd.exe window; SDL creates its own
    elif SYSTEM == "Darwin":
        cmd.append("--windowed")    # create a proper .app bundle

    cmd.append(os.path.join(ROOT, "main.py"))
    _run(cmd, cwd=ROOT)

    exe = os.path.join(DIST_DIR, exe_name)
    if SYSTEM == "Windows":
        exe += ".exe"
    if not os.path.isfile(exe) and SYSTEM == "Darwin":
        # --windowed produces a .app directory
        app = os.path.join(DIST_DIR, exe_name + ".app")
        if os.path.isdir(app):
            return app
    if not os.path.isfile(exe):
        sys.exit(f"\n✗  Expected executable not found at {exe!r}.\n")
    return exe


def build_server() -> str:
    """Build the headless dedicated server.  Returns path to the executable."""
    exe_name = "DungeonAdventure-Server"

    cmd: list[str] = [
        PYTHON, "-m", "PyInstaller",
        "--onefile",
        "--name", exe_name,
        "--collect-all", "pygame",
        "--collect-all", "src",
        # Server does NOT need the assets/ directory
    ]

    if SYSTEM in ("Linux", "Darwin"):
        cmd.append("--strip")
    # Keep console on all platforms — server outputs logs to terminal

    cmd.append(os.path.join(ROOT, "server.py"))
    _run(cmd, cwd=ROOT)

    exe = os.path.join(DIST_DIR, exe_name)
    if SYSTEM == "Windows":
        exe += ".exe"
    if not os.path.isfile(exe):
        sys.exit(f"\n✗  Expected executable not found at {exe!r}.\n")
    return exe


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build DungeonAdventure as a portable single-file executable.",
    )
    ap.add_argument("--server",     action="store_true", help="Build the dedicated server instead of the client")
    ap.add_argument("--clean",      action="store_true", help="Remove build artefacts before building")
    ap.add_argument("--clean-only", action="store_true", help="Remove build artefacts and exit without building")
    args = ap.parse_args()

    if args.clean or args.clean_only:
        print("\n── Cleaning ─────────────────────────────────────────────────")
        clean()
        if args.clean_only:
            print("\n✓  Done.")
            return

    print("\n── Checking dependencies ────────────────────────────────────")
    ensure_pyinstaller()

    print("\n── Building ─────────────────────────────────────────────────")
    if args.server:
        exe = build_server()
        label = "Server"
    else:
        exe = build_client()
        label = "Client"

    size = _sizeof_fmt(exe) if os.path.isfile(exe) else "N/A (bundle)"
    rel  = os.path.relpath(exe, ROOT)

    print(f"""
── Done ──────────────────────────────────────────────────────
  Target     : {label}
  Executable : {rel}
  Size       : {size}
  Platform   : {SYSTEM} ({platform.machine()})

Run it:
  ./{rel}
""")


if __name__ == "__main__":
    main()
