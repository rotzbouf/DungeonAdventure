#!/usr/bin/env python3
"""
build.py — Package DungeonAdventure as a portable single-file executable.

The game has no external asset files (all graphics are procedural), so the
bundle contains only the Python interpreter, the src/ package tree, and
pygame's SDL2 shared libraries.

Output
------
    dist/DungeonAdventure        (Linux / macOS)
    dist/DungeonAdventure.exe    (Windows)

Usage
-----
    python build.py              # build
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

# Prefer the project venv when available
if SYSTEM == "Windows":
    _venv_py = os.path.join(ROOT, "venv", "Scripts", "python.exe")
else:
    _venv_py = os.path.join(ROOT, "venv", "bin", "python")

PYTHON = _venv_py if os.path.exists(_venv_py) else sys.executable

# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str | os.PathLike], **kwargs) -> None:
    """Print and execute a command; raise on non-zero exit."""
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
    """Remove build/, dist/, *.spec and stray __pycache__ trees."""
    targets = [BUILD_DIR, DIST_DIR]
    for spec in ("DungeonAdventure.spec",):
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

    # Clean __pycache__ inside src/ as a bonus
    for dirpath, dirnames, _ in os.walk(os.path.join(ROOT, "src")):
        for d in dirnames:
            if d == "__pycache__":
                full = os.path.join(dirpath, d)
                shutil.rmtree(full)


def ensure_pyinstaller() -> None:
    """Install PyInstaller into the active environment if it isn't present."""
    result = subprocess.run(
        [PYTHON, "-c", "import PyInstaller"],
        capture_output=True,
    )
    if result.returncode == 0:
        # Report installed version
        ver = subprocess.check_output(
            [PYTHON, "-c",
             "import PyInstaller; print(PyInstaller.__version__)"],
            text=True,
        ).strip()
        print(f"  PyInstaller {ver} — already installed")
    else:
        print("  Installing PyInstaller …")
        _run([PYTHON, "-m", "pip", "install", "--quiet", "pyinstaller"])


def build() -> str:
    """Run PyInstaller and return the path to the finished executable."""
    exe_name = "DungeonAdventure"

    # Every src sub-package as an explicit hidden import.
    # Belt-and-suspenders: PyInstaller's static analysis is good but
    # src.items.item uses intra-method `from … import` which can trip it up.
    hidden = [
        "src",
        "src.game",
        "src.settings",
        "src.skills",
        "src.quests",
        "src.save",
        "src.entities.entity",
        "src.entities.player",
        "src.entities.enemy",
        "src.entities.merchant",
        "src.items.item",
        "src.world.dungeon",
        "src.world.tile",
        "src.ui.hud",
        "src.ui.inventory",
        "src.ui.shop",
        "src.ui.charscreen",
        "src.ui.questlog",
        "src.ui.skillscreen",
        "src.ui.minimap",
        "src.utils.camera",
    ]

    cmd: list[str] = [
        PYTHON, "-m", "PyInstaller",
        "--onefile",
        "--name", exe_name,
        # Bundle the entire pygame package including its SDL2 shared libraries
        "--collect-all", "pygame",
    ]

    for mod in hidden:
        cmd += ["--hidden-import", mod]

    # Strip debug symbols on Linux/macOS to reduce binary size (~10-15%)
    if SYSTEM in ("Linux", "Darwin"):
        cmd.append("--strip")

    # Suppress the console window on Windows (game opens its own SDL window)
    if SYSTEM == "Windows":
        cmd.append("--noconsole")

    # Entry point
    cmd.append(os.path.join(ROOT, "main.py"))

    _run(cmd, cwd=ROOT)

    # Locate the output
    exe = os.path.join(DIST_DIR, exe_name)
    if SYSTEM == "Windows":
        exe += ".exe"

    if not os.path.isfile(exe):
        sys.exit(
            f"\n✗  Expected executable not found at {exe!r}.\n"
            "   Check PyInstaller output above for errors."
        )

    return exe


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build DungeonAdventure as a portable single-file executable.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage")[1].lstrip("\n").rstrip(),
    )
    ap.add_argument(
        "--clean",
        action="store_true",
        help="Remove build artefacts before building",
    )
    ap.add_argument(
        "--clean-only",
        action="store_true",
        help="Remove build artefacts and exit without building",
    )
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
    exe = build()

    size = _sizeof_fmt(exe)
    rel  = os.path.relpath(exe, ROOT)

    print(f"""
── Done ──────────────────────────────────────────────────────
  Executable : {rel}
  Size       : {size}
  Platform   : {SYSTEM} ({platform.machine()})

Run it:
  ./{rel}
""")


if __name__ == "__main__":
    main()
