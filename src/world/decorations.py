"""
Dungeon and town decorations using DCSS sprites.

Decorations are static world props (statues, trees, fountains, boulders)
placed at specific pixel positions. They draw at their position relative to
the camera and are culled by the LoS system.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
import pygame
from src.settings import TILE_SIZE

# ── DCSS bundle path ──────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    _DCSS = Path(sys._MEIPASS) / "assets" / "Dungeon Crawl Stone Soup Full"  # type: ignore
else:
    _DCSS = Path(__file__).parent.parent.parent / "assets" / "Dungeon Crawl Stone Soup Full"

_DUNGEON = _DCSS / "dungeon"

# ── Sprite cache ──────────────────────────────────────────────────────────────
_spr_cache: dict[str, pygame.Surface] = {}


def _load(rel: str, size: int) -> pygame.Surface | None:
    key = f"{rel}_{size}"
    if key not in _spr_cache:
        p = _DUNGEON / rel
        if not p.exists():
            _spr_cache[key] = None  # type: ignore
            return None
        try:
            surf = pygame.image.load(str(p)).convert_alpha()
            surf = pygame.transform.smoothscale(surf, (size, size))
            _spr_cache[key] = surf
        except Exception:
            _spr_cache[key] = None  # type: ignore
    return _spr_cache.get(key)


# ── Theme → statue pool mapping ───────────────────────────────────────────────
_THEME_STATUES: dict[str, list[str]] = {
    "dungeon":  ["statues/statue_iron.png",
                 "statues/crumbled_column.png",
                 "statues/crumbled_column_1.png",
                 "statues/crumbled_column_2.png"],
    "crypt":    ["statues/statue_angel.png",
                 "statues/statue_ancient_hero.png",
                 "statues/statue_wraith.png",
                 "statues/statue_sword.png"],
    "forge":    ["statues/statue_dwarf.png",
                 "statues/statue_iron.png"],
    "inferno":  ["statues/statue_dragon.png",
                 "statues/statue_ancient_evil.png",
                 "statues/statue_demonic_bust.png"],
    "abyss":    ["statues/statue_cerebov.png",
                 "statues/statue_orb.png",
                 "statues/statue_orb_guardian.png"],
}

# Sprites that live outside the statues/ sub-folder
_THEME_EXTRAS: dict[str, list[str]] = {
    "dungeon":  ["zot_pillar.png"],
    "crypt":    [],
    "forge":    ["boulder.png"],
    "inferno":  ["boulder.png"],
    "abyss":    ["zot_pillar.png"],
}

_TOWN_STATUE_POOL = [
    "statues/statue_angel.png",
    "statues/statue_ancient_hero.png",
    "statues/statue_archer.png",
    "statues/pedestal.png",
]

_TREE_VARIANTS = [
    "trees/tree_1_yellow.png",
    "trees/tree_2_yellow.png",
    "trees/tree_1_red.png",
    "trees/tree_2_red.png",
    "trees/tree_1_lightred.png",
    "trees/tree_2_lightred.png",
    "trees/mangrove_1.png",
    "trees/mangrove_2.png",
    "trees/mangrove_3.png",
]

_FOUNTAIN_SPRITES = [
    "blue_fountain.png",
    "sparkling_fountain.png",
    "blue_fountain_2.png",
]


class Decoration:
    """A static sprite placed in the world at pixel position (x, y)."""

    def __init__(self, x: float, y: float, sprite_rel: str, size: int = 64,
                 shadow: bool = True):
        self.x    = x
        self.y    = y
        self._rel  = sprite_rel
        self._size = size
        self._shadow = shadow

    def draw(self, surface: pygame.Surface, camera) -> None:
        spr = _load(self._rel, self._size)
        if spr is None:
            return
        sx = int(self.x - camera.x) - self._size // 2
        sy = int(self.y - camera.y) - self._size // 2
        if self._shadow:
            sh = pygame.Surface((self._size, self._size // 4), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 60), sh.get_rect())
            surface.blit(sh, (sx, sy + self._size - self._size // 8))
        surface.blit(spr, (sx, sy))


def generate_dungeon_decorations(dungeon, theme: str,
                                 rng: random.Random) -> list[Decoration]:
    """
    Place decorations inside dungeon rooms.

    Rules:
    - Skip start room (rooms[0]) and stair room (rooms[-1]).
    - Each eligible room has a 45 % chance of getting a decoration.
    - Statues and extras from the theme pool are used.
    - Decorations are placed in room corners / near walls, not at the centre
      (which is kept clear for combat).
    """
    if not dungeon.rooms or len(dungeon.rooms) < 3:
        return []

    pool = _THEME_STATUES.get(theme, _THEME_STATUES["dungeon"]).copy()
    pool += [f"statues/{f}" for f in []]   # no stray extras at statues level
    # Also include top-level extras (boulder, zot_pillar)
    for rel in _THEME_EXTRAS.get(theme, []):
        pool.append(rel)

    if not pool:
        return []

    decos: list[Decoration] = []
    eligible = dungeon.rooms[1:-1]

    for room in eligible:
        if rng.random() > 0.45:
            continue

        rel = rng.choice(pool)
        # Place near a random inner wall corner (1 tile in from edges)
        cx, cy = room.center
        # Offset into a corner quadrant so the centre aisle stays free
        qx = rng.choice([-1, 1]) * rng.randint(TILE_SIZE, max(TILE_SIZE, (room.w - 2) * TILE_SIZE // 2 - TILE_SIZE))
        qy = rng.choice([-1, 1]) * rng.randint(TILE_SIZE, max(TILE_SIZE, (room.h - 2) * TILE_SIZE // 2 - TILE_SIZE))
        px = cx * TILE_SIZE + TILE_SIZE // 2 + qx
        py = cy * TILE_SIZE + TILE_SIZE // 2 + qy
        decos.append(Decoration(float(px), float(py), rel, size=56))

    return decos


def blit_town_decoration(surf: pygame.Surface, rel: str, cx: int, cy: int,
                         size: int = 64, shadow: bool = True) -> None:
    """
    Blit a single DCSS decoration onto a pre-baked town surface.
    cx, cy are the centre position in town pixel coords.
    """
    spr = _load(rel, size)
    if spr is None:
        return
    if shadow:
        sh = pygame.Surface((size, size // 4), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 60), sh.get_rect())
        surf.blit(sh, (cx - size // 2, cy + size // 2 - size // 8))
    surf.blit(spr, (cx - size // 2, cy - size // 2))
