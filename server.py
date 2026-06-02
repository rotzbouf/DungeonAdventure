#!/usr/bin/env python3
"""
Dedicated headless game server.

Usage:
    python server.py
    python server.py --port 5555
    python server.py --host 0.0.0.0 --port 5555 --floor 1 --max-players 4
    python server.py --floor 3 --seed 42

The server runs the full authoritative game simulation with no window or audio.
Run it inside screen / tmux or as a systemd service on any headless Linux box.
"""
import argparse
import os
import sys

# Set dummy display/audio drivers BEFORE pygame is imported anywhere.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Ensure the project root is on the path when invoked as "python server.py"
sys.path.insert(0, os.path.dirname(__file__))


def main():
    parser = argparse.ArgumentParser(
        description="DungeonAdventure dedicated server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host",        default="0.0.0.0",
                        help="Bind address (0.0.0.0 = all interfaces)")
    parser.add_argument("--port",        default=5555, type=int,
                        help="TCP port to listen on")
    parser.add_argument("--floor",       default=1,    type=int,
                        help="Dungeon floor to start on (1–∞)")
    parser.add_argument("--seed",        default=None, type=int,
                        help="RNG seed for deterministic dungeon layout")
    parser.add_argument("--max-players", default=4,    type=int,
                        help="Maximum simultaneous players")
    args = parser.parse_args()

    from src.network.server import run_server
    run_server(
        host        = args.host,
        port        = args.port,
        floor       = args.floor,
        seed        = args.seed,
        max_players = args.max_players,
    )


if __name__ == "__main__":
    main()
