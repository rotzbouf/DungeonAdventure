import pygame
from src.settings import TILE_SIZE, VOID_COLOR

TILE_VOID        = 0
TILE_FLOOR       = 1
TILE_WALL        = 2
TILE_DOOR        = 3
TILE_STAIRS_DOWN = 4
TILE_STAIRS_UP   = 5

WALKABLE = {TILE_FLOOR, TILE_DOOR, TILE_STAIRS_DOWN, TILE_STAIRS_UP}

_cache: dict = {}

# ── Floor-theme palettes ───────────────────────────────────────────────────────
_THEMES: dict[str, dict] = {
    "dungeon": {                            # Floors 1-2 — blue stone
        'mortar':   (0,    8,  52),
        'stone':    (68, 100, 176),
        'stone_hi': (112, 152, 220),
        'stone_sh': (36,  56,  116),
        'floor':    (16,   8,    0),
        'floor_dot':(28,  14,    2),
    },
    "crypt": {                              # Floor 3 — bone-gray crypts
        'mortar':   (22,  18,  22),
        'stone':    (88,  82,  88),
        'stone_hi': (148, 140, 148),
        'stone_sh': (44,  38,  44),
        'floor':    (12,  10,  12),
        'floor_dot':(24,  20,  24),
    },
    "forge": {                              # Floor 4 — iron forge, rust-red
        'mortar':   (28,   8,   0),
        'stone':    (104,  50,  20),
        'stone_hi': (168,  90,  40),
        'stone_sh': (56,  22,   6),
        'floor':    (22,   6,   0),
        'floor_dot':(36,  12,   4),
    },
    "inferno": {                            # Floor 5 — lava cavern
        'mortar':   (52,   8,   0),
        'stone':    (188,  48,  10),
        'stone_hi': (240, 100,  20),
        'stone_sh': (100,  18,   0),
        'floor':    (32,   4,   0),
        'floor_dot':(52,  12,   4),
    },
    "abyss": {                              # NG+ — void cyan deep-dark
        'mortar':   (0,    8,  18),
        'stone':    (18,  72,  96),
        'stone_hi': (36, 132, 160),
        'stone_sh': (6,   36,  52),
        'floor':    (4,    8,  12),
        'floor_dot':(8,   18,  26),
    },
}

_current_theme: dict = _THEMES["dungeon"]

# Stairs/door colours remain fixed across themes
_VOID      = (0,   0,   0)
_DOOR_BG   = (72,  40,   0)
_DOOR_WOOD = (160, 100,  28)
_DOOR_HI   = (212, 148,  52)
_STEP_1    = (164, 132,  52)
_STEP_2    = (128, 100,  32)
_STEP_3    = (96,   72,  16)
_STEP_HI   = (216, 188,  88)


_THEME_CYCLE = ["dungeon", "crypt", "forge", "inferno", "abyss"]


def set_theme(floor: int, ng_plus: int = 0):
    """Select a tile palette based on floor depth (cycles every 5 floors)."""
    global _current_theme
    idx = (floor - 1) // 5 % len(_THEME_CYCLE)
    _current_theme = _THEMES[_THEME_CYCLE[idx]]
    _cache.clear()


# ─── Tile builders ────────────────────────────────────────────────────────────

