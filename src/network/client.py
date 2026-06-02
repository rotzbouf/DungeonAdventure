"""
Thread-safe network client and client-side rendering proxies.

NetworkClient runs asyncio in a background daemon thread.  The main
Pygame thread calls send_input() and reads latest_state without blocking.

GhostEnemy / GhostItem / RemotePlayer are minimal rendering proxies built
from server state snapshots; they match the draw(surface, camera) interface
of the real game entities so _draw_world() needs no changes.
"""
from __future__ import annotations

import asyncio
import math
import threading
import time

import pygame

from src.network.protocol import pack, Unpacker
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT


# ── Rendering proxies ─────────────────────────────────────────────────────────

_ENEMY_COLORS: dict[str, tuple] = {
    "Skeleton":     (180, 180, 200),
    "Orc":          (100, 160,  80),
    "Demon":        (200,  50,  50),
    "Troll":        ( 80, 140,  60),
    "Vampire":      (160,  50, 160),
    "Wraith":       ( 80,  80, 160),
    "Lich":         (200, 150, 255),
    "DemonLord":    (220,  40,  40),
    "StoneGolem":   (150, 140, 120),
    "VampireLord":  (190,  60, 190),
    "ElderDragon":  (220, 100,  30),
    "IronColossus": (120, 140, 180),
}

_REMOTE_PLAYER_COLORS = [
    (100, 180, 255),
    (255, 180, 100),
    (100, 255, 130),
    (255, 100, 180),
]


class GhostEnemy:
    """Client-side enemy proxy — state comes from server snapshots."""

    def __init__(self, eid: int, kind: str,
                 x: float, y: float, hp: float, max_hp: float,
                 is_boss: bool = False, is_elite: bool = False):
        self.net_id  = eid
        self.kind    = kind
        self.x       = x
        self.y       = y
        self.hp      = hp
        self.max_hp  = max_hp
        self.alive   = True
        self.is_boss  = is_boss
        self.is_elite = is_elite
        self.size    = 36 if is_boss else 28
        self.rect    = pygame.Rect(0, 0, self.size, self.size)
        self._status: dict = {}
        self._sync_rect()

        self._font = pygame.font.SysFont("monospace", 10)

    def _sync_rect(self):
        self.rect.centerx = round(self.x)
        self.rect.centery = round(self.y)

    def draw(self, surface: pygame.Surface, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y - camera.y)
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        if not (-50 < sx < SCREEN_WIDTH + 50 and -50 < sy < play_h + 50):
            return

        col = _ENEMY_COLORS.get(self.kind, (180, 60, 60))
        hw  = self.size // 2

        # Shadow
        sh = pygame.Surface((self.size + 6, 6), pygame.SRCALPHA)
        sh.fill((0, 0, 0, 50))
        surface.blit(sh, (sx - hw - 3, sy + hw - 2))

        # Body
        pygame.draw.rect(surface, col,
                         (sx - hw, sy - hw, self.size, self.size))
        if self.is_elite:
            pygame.draw.rect(surface, (255, 200, 0),
                             (sx - hw, sy - hw, self.size, self.size), 2)
        elif self.is_boss:
            pygame.draw.rect(surface, (255, 80, 30),
                             (sx - hw, sy - hw, self.size, self.size), 3)
        else:
            pygame.draw.rect(surface, (0, 0, 0),
                             (sx - hw, sy - hw, self.size, self.size), 1)

        # HP bar
        bar_w  = self.size + 8
        bar_x  = sx - bar_w // 2
        bar_y  = sy - hw - 10
        hp_frac = max(0.0, self.hp / max(1.0, self.max_hp))
        pygame.draw.rect(surface, (50, 10, 10), (bar_x, bar_y, bar_w, 5))
        if hp_frac > 0:
            bar_col = (220, 160, 0) if self.is_elite else (220, 40, 40)
            pygame.draw.rect(surface, bar_col,
                             (bar_x, bar_y, int(bar_w * hp_frac), 5))
        pygame.draw.rect(surface, (80, 20, 20), (bar_x, bar_y, bar_w, 5), 1)


class GhostItem:
    """Client-side item proxy — just a coloured dot with a subtle glow."""

    def __init__(self, iid: int, kind: str, x: float, y: float):
        self.net_id   = iid
        self.kind     = kind
        self.x        = x
        self.y        = y
        self.size     = 14
        self.rect     = pygame.Rect(0, 0, self.size, self.size)
        self.rect.center = (round(x), round(y))
        self.collected = False

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface, camera):
        sx = int(self.x - camera.x)
        sy = int(self.y - camera.y)
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        if not (-20 < sx < SCREEN_WIDTH + 20 and -20 < sy < play_h + 20):
            return
        col = (255, 210, 30) if self.kind == "GoldPile" else (80, 200, 255)
        # Glow
        gs = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*col, 60), (10, 10), 10)
        surface.blit(gs, (sx - 10, sy - 10))
        pygame.draw.circle(surface, col, (sx, sy), 5)
        pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 5, 1)


