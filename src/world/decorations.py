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
from src.world.tile import TILE_FLOOR, TILE_WALL

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


def _wall_backed_spots(dungeon, room) -> list[tuple[int, int]]:
    """
    Floor tiles along a room's edge that have a solid wall directly behind
    them *and* solid wall to both flanking sides — i.e. a flat wall section
    rather than a doorway/corridor mouth. Rooms are carved as solid floor
    rectangles with the wall ring one tile *outside* the room bounds, so
    "backed by a wall" means the neighbouring tile just past the room's edge.
    These are the only spots where a statue or pillar looks like it's
    actually resting against something, instead of floating in open floor.
    """
    x0, y0 = room.x, room.y
    x1, y1 = room.x + room.w - 1, room.y + room.h - 1
    if room.w < 5 or room.h < 5:
        return []

    def is_wall(tx, ty):
        return (0 <= ty < dungeon.height and 0 <= tx < dungeon.width
                and dungeon.grid[ty][tx] == TILE_WALL)

    def is_floor(tx, ty):
        return (0 <= ty < dungeon.height and 0 <= tx < dungeon.width
                and dungeon.grid[ty][tx] == TILE_FLOOR)

    spots: list[tuple[int, int]] = []

    # Top and bottom edges (skip corner tiles — flanking checks cover them)
    for tx in range(x0 + 1, x1):
        for ty, dy in ((y0, -1), (y1, 1)):
            if (is_floor(tx, ty) and is_wall(tx, ty + dy)
                    and is_wall(tx - 1, ty + dy) and is_wall(tx + 1, ty + dy)):
                spots.append((tx, ty))

    # Left and right edges
    for ty in range(y0 + 1, y1):
        for tx, dx in ((x0, -1), (x1, 1)):
            if (is_floor(tx, ty) and is_wall(tx + dx, ty)
                    and is_wall(tx + dx, ty - 1) and is_wall(tx + dx, ty + 1)):
                spots.append((tx, ty))

    return spots


def generate_dungeon_decorations(dungeon, theme: str,
                                 rng: random.Random) -> list[Decoration]:
    """
    Place decorations inside dungeon rooms.

    Rules:
    - Skip start room (rooms[0]) and stair room (rooms[-1]).
    - Each eligible room has a 45 % chance of getting a decoration.
    - Statues are the common case; pillars/boulders ("extras") are rare —
      they read as structural clutter when overused, so they only show up
      occasionally for variety.
    - Decorations are only placed on floor tiles that are backed by a solid
      wall section (not a doorway or corridor mouth), so they always read as
      "standing against the wall" rather than floating in a walkway.
    """
    if not dungeon.rooms or len(dungeon.rooms) < 3:
        return []

    statue_pool = _THEME_STATUES.get(theme, _THEME_STATUES["dungeon"])
    extra_pool  = _THEME_EXTRAS.get(theme, [])
    if not statue_pool and not extra_pool:
        return []

    decos: list[Decoration] = []
    eligible = dungeon.rooms[1:-1]

    for room in eligible:
        if rng.random() > 0.45:
            continue

        spots = _wall_backed_spots(dungeon, room)
        if not spots:
            continue

        # Statues are the logical choice for a lone wall-niche; pillars and
        # boulders are reserved for the rare "structural" accent.
        if extra_pool and rng.random() < 0.12:
            rel = rng.choice(extra_pool)
        elif statue_pool:
            rel = rng.choice(statue_pool)
        else:
            rel = rng.choice(extra_pool)

        tx, ty = rng.choice(spots)
        px = tx * TILE_SIZE + TILE_SIZE // 2
        py = ty * TILE_SIZE + TILE_SIZE // 2
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
