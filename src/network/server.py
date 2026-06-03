"""
Headless authoritative game server.

Usage (via server.py entry point):
    python server.py [--host 0.0.0.0] [--port 5555] [--floor 1] [--max-players 4]
"""
from __future__ import annotations

import asyncio
import math
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()

from src.entities.player import Player
from src.entities.enemy import get_enemy_types
from src.items.item import (
    random_item, GoldPile, TreasureChest, _ilvl_and_mult,
    random_equip, QUALITY_RARE, QUALITY_UNIQUE,
)
from src.world.dungeon import Dungeon
from src.world.tile import set_theme
from src.boss_pool import pick_boss
from src.settings import (
    TILE_SIZE,
    ARROW_SPEED, ARROW_MAX_RANGE,
    FIREBALL_MANA_COST, FIREBALL_SPEED, FIREBALL_MAX_RANGE,
    FIREBALL_DAMAGE, FIREBALL_RADIUS, STATUS_BURN,
    ICE_NOVA_MANA_COST, ICE_NOVA_DAMAGE, ICE_NOVA_RADIUS,
    ICE_NOVA_SLOW_DUR, ICE_NOVA_COOLDOWN, STATUS_FREEZE,
    CHAIN_LIGHTNING_MANA_COST, CHAIN_LIGHTNING_DAMAGE,
    CHAIN_LIGHTNING_JUMPS, CHAIN_LIGHTNING_RANGE, CHAIN_LIGHTNING_COOLDOWN,
    BLINK_MANA_COST, BLINK_COOLDOWN,
    BATTLE_CRY_MANA_COST, BATTLE_CRY_DURATION,
)
from src.network.protocol import pack, Unpacker

TICK_RATE   = 20
TICK_DT     = 1.0 / TICK_RATE
MAX_PLAYERS = 4


# ── Key-state adapter ─────────────────────────────────────────────────────────

class _NetKeys:
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
    x = 0.0; y = 0.0
    def update(self, *a, **kw): pass
    def apply(self, r): return r


_NULL_CAM = _NullCamera()


# ── ServerGame ────────────────────────────────────────────────────────────────