class RemotePlayer:
    """Another player, received from server and rendered in the local world."""

    def __init__(self, pid: int, name: str):
        self.pid      = pid
        self.name     = name
        self.x        = 0.0
        self.y        = 0.0
        self.hp       = 100.0
        self.max_hp   = 100.0
        self.alive    = True
        self.size     = 24
        self.level    = 1
        self.rect     = pygame.Rect(0, 0, self.size, self.size)
        self._font    = pygame.font.SysFont("monospace", 11)

    def update_from(self, data: dict):
        self.x      = float(data["x"])
        self.y      = float(data["y"])
        self.hp     = float(data["hp"])
        self.max_hp = float(data["max_hp"])
        self.alive  = data.get("alive", True)
        self.name   = data.get("name", self.name)
        self.level  = data.get("level", self.level)
        self.rect.centerx = round(self.x)
        self.rect.centery = round(self.y)

    def draw(self, surface: pygame.Surface, camera):
        if not self.alive:
            return
        sx = int(self.x - camera.x)
        sy = int(self.y - camera.y)
        play_h = SCREEN_HEIGHT - HUD_HEIGHT
        if not (-40 < sx < SCREEN_WIDTH + 40 and -40 < sy < play_h + 40):
            return

        col = _REMOTE_PLAYER_COLORS[self.pid % len(_REMOTE_PLAYER_COLORS)]
        hw  = self.size // 2

        # Shadow
        sh = pygame.Surface((self.size + 6, 6), pygame.SRCALPHA)
        sh.fill((0, 0, 0, 50))
        surface.blit(sh, (sx - hw - 3, sy + hw - 2))

        # Body
        pygame.draw.rect(surface, col, (sx - hw, sy - hw, self.size, self.size))
        pygame.draw.rect(surface, (255, 255, 255),
                         (sx - hw, sy - hw, self.size, self.size), 2)

        # HP bar
        bar_w   = self.size + 12
        bar_x   = sx - bar_w // 2
        bar_y   = sy - hw - 12
        hp_frac = max(0.0, self.hp / max(1.0, self.max_hp))
        pygame.draw.rect(surface, (50, 0, 0), (bar_x, bar_y, bar_w, 5))
        if hp_frac > 0:
            pygame.draw.rect(surface, (80, 220, 80),
                             (bar_x, bar_y, int(bar_w * hp_frac), 5))

        # Name + level label
        label = self._font.render(
            f"{self.name} Lv{self.level}", True, (220, 220, 220))
        # Shadow
        sh2 = label.copy()
        sh2.fill((0, 0, 0, 160), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(sh2, (sx - label.get_width() // 2 + 1,
                           bar_y - label.get_height() - 1))
        surface.blit(label, (sx - label.get_width() // 2,
                              bar_y - label.get_height() - 2))


# ── NetworkClient ─────────────────────────────────────────────────────────────

class NetworkClient:
    """
    Connects to a GameServer.  asyncio runs in a background daemon thread;
    the main Pygame thread communicates via thread-safe properties.
    """

    def __init__(self, host: str, port: int,
                 player_name: str = "Adventurer"):
        self.host  = host
        self.port  = port
        self.name  = player_name[:24]
        self.pid:  int | None = None
        self.connected = False
        self.error: str | None = None

        # Shared state (all accesses protected by _lock)
        self._lock    = threading.Lock()
        self._latest: dict | None = None
        self._pending: list[dict] = []   # inputs to send
        self._events:  list[dict] = []   # unread events
        self._chat:    list[str]  = []   # unread chat lines

        self._loop   = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="net-client")
        self._thread.start()

    # ── Main-thread API ───────────────────────────────────────────────────────

    def send_input(self, inp: dict):
        """Queue an input packet for the next send window (non-blocking)."""
        inp["type"] = "input"
        with self._lock:
            # Keep only the latest input; old ones are redundant
            self._pending = [inp]

    @property
    def latest_state(self) -> dict | None:
        with self._lock:
            return self._latest

    def pop_events(self) -> list[dict]:
        with self._lock:
            out = self._events[:]
            self._events.clear()
            return out

    def pop_chat(self) -> list[str]:
        with self._lock:
            out = self._chat[:]
            self._chat.clear()
            return out

    def close(self):
        self._loop.call_soon_threadsafe(self._loop.stop)

    # ── Background asyncio thread ─────────────────────────────────────────────

    def _run(self):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect())
        except Exception as exc:
            with self._lock:
                self.error = str(exc)
        finally:
            self.connected = False

    async def _connect(self):
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
        except Exception as exc:
            with self._lock:
                self.error = f"Cannot connect to {self.host}:{self.port} — {exc}"
            return

        # Send join handshake
        writer.write(pack({"type": "join", "name": self.name}))
        await writer.drain()

        unpack = Unpacker()

        # Wait for welcome
        while True:
            raw = await asyncio.wait_for(reader.read(4096), timeout=8.0)
            if not raw:
                raise ConnectionError("Server closed connection before welcome")
            for msg in unpack.feed(raw):
                if msg.get("type") == "welcome":
                    self.pid = msg["pid"]
                    with self._lock:
                        self._latest  = msg
                        self.connected = True   # set under lock so reader sees it
                    await asyncio.gather(
                        self._recv_loop(reader, unpack),
                        self._send_loop(writer),
                    )
                    return
                if msg.get("type") == "error":
                    with self._lock:
                        self.error = msg.get("text", "Server refused connection")
                    return

    async def _recv_loop(self, reader: asyncio.StreamReader, unpack: Unpacker):
        while True:
            data = await reader.read(16384)
            if not data:
                break
            for msg in unpack.feed(data):
                mtype = msg.get("type")
                if mtype == "state":
                    with self._lock:
                        self._latest = msg
                        if msg.get("events"):
                            self._events.extend(msg["events"])
                elif mtype == "chat":
                    with self._lock:
                        self._chat.append(msg.get("text", ""))

    async def _send_loop(self, writer: asyncio.StreamWriter):
        while True:
            with self._lock:
                msgs = self._pending[:]
                self._pending.clear()
            for msg in msgs:
                writer.write(pack(msg))
            if msgs:
                try:
                    await writer.drain()
                except Exception:
                    return
            await asyncio.sleep(1.0 / 60)   # 60 Hz send cadence
