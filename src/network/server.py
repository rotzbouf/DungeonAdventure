"""
Headless authoritative game server.

Usage (via server.py entry point):
    python server.py [--host 0.0.0.0] [--port 5555] [--floor 1] [--max-players 4]

The server owns the entire simulation: enemy AI, combat resolution,
item pickup, and loot drops.  Clients send compact input frames; the
server broadcasts a full world-state snapshot every tick (20 TPS).
"""
from __future__ import annotations

import asyncio
import math
import os
import random
import time

# Must be set before pygame is imported anywhere in this process.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()

from src.entities.player import Player
from src.entities.enemy import (
    get_enemy_types,
    Lich, DemonLord, StoneGolem, VampireLord, ElderDragon, IronColossus,
)
from src.items.item import (
    random_item, GoldPile, TreasureChest, _ilvl_and_mult,
    random_equip, QUALITY_RARE, QUALITY_UNIQUE,
)
from src.world.dungeon import Dungeon
from src.world.tile import set_theme
from src.settings import TILE_SIZE, BOSS_FLOOR_INTERVAL, ARROW_MAX_RANGE
from src.network.protocol import pack, Unpacker

TICK_RATE    = 20           # ticks per second
TICK_DT      = 1.0 / TICK_RATE
MAX_PLAYERS  = 4


# ── Key-state adapter ─────────────────────────────────────────────────────────

class _NetKeys:
    """
    Wraps a string-keyed input dict so it responds to pygame key constants,
    letting Player.update() / try_attack() work without a real keyboard.
    """
    __slots__ = ("_m",)

    def __init__(self, inp: dict):
        self._m = {
            pygame.K_w:     inp.get("up",    False),
            pygame.K_UP:    inp.get("up",    False),
            pygame.K_s:     inp.get("down",  False),
            pygame.K_DOWN:  inp.get("down",  False),
            pygame.K_a:     inp.get("left",  False),
            pygame.K_LEFT:  inp.get("left",  False),
            pygame.K_d:     inp.get("right", False),
            pygame.K_RIGHT: inp.get("right", False),
        }

    def __getitem__(self, key: int) -> bool:
        return self._m.get(key, False)


class _NullCamera:
    """Zero-offset camera stub for server-side Player.update() calls."""
    x = 0.0
    y = 0.0

    def update(self, *a, **kw):
        pass

    def apply(self, rect):
        return rect


_NULL_CAM = _NullCamera()


# ── ServerGame ────────────────────────────────────────────────────────────────