def _build_wall(surf: pygame.Surface, tx: int, ty: int):
    t = _current_theme
    surf.fill(t['mortar'])
    BLOCK_W = 17
    BLOCK_H = 10
    for row in range(4):
        ry  = row * BLOCK_H
        off = (BLOCK_W // 2) if (ty + row) % 2 == 0 else 0
        for col in range(-1, 4):
            bx = col * BLOCK_W + off
            x1 = max(0, bx + 1)
            x2 = min(TILE_SIZE, bx + BLOCK_W - 1)
            y1 = ry + 1
            y2 = min(TILE_SIZE, ry + BLOCK_H - 1)
            if x2 <= x1 + 1 or y2 <= y1 + 1:
                continue
            pygame.draw.rect(surf, t['stone'],   (x1, y1, x2 - x1, y2 - y1))
            pygame.draw.line(surf, t['stone_hi'], (x1,     y1),     (x2 - 1, y1))
            pygame.draw.line(surf, t['stone_hi'], (x1,     y1),     (x1,     y2 - 1))
            pygame.draw.line(surf, t['stone_sh'], (x1,     y2 - 1), (x2 - 1, y2 - 1))
            pygame.draw.line(surf, t['stone_sh'], (x2 - 1, y1),     (x2 - 1, y2 - 1))


def _build_floor(surf: pygame.Surface, tx: int, ty: int):
    t = _current_theme
    surf.fill(t['floor'])
    for dy in range(5, TILE_SIZE, 10):
        for dx in range(5, TILE_SIZE, 10):
            if (tx + ty + dx // 10 + dy // 10) % 3 != 0:
                surf.set_at((dx, dy), t['floor_dot'])
    # subtle variation — slightly lighter patches
    if (tx * 3 + ty * 7) % 5 == 0:
        shade = tuple(min(255, c + 6) for c in t['floor'])
        pygame.draw.rect(surf, shade, (1, 1, TILE_SIZE - 2, TILE_SIZE - 2))
        surf.set_at((TILE_SIZE//2, TILE_SIZE//2), t['floor_dot'])


def _build_door(surf: pygame.Surface):
    """Wooden door with plank detail."""
    surf.fill(_DOOR_BG)
    dr = pygame.Rect(TILE_SIZE // 4, 0, TILE_SIZE // 2, TILE_SIZE)
    pygame.draw.rect(surf, _DOOR_WOOD, dr)
    pygame.draw.line(surf, _DOOR_HI, (dr.left, 0), (dr.left, TILE_SIZE - 1))
    for y in range(6, TILE_SIZE, 9):
        pygame.draw.line(surf, _DOOR_BG, (dr.left + 2, y), (dr.right - 3, y))
    pygame.draw.rect(surf, (220, 188, 40),
                     (dr.right - 9, TILE_SIZE // 2 - 2, 4, 4))


def _build_stairs(surf: pygame.Surface, going_down: bool):
    surf.fill(_VOID)
    step_colors = [_STEP_1, _STEP_2, _STEP_3]
    for i, sc in enumerate(step_colors):
        indent = i * 5
        y = (5 + i * 9) if going_down else (TILE_SIZE - 14 - i * 9)
        r = pygame.Rect(2 + indent, y, TILE_SIZE - 4 - indent * 2, 7)
        pygame.draw.rect(surf, sc, r)
        pygame.draw.line(surf, _STEP_HI, (r.left, r.top), (r.right - 1, r.top))
    cx = TILE_SIZE // 2
    if going_down:
        pts = [(cx, TILE_SIZE - 4), (cx - 6, TILE_SIZE - 12), (cx + 6, TILE_SIZE - 12)]
    else:
        pts = [(cx, 4), (cx - 6, 12), (cx + 6, 12)]
    pygame.draw.polygon(surf, _STEP_HI, pts)


# ─── Public API ───────────────────────────────────────────────────────────────

def get_tile_surface(tile_type: int, tx: int, ty: int) -> pygame.Surface:
    key = (tile_type, (tx * 11 + ty * 7) % 16)
    if key in _cache:
        return _cache[key]

    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))

    if tile_type == TILE_FLOOR:
        _build_floor(surf, tx, ty)
    elif tile_type == TILE_WALL:
        _build_wall(surf, tx, ty)
    elif tile_type == TILE_DOOR:
        _build_door(surf)
    elif tile_type == TILE_STAIRS_DOWN:
        _build_stairs(surf, going_down=True)
    elif tile_type == TILE_STAIRS_UP:
        _build_stairs(surf, going_down=False)
    else:
        surf.fill(VOID_COLOR)

    _cache[key] = surf
    return surf