class ServerGame:
    """Full authoritative dungeon simulation — no rendering."""

    def __init__(self, floor: int = 1, seed: int | None = None):
        self.floor   = floor
        self.seed    = seed if seed is not None else random.randint(1, 2 ** 30)
        self._tick_n = 0
        self._floor_changing = False   # debounce stair trigger

        self.players:          dict[int, Player] = {}
        self._inputs:          dict[int, dict]   = {}
        self._spell_state:     dict[int, dict]   = {}
        self._defeated_bosses: set[str]           = set()
        self.enemies:     list = []
        self.items:       list = []
        self.chests:      list = []
        self.projectiles: list = []

        self._init_level(floor, self.seed)
        print(f"[game] Floor {floor}  seed={self.seed}  "
              f"{len(self.enemies)} enemies  {len(self.items)} items")

    # ── Level setup ───────────────────────────────────────────────────────────

    def _init_level(self, floor: int, seed: int):
        set_theme(floor)
        self.dungeon = Dungeon(level=floor, seed=seed)
        self.enemies     = []
        self.items       = []
        self.chests      = []
        self.projectiles = []
        self._floor_changing = False

        etypes = get_enemy_types(floor)
        for tx, ty in self.dungeon.enemy_spawns:
            e = random.choice(etypes)(
                tx * TILE_SIZE + TILE_SIZE // 2,
                ty * TILE_SIZE + TILE_SIZE // 2,
            )
            e.scale_to_level(floor)
            if random.random() < 0.15:
                e.make_elite()
            self.enemies.append(e)

        # Power-gated boss: use strongest player's CR as the gate
        if self.dungeon.rooms and self.players:
            strongest = max(self.players.values(), key=lambda p: p.level)
            BossClass = pick_boss(
                strongest, floor,
                self._defeated_bosses,
                self.dungeon.rng,
            )
            if BossClass:
                room = self.dungeon.rooms[-1]
                bx   = room.center[0] * TILE_SIZE + TILE_SIZE // 2
                by   = room.center[1] * TILE_SIZE + TILE_SIZE // 2
                boss = BossClass(float(bx), float(by))
                boss.scale_to_level(floor)
                self.enemies.append(boss)

        self.items  = [random_item(tx, ty, floor, floor=floor)
                       for tx, ty in self.dungeon.item_spawns]
        self.chests = [TreasureChest(tx, ty)
                       for tx, ty in self.dungeon.chest_positions]

    def change_floor(self, new_floor: int,
                     new_seed: int | None = None) -> int:
        """Advance to a new floor, keeping all player objects."""
        self.floor = new_floor
        self.seed  = new_seed if new_seed is not None else random.randint(1, 2 ** 30)
        self._tick_n = 0
        self._init_level(new_floor, self.seed)

        # Reposition all players and restore HP/mana (rest between floors)
        sx, sy = self.dungeon.player_start
        for p in self.players.values():
            p.x    = float(sx)
            p.y    = float(sy)
            p.hp   = float(p.max_hp_total)
            p.mana = float(p.max_mana_total)
            p._sync_rect()

        print(f"[game] → Floor {new_floor}  seed={self.seed}  "
              f"{len(self.enemies)} enemies  {len(self.items)} items")
        return self.seed

    # ── Player management ─────────────────────────────────────────────────────

    def add_player(self, pid: int, name: str,
                   player_data: dict | None = None) -> Player:
        sx, sy = self.dungeon.player_start
        p = Player(float(sx), float(sy))

        if player_data:
            try:
                from src import save as savesys
                savesys.restore_player(p, player_data)
            except Exception as exc:
                print(f"[server] Warning: could not restore player data for pid={pid}: {exc}")
            # Reset position to dungeon start regardless
            p.x    = float(sx)
            p.y    = float(sy)
            p.hp   = float(p.max_hp_total)
            p.mana = float(p.max_mana_total)
            p._sync_rect()

        p.net_name = name   # type: ignore[attr-defined]
        p.net_pid  = pid    # type: ignore[attr-defined]
        self.players[pid]      = p
        self._inputs[pid]      = {}
        self._spell_state[pid] = {
            "ice_nova": 0.0,
            "chain":    0.0,
            "blink":    0.0,
            "battle_cry": 0.0,   # active duration remaining
        }
        return p

    def remove_player(self, pid: int):
        self.players.pop(pid, None)
        self._inputs.pop(pid, None)
        self._spell_state.pop(pid, None)

    def set_input(self, pid: int, inp: dict):
        self._inputs[pid] = inp

    # ── Simulation tick ───────────────────────────────────────────────────────

    def tick(self, dt: float) -> list[dict]:
        self._tick_n += 1
        events: list[dict] = []

        # Tick spell cooldowns
        for ss in self._spell_state.values():
            ss["ice_nova"]    = max(0.0, ss["ice_nova"]    - dt)
            ss["chain"]       = max(0.0, ss["chain"]       - dt)
            ss["blink"]       = max(0.0, ss["blink"]       - dt)
            ss["battle_cry"]  = max(0.0, ss["battle_cry"]  - dt)

        alive_players = [p for p in self.players.values()
                         if p.is_alive() and not self._inputs.get(p.net_pid, {}).get("in_town")]

        # ── Move players ──────────────────────────────────────────────────────
        for pid, player in self.players.items():
            if not player.is_alive():
                continue
            inp = self._inputs.get(pid, {})
            if inp.get("in_town"):
                continue
            net_keys = _NetKeys(inp)
            player.update(dt, self.dungeon, _NULL_CAM, net_keys=net_keys)

        # ── Enemy AI ──────────────────────────────────────────────────────────
        if alive_players:
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                nearest = min(alive_players,
                              key=lambda p: math.hypot(enemy.x - p.x,
                                                        enemy.y - p.y))
                enemy.update(dt, nearest, self.dungeon)

        # ── Player actions ────────────────────────────────────────────────────
        for pid, player in self.players.items():
            if not player.is_alive():
                continue
            inp = self._inputs.get(pid, {})
            if inp.get("in_town"):
                continue
            ss  = self._spell_state[pid]
            aim = float(inp.get("aim_angle", player.attack_angle))

            # Melee / bow attack
            if inp.get("attack"):
                net_keys = _NetKeys(inp)
                if player.has_bow:
                    self._shoot_arrow(player, pid, aim, events)
                else:
                    hits = player.try_attack(self.enemies, net_keys=net_keys)
                    mult = 1.0 + (player.skill_tree.battle_cry_bonus()
                                  if ss["battle_cry"] > 0 else 0.0)
                    for enemy in hits:
                        raw     = int((player.attack + random.randint(-2, 4)) * mult)
                        is_crit = random.uniform(0, 100) < player.crit_chance
                        if is_crit:
                            raw = int(raw * 2)
                        dmg = enemy.take_damage(raw)
                        events.append({"k": "hit", "eid": id(enemy),
                                       "dmg": dmg, "crit": is_crit})
                        if player.life_steal > 0:
                            player.heal(max(1, int(dmg * player.life_steal / 100)))
                        if not enemy.alive:
                            self._kill_enemy(enemy, player, pid, events)

            # Spells
            if inp.get("spell_fireball"):
                self._cast_fireball(player, pid, events)
            if inp.get("spell_ice_nova"):
                self._cast_ice_nova(player, pid, events)
            if inp.get("spell_chain"):
                self._cast_chain(player, pid, events)
            if inp.get("spell_blink"):
                self._cast_blink(player, pid, aim, events)
            if inp.get("spell_battle_cry"):
                self._cast_battle_cry(player, pid, events)

            # Potion
            if inp.get("use_potion"):
                player.use_potion()

            # Stair descend — only one player needs to trigger it
            if inp.get("descend") and not self._floor_changing:
                stx, sty = self.dungeon.stairs_pos
                if math.hypot(player.x - stx, player.y - sty) < TILE_SIZE * 1.6:
                    self._floor_changing = True
                    events.append({"k": "floor_change", "new_floor": self.floor + 1})

        # ── Projectiles ───────────────────────────────────────────────────────
        self._tick_projectiles(dt, events)

        # ── Item pickup ───────────────────────────────────────────────────────
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
                        events.append({"k": "gold",
                                       "pid": getattr(player, "net_pid", -1),
                                       "amount": item.amount})
                    else:
                        item.collect(player)
                        events.append({"k": "item",
                                       "pid": getattr(player, "net_pid", -1)})
                    break
        self.items = [i for i in self.items if not i.collected]

        # ── Chests ────────────────────────────────────────────────────────────
        for chest in self.chests:
            chest.update(dt)
            if not chest.opened:
                for player in alive_players:
                    if player.rect.colliderect(chest.rect):
                        chest.open(player, self.items, self.floor)
                        events.append({"k": "chest",
                                       "pid": getattr(player, "net_pid", -1)})

        # ── Prune dead enemies ────────────────────────────────────────────────
        self.enemies = [e for e in self.enemies if e.alive]

        return events

    # ── Spell implementations ─────────────────────────────────────────────────

    def _cast_fireball(self, player: Player, pid: int, events: list):
        discount = player.skill_tree.fireball_mana_discount()
        cost     = max(5, FIREBALL_MANA_COST - discount)
        if player.mana < cost:
            return
        alive = [e for e in self.enemies if e.alive]
        target = min(alive, key=lambda e: math.hypot(e.x - player.x, e.y - player.y),
                     default=None)
        if not target and not alive:
            return
        player.mana -= cost
        if target:
            dx, dy = target.x - player.x, target.y - player.y
        else:
            dx, dy = math.cos(player.attack_angle), math.sin(player.attack_angle)
        dist = math.hypot(dx, dy) or 1.0
        nx, ny = dx / dist, dy / dist
        self.projectiles.append({
            "x": player.x, "y": player.y,
            "vx": nx * FIREBALL_SPEED, "vy": ny * FIREBALL_SPEED,
            "traveled": 0.0, "alive": True,
            "exploding": False, "exp_timer": 0.0,
            "type": "fireball",
            "owner_pid": pid,
            "dmg_mult": player.skill_tree.fireball_damage_mult(),
        })
        events.append({"k": "spell", "spell": "fireball", "pid": pid})

    def _cast_ice_nova(self, player: Player, pid: int, events: list):
        ss = self._spell_state[pid]
        if not player.skill_tree.has_ice_nova():
            return
        if player.mana < ICE_NOVA_MANA_COST or ss["ice_nova"] > 0:
            return
        player.mana    -= ICE_NOVA_MANA_COST
        ss["ice_nova"]  = ICE_NOVA_COOLDOWN
        for enemy in list(self.enemies):
            if not enemy.alive:
                continue
            if math.hypot(enemy.x - player.x, enemy.y - player.y) <= ICE_NOVA_RADIUS:
                raw = ICE_NOVA_DAMAGE + random.randint(-3, 5)
                dmg = enemy.take_damage(raw)
                enemy.apply_status(STATUS_FREEZE, ICE_NOVA_SLOW_DUR)
                events.append({"k": "hit", "eid": id(enemy), "dmg": dmg,
                                "crit": False, "col": "ice"})
                if not enemy.alive:
                    self._kill_enemy(enemy, player, pid, events)
        events.append({"k": "spell", "spell": "ice_nova", "pid": pid,
                        "x": player.x, "y": player.y})

    def _cast_chain(self, player: Player, pid: int, events: list):
        ss = self._spell_state[pid]
        if not player.skill_tree.has_chain_lightning():
            return
        if player.mana < CHAIN_LIGHTNING_MANA_COST or ss["chain"] > 0:
            return
        player.mana  -= CHAIN_LIGHTNING_MANA_COST
        ss["chain"]   = CHAIN_LIGHTNING_COOLDOWN
        alive         = [e for e in self.enemies if e.alive]
        if not alive:
            return
        cur_x, cur_y = player.x, player.y
        dmg_base     = float(CHAIN_LIGHTNING_DAMAGE)
        hit_set:     set = set()
        arcs:        list[dict] = []
        for _ in range(CHAIN_LIGHTNING_JUMPS):
            cands = sorted(
                [e for e in alive if id(e) not in hit_set],
                key=lambda e: math.hypot(e.x - cur_x, e.y - cur_y))
            if not cands:
                break
            target = cands[0]
            if math.hypot(target.x - cur_x, target.y - cur_y) > CHAIN_LIGHTNING_RANGE:
                break
            hit_set.add(id(target))
            raw = int(dmg_base) + random.randint(-4, 4)
            dmg = target.take_damage(raw)
            arcs.append({"x1": cur_x, "y1": cur_y, "x2": target.x, "y2": target.y})
            events.append({"k": "hit", "eid": id(target), "dmg": dmg,
                           "crit": False, "col": "lightning"})
            if not target.alive:
                self._kill_enemy(target, player, pid, events)
            cur_x, cur_y = target.x, target.y
            dmg_base    *= 0.70
        events.append({"k": "spell", "spell": "chain", "pid": pid, "arcs": arcs})

    def _cast_blink(self, player: Player, pid: int,
                    aim_angle: float, events: list):
        ss = self._spell_state[pid]
        if not player.skill_tree.has_blink():
            return
        discount = player.skill_tree.blink_mana_discount()
        cost     = max(5, BLINK_MANA_COST - discount)
        if player.mana < cost or ss["blink"] > 0:
            return
        player.mana -= cost
        ss["blink"]  = BLINK_COOLDOWN
        # Blink up to 8 tiles in the aim direction
        BLINK_TILES  = 8
        dx = math.cos(aim_angle)
        dy = math.sin(aim_angle)
        ox, oy = player.x, player.y
        for tiles in range(BLINK_TILES, 0, -1):
            tx = int((player.x + dx * tiles * TILE_SIZE) // TILE_SIZE)
            ty = int((player.y + dy * tiles * TILE_SIZE) // TILE_SIZE)
            if self.dungeon.is_walkable(tx, ty):
                player.x = float(tx * TILE_SIZE + TILE_SIZE // 2)
                player.y = float(ty * TILE_SIZE + TILE_SIZE // 2)
                player._sync_rect()
                break
        events.append({"k": "spell", "spell": "blink", "pid": pid,
                        "ox": ox, "oy": oy, "x": player.x, "y": player.y})

    def _cast_battle_cry(self, player: Player, pid: int, events: list):
        if not player.skill_tree.level("battle_cry") > 0:
            return
        if player.mana < BATTLE_CRY_MANA_COST:
            return
        ss = self._spell_state[pid]
        player.mana          -= BATTLE_CRY_MANA_COST
        ss["battle_cry"]      = BATTLE_CRY_DURATION
        events.append({"k": "spell", "spell": "battle_cry", "pid": pid})

    def _shoot_arrow(self, player: Player, pid: int,
                     aim_angle: float, events: list):
        if player._attack_timer > 0:
            return
        player._attack_timer = player.effective_cooldown
        player._attack_anim  = 0.2
        nx = math.cos(aim_angle)
        ny = math.sin(aim_angle)
        self.projectiles.append({
            "x": player.x, "y": player.y,
            "vx": nx * ARROW_SPEED, "vy": ny * ARROW_SPEED,
            "traveled": 0.0, "alive": True,
            "type": "arrow",
            "damage": player.bow_attack,
            "angle": aim_angle,
            "owner_pid": pid,
        })
        events.append({"k": "shoot", "pid": pid})

    # ── Projectile tick ───────────────────────────────────────────────────────

    def _tick_projectiles(self, dt: float, events: list):
        keep = []
        for proj in self.projectiles:
            if not proj.get("alive", True):
                continue

            ptype = proj.get("type", "fireball")

            # ── Arrow ─────────────────────────────────────────────────────────
            if ptype == "arrow":
                proj["x"] += proj["vx"] * dt
                proj["y"] += proj["vy"] * dt
                proj["traveled"] += ARROW_SPEED * dt
                tx = int(proj["x"] // TILE_SIZE)
                ty = int(proj["y"] // TILE_SIZE)
                if (not self.dungeon.is_walkable(tx, ty)
                        or proj["traveled"] >= ARROW_MAX_RANGE):
                    proj["alive"] = False
                    continue
                hit = False
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    if (math.hypot(enemy.x - proj["x"], enemy.y - proj["y"])
                            < enemy.size // 2 + 6):
                        raw     = proj["damage"] + random.randint(-3, 5)
                        is_crit = random.uniform(0, 100) < 5.0
                        if is_crit:
                            raw = int(raw * 2)
                        dmg = enemy.take_damage(raw)
                        events.append({"k": "hit", "eid": id(enemy),
                                       "dmg": dmg, "crit": is_crit})
                        proj["alive"] = False
                        if not enemy.alive:
                            owner = self.players.get(proj.get("owner_pid"))
                            if owner:
                                self._kill_enemy(enemy, owner,
                                                 proj.get("owner_pid"), events)
                        hit = True
                        break
                if proj["alive"]:
                    keep.append(proj)
                continue

            # ── Fireball exploding visual (timer only) ────────────────────────
            if proj.get("exploding"):
                proj["exp_timer"] -= dt
                if proj["exp_timer"] <= 0:
                    proj["alive"] = False
                else:
                    keep.append(proj)
                continue

            # ── Fireball in flight ────────────────────────────────────────────
            proj["x"] += proj["vx"] * dt
            proj["y"] += proj["vy"] * dt
            proj["traveled"] += FIREBALL_SPEED * dt
            tx = int(proj["x"] // TILE_SIZE)
            ty = int(proj["y"] // TILE_SIZE)

            explode = (not self.dungeon.is_walkable(tx, ty)
                       or proj["traveled"] >= FIREBALL_MAX_RANGE)
            if not explode:
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    if (math.hypot(enemy.x - proj["x"], enemy.y - proj["y"])
                            < enemy.size // 2 + 8):
                        explode = True
                        break

            if explode:
                self._fireball_explode(proj, events)
                proj["exploding"] = True
                proj["exp_timer"] = 0.30
                keep.append(proj)
                continue

            keep.append(proj)

        self.projectiles = [p for p in keep if p.get("alive", True)]

    def _fireball_explode(self, proj: dict, events: list):
        ex, ey    = proj["x"], proj["y"]
        dmg_mult  = proj.get("dmg_mult", 1.0)
        owner_pid = proj.get("owner_pid")
        owner     = self.players.get(owner_pid)
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if math.hypot(enemy.x - ex, enemy.y - ey) > FIREBALL_RADIUS:
                continue
            raw = int((FIREBALL_DAMAGE + random.randint(-4, 8)) * dmg_mult)
            dmg = enemy.take_damage(raw)
            enemy.apply_status(STATUS_BURN, 3.0, 5.0)
            events.append({"k": "hit", "eid": id(enemy), "dmg": dmg,
                           "crit": False, "col": "fire"})
            if not enemy.alive and owner:
                self._kill_enemy(enemy, owner, owner_pid, events)
        events.append({"k": "spell", "spell": "fireball_exp",
                        "x": ex, "y": ey, "pid": owner_pid})

    # ── Kill helper ───────────────────────────────────────────────────────────

    def _kill_enemy(self, enemy, player: Player, pid, events: list):
        leveled = player.gain_xp(enemy.XP_REWARD)
        if getattr(enemy, "is_boss", False):
            # Boss-specific loot: extra uniques
            from src.items.item import _ilvl_and_mult, random_equip, QUALITY_UNIQUE, QUALITY_RARE
            ilvl, dm = _ilvl_and_mult(self.floor)
            for _ in range(3):
                it = random_equip(0, 0, ilvl, quality=QUALITY_UNIQUE if _ == 0 else QUALITY_RARE,
                                  depth_mult=dm)
                if it:
                    it._reposition(enemy.x + random.uniform(-24, 24),
                                   enemy.y + random.uniform(-24, 24))
                    self.items.append(it)
            self._defeated_bosses.add(type(enemy).__name__)
        else:
            new_items = self._drop_loot(enemy, player)
            self.items.extend(new_items)
        events.append({"k": "kill", "eid": id(enemy),
                        "xp": enemy.XP_REWARD, "leveled": leveled,
                        "pid": pid, "x": enemy.x, "y": enemy.y,
                        "boss": getattr(enemy, "is_boss", False)})

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
        return {
            "type":    "state",
            "tick":    self._tick_n,
            "floor":   self.floor,
            "players": [
                {
                    "pid":      pid,
                    "x":        round(p.x, 1),
                    "y":        round(p.y, 1),
                    "hp":       round(p.hp, 1),
                    "max_hp":   p.max_hp_total,
                    "mana":     round(p.mana, 1),
                    "max_mana": p.max_mana_total,
                    "alive":    p.is_alive(),
                    "angle":    round(p.attack_angle, 3),
                    "name":     getattr(p, "net_name", "???"),
                    "level":    p.level,
                    "gold":     p.gold,
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
    def __init__(self, pid: int,
                 reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter):
        self.pid    = pid
        self.reader = reader
        self.writer = writer
        self.name   = f"Player{pid}"
        self.unpack = Unpacker()
        self.alive  = True


# ── GameServer ────────────────────────────────────────────────────────────────

class GameServer:
    def __init__(self, floor: int = 1, seed: int | None = None,
                 max_players: int = MAX_PLAYERS):
        self.game        = ServerGame(floor=floor, seed=seed)
        self.max_players = max_players
        self._conns:     dict[int, _Conn] = {}
        self._next_pid   = 0

    async def serve(self, host: str, port: int):
        server = await asyncio.start_server(self._accept, host, port)
        addr   = server.sockets[0].getsockname()
        print(f"[server] Listening on {addr[0]}:{addr[1]}  "
              f"floor={self.game.floor}  seed={self.game.seed}  "
              f"max_players={self.max_players}")
        asyncio.create_task(self._tick_loop())
        async with server:
            await server.serve_forever()

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
        except (ConnectionResetError, asyncio.IncompleteReadError,
                EOFError, BrokenPipeError, ConnectionAbortedError):
            pass
        finally:
            self._drop(conn)

    async def _client_loop(self, conn: _Conn):
        # Wait for join message
        try:
            raw = await asyncio.wait_for(conn.reader.read(65536), timeout=8.0)
        except asyncio.TimeoutError:
            return
        player_data = None
        for msg in conn.unpack.feed(raw):
            if msg.get("type") == "join":
                conn.name   = str(msg.get("name", conn.name))[:24]
                player_data = msg.get("player_data")
                break

        player = self.game.add_player(conn.pid, conn.name, player_data)
        await self._send(conn, {
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
                        await self._send(conn, {"type": "pong", "t": msg.get("t", 0)})
            except asyncio.TimeoutError:
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

    async def _tick_loop(self):
        loop   = asyncio.get_event_loop()
        next_t = loop.time()
        while True:
            now = loop.time()
            if now < next_t:
                await asyncio.sleep(next_t - now)
            next_t += TICK_DT

            if not self._conns:
                continue

            events = self.game.tick(TICK_DT)

            # Handle floor transition: broadcast floor_change BEFORE state
            for evt in events[:]:
                if evt.get("k") == "floor_change":
                    events.remove(evt)
                    new_floor = evt["new_floor"]
                    new_seed  = self.game.change_floor(new_floor)
                    fc_msg    = pack({"type":  "floor_change",
                                      "floor": new_floor,
                                      "seed":  new_seed})
                    self._write_all(fc_msg)
                    print(f"[server] Floor change → {new_floor}")
                    break  # one transition per tick

            snapshot = pack(self.game.snapshot(events))
            dead = []
            for conn in list(self._conns.values()):
                try:
                    conn.writer.write(snapshot)
                    if self.game._tick_n % 4 == 0:
                        await conn.writer.drain()
                except Exception:
                    dead.append(conn)
            for conn in dead:
                self._drop(conn)

    def _write_all(self, data: bytes):
        for conn in list(self._conns.values()):
            try:
                conn.writer.write(data)
            except Exception:
                pass

    async def _send(self, conn: _Conn, msg: dict):
        try:
            conn.writer.write(pack(msg))
            await conn.writer.drain()
        except Exception:
            self._drop(conn)

    def _broadcast_chat(self, text: str):
        self._write_all(pack({"type": "chat", "text": text}))


# ── Public runner ─────────────────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 5555,
               floor: int = 1, seed: int | None = None,
               max_players: int = MAX_PLAYERS):
    server = GameServer(floor=floor, seed=seed, max_players=max_players)
    try:
        asyncio.run(server.serve(host, port))
    except KeyboardInterrupt:
        print("\n[server] Shutting down.")