class ServerGame:
    """
    Full authoritative dungeon simulation — no rendering.
    All game state lives here; the GameServer drives it via tick().
    """

    def __init__(self, floor: int = 1, seed: int | None = None):
        self.floor   = floor
        self.seed    = seed if seed is not None else random.randint(1, 2 ** 30)
        self._tick_n = 0

        set_theme(floor)
        self.dungeon = Dungeon(level=floor, seed=self.seed)

        self.players:  dict[int, Player]  = {}
        self._inputs:  dict[int, dict]    = {}
        self.enemies:  list               = []
        self.items:    list               = []
        self.chests:   list               = []
        self.projectiles: list            = []

        self._spawn_entities()
        print(f"[game] Floor {floor} ready — seed={self.seed}, "
              f"{len(self.enemies)} enemies, {len(self.items)} items")

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _spawn_entities(self):
        etypes = get_enemy_types(self.floor)
        for tx, ty in self.dungeon.enemy_spawns:
            e = random.choice(etypes)(
                tx * TILE_SIZE + TILE_SIZE // 2,
                ty * TILE_SIZE + TILE_SIZE // 2,
            )
            e.scale_to_level(self.floor)
            if random.random() < 0.15:
                e.make_elite()
            self.enemies.append(e)

        if (self.floor > 0 and self.floor % BOSS_FLOOR_INTERVAL == 0
                and self.dungeon.rooms):
            _BOSSES = [Lich, DemonLord, StoneGolem,
                       VampireLord, ElderDragon, IronColossus]
            bidx = (self.floor // BOSS_FLOOR_INTERVAL - 1) % len(_BOSSES)
            room = self.dungeon.rooms[-1]
            bx   = room.center[0] * TILE_SIZE + TILE_SIZE // 2
            by   = room.center[1] * TILE_SIZE + TILE_SIZE // 2
            boss = _BOSSES[bidx](float(bx), float(by))
            boss.scale_to_level(self.floor)
            self.enemies.append(boss)

        self.items  = [random_item(tx, ty, self.floor, floor=self.floor)
                       for tx, ty in self.dungeon.item_spawns]
        self.chests = [TreasureChest(tx, ty)
                       for tx, ty in self.dungeon.chest_positions]

    # ── Player management ─────────────────────────────────────────────────────

    def add_player(self, pid: int, name: str) -> Player:
        sx, sy = self.dungeon.player_start
        p = Player(float(sx), float(sy))
        p.net_name = name    # type: ignore[attr-defined]
        p.net_pid  = pid     # type: ignore[attr-defined]
        self.players[pid]  = p
        self._inputs[pid]  = {}
        return p

    def remove_player(self, pid: int):
        self.players.pop(pid, None)
        self._inputs.pop(pid, None)

    def set_input(self, pid: int, inp: dict):
        self._inputs[pid] = inp

    # ── Simulation tick ───────────────────────────────────────────────────────

    def tick(self, dt: float) -> list[dict]:
        """Advance the simulation by *dt* seconds. Returns a list of events."""
        self._tick_n += 1
        events: list[dict] = []
        alive_players = [p for p in self.players.values() if p.is_alive()]

        # Move players
        for pid, player in self.players.items():
            if not player.is_alive():
                continue
            inp      = self._inputs.get(pid, {})
            net_keys = _NetKeys(inp)
            player.update(dt, self.dungeon, _NULL_CAM, net_keys=net_keys)

        # Enemy AI — each enemy targets the nearest alive player
        if alive_players:
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                nearest = min(alive_players,
                              key=lambda p: math.hypot(enemy.x - p.x,
                                                        enemy.y - p.y))
                enemy.update(dt, nearest, self.dungeon)

        # Player melee attacks
        for pid, player in self.players.items():
            if not player.is_alive():
                continue
            inp = self._inputs.get(pid, {})
            if inp.get("attack"):
                net_keys = _NetKeys(inp)
                hits = player.try_attack(self.enemies, net_keys=net_keys)
                for enemy in hits:
                    raw     = int(player.attack + random.randint(-2, 4))
                    is_crit = random.uniform(0, 100) < player.crit_chance
                    if is_crit:
                        raw = int(raw * 2)
                    dmg = enemy.take_damage(raw)
                    events.append({"k": "hit", "eid": id(enemy),
                                   "dmg": dmg, "crit": is_crit})
                    if player.life_steal > 0:
                        player.heal(max(1, int(dmg * player.life_steal / 100)))
                    if not enemy.alive:
                        leveled = player.gain_xp(enemy.XP_REWARD)
                        new_items = self._drop_loot(enemy, player)
                        self.items.extend(new_items)
                        events.append({"k": "kill", "eid": id(enemy),
                                       "xp": enemy.XP_REWARD, "leveled": leveled,
                                       "pid": pid})

        # Projectiles
        for proj in self.projectiles:
            if not proj["alive"]:
                continue
            proj["x"] += proj["vx"] * dt
            proj["y"] += proj["vy"] * dt
            proj["traveled"] += math.hypot(proj["vx"], proj["vy"]) * dt
            if proj["traveled"] > ARROW_MAX_RANGE:
                proj["alive"] = False
                continue
            tx = int(proj["x"] // TILE_SIZE)
            ty = int(proj["y"] // TILE_SIZE)
            if not self.dungeon.is_walkable(tx, ty):
                proj["alive"] = False
                continue
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if enemy.rect.collidepoint(proj["x"], proj["y"]):
                    dmg = enemy.take_damage(proj["damage"])
                    proj["alive"] = False
                    events.append({"k": "proj_hit", "eid": id(enemy), "dmg": dmg})
                    if not enemy.alive:
                        owner = self.players.get(proj.get("owner_pid"))
                        if owner:
                            leveled = owner.gain_xp(enemy.XP_REWARD)
                            self.items.extend(self._drop_loot(enemy, owner))
                            events.append({"k": "kill", "eid": id(enemy),
                                           "xp": enemy.XP_REWARD,
                                           "leveled": leveled,
                                           "pid": proj["owner_pid"]})
                    break
        self.projectiles = [p for p in self.projectiles if p["alive"]]

        # Item pickup
        for item in self.items:
            if item.collected:
                continue
            item.update(dt)
            for player in alive_players:
                if player.rect.colliderect(item.rect):
                    from src.items.item import GoldPile as _GP
                    if isinstance(item, _GP):
                        player.gold += item.amount
                        item.collected = True
                        events.append({"k": "gold", "pid": getattr(player, "net_pid", -1),
                                       "amount": item.amount})
                    else:
                        item.collect(player)
                        events.append({"k": "item", "pid": getattr(player, "net_pid", -1)})
                    break
        self.items = [i for i in self.items if not i.collected]

        # Chest opening
        for chest in self.chests:
            chest.update(dt)
            if not chest.opened:
                for player in alive_players:
                    if player.rect.colliderect(chest.rect):
                        chest.open(player, self.items, self.floor)
                        events.append({"k": "chest",
                                       "pid": getattr(player, "net_pid", -1)})

        # Prune dead enemies
        self.enemies = [e for e in self.enemies if e.alive]

        return events

    def _drop_loot(self, enemy, player: Player) -> list:
        from src.entities.enemy import Skeleton, Orc, Demon
        out = []
        px, py = enemy.x, enemy.y
        lvl    = self.floor
        gf     = 1.0 + player.gold_find_bonus / 100
        q_bonus = (40 if isinstance(enemy, Demon) else
                   20 if isinstance(enemy, Orc)   else
                   10 if isinstance(enemy, Skeleton) else 0)
        if getattr(enemy, "is_elite", False):
            q_bonus += 30
        if random.random() < enemy.LOOT_CHANCE:
            it = random_item(0, 0, lvl, quality_bonus=q_bonus, floor=lvl)
            it._reposition(px + random.uniform(-14, 14),
                           py + random.uniform(-14, 14))
            out.append(it)
        gold = GoldPile(0, 0, int(random.randint(2, 8) * lvl * gf))
        gold._reposition(px + random.uniform(-10, 10),
                         py + random.uniform(-10, 10))
        out.append(gold)
        return out

    # ── State snapshot ────────────────────────────────────────────────────────

    def snapshot(self, events: list[dict]) -> dict:
        """Build the full state dict to broadcast to all clients."""
        return {
            "type":    "state",
            "tick":    self._tick_n,
            "floor":   self.floor,
            "players": [
                {
                    "pid":     pid,
                    "x":       round(p.x, 1),
                    "y":       round(p.y, 1),
                    "hp":      round(p.hp, 1),
                    "max_hp":  p.max_hp_total,
                    "mana":    round(p.mana, 1),
                    "max_mana": p.max_mana_total,
                    "alive":   p.is_alive(),
                    "angle":   round(p.attack_angle, 3),
                    "name":    getattr(p, "net_name", "???"),
                    "level":   p.level,
                    "gold":    p.gold,
                }
                for pid, p in self.players.items()
            ],
            "enemies": [
                {
                    "eid":    id(e),
                    "x":      round(e.x, 1),
                    "y":      round(e.y, 1),
                    "hp":     round(e.hp, 1),
                    "max_hp": e.max_hp,
                    "kind":   type(e).__name__,
                    "elite":  getattr(e, "is_elite", False),
                    "boss":   getattr(e, "is_boss", False),
                }
                for e in self.enemies
            ],
            "items": [
                {
                    "iid":  id(i),
                    "x":    round(i.x, 1),
                    "y":    round(i.y, 1),
                    "kind": type(i).__name__,
                }
                for i in self.items
            ],
            "events": events,
        }


# ── Connection ────────────────────────────────────────────────────────────────

class _Conn:
    """One connected client."""
    def __init__(self, pid: int,
                 reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.pid    = pid
        self.reader = reader
        self.writer = writer
        self.name   = f"Player{pid}"
        self.unpack = Unpacker()
        self.alive  = True

    async def send(self, msg: dict):
        try:
            self.writer.write(pack(msg))
            await self.writer.drain()
        except Exception:
            self.alive = False


# ── GameServer ────────────────────────────────────────────────────────────────

class GameServer:
    """
    asyncio TCP server.  One GameServer manages one dungeon floor and up to
    *max_players* simultaneous connections.
    """

    def __init__(self, floor: int = 1, seed: int | None = None,
                 max_players: int = MAX_PLAYERS):
        self.game        = ServerGame(floor=floor, seed=seed)
        self.max_players = max_players
        self._conns:     dict[int, _Conn] = {}
        self._next_pid   = 0

    # ── Entry point ───────────────────────────────────────────────────────────

    async def serve(self, host: str, port: int):
        server = await asyncio.start_server(
            self._accept, host, port)
        addr = server.sockets[0].getsockname()
        print(f"[server] Listening on {addr[0]}:{addr[1]}  "
              f"floor={self.game.floor}  seed={self.game.seed}  "
              f"max_players={self.max_players}")
        asyncio.create_task(self._tick_loop())
        async with server:
            await server.serve_forever()

    # ── Connection lifecycle ──────────────────────────────────────────────────

    async def _accept(self, reader: asyncio.StreamReader,
                       writer: asyncio.StreamWriter):
        if len(self._conns) >= self.max_players:
            writer.write(pack({"type": "error", "text": "Server full"}))
            await writer.drain()
            writer.close()
            return

        pid  = self._next_pid
        self._next_pid += 1
        conn = _Conn(pid, reader, writer)
        self._conns[pid] = conn
        peer = writer.get_extra_info("peername")
        print(f"[server] pid={pid} connected  peer={peer}")

        try:
            await self._client_loop(conn)
        except (ConnectionResetError, asyncio.IncompleteReadError, EOFError,
                BrokenPipeError, ConnectionAbortedError):
            pass
        finally:
            self._drop(conn)

    async def _client_loop(self, conn: _Conn):
        # Expect a join message within 5 s
        try:
            raw = await asyncio.wait_for(conn.reader.read(2048), timeout=5.0)
        except asyncio.TimeoutError:
            return
        for msg in conn.unpack.feed(raw):
            if msg.get("type") == "join":
                conn.name = str(msg.get("name", conn.name))[:24]
                break

        player = self.game.add_player(conn.pid, conn.name)
        await conn.send({
            "type":    "welcome",
            "pid":     conn.pid,
            "floor":   self.game.floor,
            "seed":    self.game.seed,
            "start_x": round(player.x, 1),
            "start_y": round(player.y, 1),
        })
        self._broadcast_chat(f"{conn.name} entered the dungeon.")

        while conn.alive:
            try:
                data = await asyncio.wait_for(conn.reader.read(4096), timeout=10.0)
                if not data:
                    break
                for msg in conn.unpack.feed(data):
                    mtype = msg.get("type")
                    if mtype == "input":
                        self.game.set_input(conn.pid, msg)
                    elif mtype == "ping":
                        await conn.send({"type": "pong", "t": msg.get("t", 0)})
            except asyncio.TimeoutError:
                # Send a keepalive; if write fails, drop client
                try:
                    conn.writer.write(pack({"type": "ping_sv"}))
                except Exception:
                    break

    def _drop(self, conn: _Conn):
        conn.alive = False
        self._conns.pop(conn.pid, None)
        self.game.remove_player(conn.pid)
        try:
            conn.writer.close()
        except Exception:
            pass
        print(f"[server] pid={conn.pid} ({conn.name}) disconnected")
        self._broadcast_chat(f"{conn.name} left the dungeon.")

    # ── Tick loop ─────────────────────────────────────────────────────────────

    async def _tick_loop(self):
        loop     = asyncio.get_event_loop()
        next_t   = loop.time()
        while True:
            now = loop.time()
            if now < next_t:
                await asyncio.sleep(next_t - now)
            next_t += TICK_DT

            if not self._conns:
                continue

            events   = self.game.tick(TICK_DT)
            snapshot = pack(self.game.snapshot(events))

            dead = []
            for conn in list(self._conns.values()):
                try:
                    conn.writer.write(snapshot)
                    # Drain periodically, not every tick, for throughput
                    if self.game._tick_n % 4 == 0:
                        await conn.writer.drain()
                except Exception:
                    dead.append(conn)
            for conn in dead:
                self._drop(conn)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _broadcast_chat(self, text: str):
        msg = pack({"type": "chat", "text": text})
        for conn in list(self._conns.values()):
            try:
                conn.writer.write(msg)
            except Exception:
                pass


# ── Public runner ─────────────────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 5555,
               floor: int = 1, seed: int | None = None,
               max_players: int = MAX_PLAYERS):
    server = GameServer(floor=floor, seed=seed, max_players=max_players)
    try:
        asyncio.run(server.serve(host, port))
    except KeyboardInterrupt:
        print("\n[server] Shutting down.")
