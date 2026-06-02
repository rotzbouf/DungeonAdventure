import argparse
import sys
import time
import pygame
from src.game import Game


def main():
    parser = argparse.ArgumentParser(
        description="DungeonAdventure",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--connect", metavar="HOST:PORT", default=None,
                        help="Connect to a multiplayer server, e.g. localhost:5555")
    parser.add_argument("--name", default="Adventurer",
                        help="Your player name shown to other players")
    args = parser.parse_args()

    pygame.init()
    pygame.font.init()

    net_client = None

    if args.connect:
        # Parse host:port
        try:
            host, port_str = args.connect.rsplit(":", 1)
            port = int(port_str)
        except ValueError:
            print(f"Bad --connect value '{args.connect}' — expected HOST:PORT")
            sys.exit(1)

        from src.network.client import NetworkClient
        print(f"Connecting to {host}:{port} as '{args.name}' …")
        net_client = NetworkClient(host, port, args.name)

        # Wait up to 8 s for the welcome handshake
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            if net_client.connected:
                break
            if net_client.error:
                print(f"Connection failed: {net_client.error}")
                sys.exit(1)
            time.sleep(0.05)
        else:
            print("Connection timed out — is the server running?")
            sys.exit(1)

        print(f"Connected!  pid={net_client.pid}")

    game = Game(net_client=net_client)
    game.run()


if __name__ == "__main__":
    main()
