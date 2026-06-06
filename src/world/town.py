"""
Town — the player's central hub between dungeon runs.

The town is larger than one screen (2400 × 1600) and the camera scrolls to
follow the player.  Six merchants are arranged around a central plaza with a
fountain; the player's house sits in the lower-right quarter.
Entering town fully restores the player's HP and mana.
"""
from __future__ import annotations

import math
import random
import pygame
from src.settings import SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE
from src.locale import t

TOWN_W = 2400
TOWN_H = 1600

# Building dimensions shared between _draw_building and the torch-bake loop
BUILDING_W = 165
BUILDING_H = 115

# ── Key positions (pixel coords) ──────────────────────────────────────────────

PLAYER_SPAWN = (TOWN_W // 2, 220)   # just inside gate, player walks down

# Top-centre archway leading to the dungeon
DUNGEON_ENTRANCE_POS = (TOWN_W // 2, 88)
DUNGEON_INTERACT_R   = TILE_SIZE * 2.8

# Central plaza (fountain centrepiece, open square)
PLAZA_CX = TOWN_W // 2   # 1200
PLAZA_CY = 820

# Player-owned house — lower-right quarter
HOUSE_POS        = (1900, 1300)
HOUSE_INTERACT_R = TILE_SIZE * 2.8

# (display_title, specialty_key, px, py)
MERCHANT_SPECS: list[tuple[str, str, int, int]] = [
    ("Blacksmith",    "weapons",  750,   340),   # upper-left,  between gate and plaza
    ("Armourer",      "armor",    1650,  340),   # upper-right, between gate and plaza
    ("Craftsman",     "craft",    370,   820),   # left of plaza
    ("Enchanter",     "enchant",  2030,  820),   # right of plaza
    ("Jeweler",       "jewelry",  650,   1300),  # lower-left
    ("Alchemist",     "potions",  1300,  1300),  # lower-centre
    ("Guild Master",  "guild",    1700,  1060),  # mid-right, clear of house (1900,1300)
]

GUILD_MASTER_SPEC = MERCHANT_SPECS[-1]   # convenience alias

TOWN_INTERACT_R = TILE_SIZE * 3.0


# ── Stall colour palette per specialty ────────────────────────────────────────

_STALL: dict[str, dict] = {
    "weapons":  {"bg": (72,  24,  8),  "hi": (180,  70, 20), "awning": (160, 50, 10)},
    "armor":    {"bg": (16,  36, 68),  "hi": ( 80, 130, 210), "awning": (30, 70, 130)},
    "jewelry":  {"bg": (12,  64, 64),  "hi": ( 40, 200, 200), "awning": (20, 130, 130)},
    "potions":  {"bg": (20,  56, 20),  "hi": ( 60, 200,  60), "awning": (30, 120, 30)},
    "enchant":  {"bg": (36,   8, 72),  "hi": (160,  80, 255), "awning": (80, 20, 150)},
    "craft":    {"bg": (48,  28,   8), "hi": (200, 130,  40), "awning": (140, 80, 20)},
    "guild":    {"bg": (28,  28,  56), "hi": (180, 160, 255), "awning": (60, 60, 140)},
}


# ── TownBounds — constrains player movement to the playable area ───────────────

class TownBounds:
    """
    Drop-in substitute for Dungeon when updating the player in town.
    Reports non-walkable for the two-tile border strip so the player
    cannot walk into the walls.
    """
    _MARGIN = 1   # tiles from each edge that are off-limits

    def is_walkable(self, tx: int, ty: int) -> bool:
        max_x = TOWN_W  // TILE_SIZE - 1
        max_y = TOWN_H  // TILE_SIZE - 1
        m = self._MARGIN
        return m <= tx <= max_x - m and m <= ty <= max_y - m


TOWN_BOUNDS = TownBounds()


# ── Colour palette ─────────────────────────────────────────────────────────────

# Stone
_ST_DARK  = (52, 46, 38)
_ST_MID   = (76, 68, 58)
_ST_LGT   = (104, 94, 82)
_ST_HI    = (136, 124, 108)
_MORTAR   = (32, 28, 22)
# Ground/earth
_GR_DARK  = (32, 24, 16)
_GR_MID   = (46, 36, 24)
_GR_LGT   = (62, 50, 36)
# Path (lighter stone slabs)
_PA_DARK  = (68, 60, 50)
_PA_MID   = (88, 80, 68)
_PA_LGT   = (112, 102, 88)
_PA_MORT  = (48, 42, 34)
# Wood/timber
_WD_DARK  = (46, 30, 12)
_WD_MID   = (72, 50, 20)
_WD_LGT   = (106, 76, 34)
# Plaster (between timbers)
_PL_BASE  = (168, 152, 120)
_PL_SHD   = (140, 126, 98)
# Roof tiles
_RF_DARK  = (64, 32, 16)
_RF_MID   = (92, 48, 22)
_RF_LGT   = (120, 64, 30)
# Foliage
_LF_DARK  = (24, 48, 12)
_LF_MID   = (36, 68, 18)
_LF_LGT   = (52, 90, 26)
# Water
_WA_DARK  = (12, 24, 48)
_WA_MID   = (16, 36, 68)
# Iron/metal
_IR_DARK  = (28, 28, 30)
_IR_MID   = (52, 52, 56)
_IR_LGT   = (82, 82, 88)


# ── Drawing helpers ────────────────────────────────────────────────────────────

def _grad_rect(surf, r, top_col, bot_col):
    """Fill a rect with a vertical linear gradient."""
    for i in range(r.height):
        t_ = i / max(1, r.height - 1)
        c = tuple(int(a + (b - a) * t_) for a, b in zip(top_col, bot_col))
        pygame.draw.line(surf, c, (r.left, r.top + i), (r.right, r.top + i))


def _blit_shadowed(surf, text_surf, pos, shadow_off=(2, 2)):
    """Blit a text surface with a darkened drop shadow."""
    sh = text_surf.copy()
    sh.fill((0, 0, 0, 160), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(sh, (pos[0] + shadow_off[0], pos[1] + shadow_off[1]))
    surf.blit(text_surf, pos)


def _draw_interaction_badge(surface, font, key_txt: str, action_txt: str,
                             cx: int, cy: int, accent: tuple):
    """
    Draw a high-contrast interaction hint badge centred at (cx, cy).
    key_txt   — the key label e.g. "[F]" shown in bright yellow
    action_txt — the action description in light colour
    accent     — border colour (themed per location)
    """
    key_s    = font.render(key_txt,    True, (255, 235, 80))
    # Strip any "[X]" prefix the locale string might already contain
    clean_action = action_txt
    for prefix in ("[F]", "[E]", "[H]"):
        clean_action = clean_action.replace(prefix, "").strip(" —").strip()
    act_s    = font.render(clean_action or action_txt, True, (220, 210, 185))
    pad, gap = 8, 6
    bw = pad + key_s.get_width() + gap + act_s.get_width() + pad
    bh = max(key_s.get_height(), act_s.get_height()) + pad
    bx = cx - bw // 2
    by = cy - bh // 2
    bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 215))
    pygame.draw.rect(bg, accent, (0, 0, bw, bh), 2)
    surface.blit(bg, (bx, by))
    ty = by + (bh - key_s.get_height()) // 2
    surface.blit(key_s, (bx + pad, ty))
    surface.blit(act_s, (bx + pad + key_s.get_width() + gap, ty))


def _draw_stone_blocks(surf, rect, block_w, block_h, seed=0):
    """Tile a rect with offset stone blocks in multiple shades."""
    rng = random.Random(seed)
    shades = [_ST_DARK, _ST_MID, _ST_LGT, _ST_HI]
    for row in range(rect.top, rect.bottom, block_h):
        offset = (block_w // 2) if ((row - rect.top) // block_h) % 2 == 0 else 0
        for col in range(rect.left - block_w, rect.right + block_w, block_w):
            bx = col + offset
            x1 = max(rect.left, bx + 1)
            x2 = min(rect.right, bx + block_w - 1)
            y1 = max(rect.top, row + 1)
            y2 = min(rect.bottom, row + block_h - 1)
            if x2 <= x1 or y2 <= y1:
                continue
            shade = shades[rng.randint(0, 3)]
            pygame.draw.rect(surf, shade, (x1, y1, x2 - x1, y2 - y1))
            pygame.draw.line(surf, _ST_HI, (x1, y1), (x2 - 1, y1))
            pygame.draw.line(surf, _ST_HI, (x1, y1), (x1, y2 - 1))
            pygame.draw.line(surf, _MORTAR, (x1, y2 - 1), (x2 - 1, y2 - 1))
            pygame.draw.line(surf, _MORTAR, (x2 - 1, y1), (x2 - 1, y2 - 1))


# ── Item icons displayed on shop fronts ──────────────────────────────────────
# Maps specialty → base_name used to look up assets/items/{name}.png
_SPECIALTY_ICON = {
    "weapons": "Broad Sword",
    "armor":   "Plate Armor",
    "jewelry": "Gold Ring",
    "potions": "health_potion",
    "enchant": "Ancient Amulet",
    "craft":   "Quarterstaff",
}

_facade_cache: dict[str, pygame.Surface | None] = {}
_icon_cache:   dict[str, pygame.Surface | None] = {}


def _load_facade(specialty: str, w: int, h: int) -> pygame.Surface | None:
    key = f"{specialty}_{w}_{h}"
    if key in _facade_cache:
        return _facade_cache[key]
    from pathlib import Path, PurePath
    import sys
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "assets" / "town"     # type: ignore
    else:
        base = Path(__file__).parent.parent.parent / "assets" / "town"
    path = base / f"facade_{specialty}.png"
    if path.exists():
        try:
            raw  = pygame.image.load(str(path)).convert_alpha()
            surf = pygame.transform.smoothscale(raw, (w, h))
            _facade_cache[key] = surf
            return surf
        except Exception:
            pass
    _facade_cache[key] = None
    return None


def _load_item_icon(specialty: str, size: int) -> pygame.Surface | None:
    key = f"{specialty}_{size}"
    if key in _icon_cache:
        return _icon_cache[key]
    from pathlib import Path
    import sys
    base_name = _SPECIALTY_ICON.get(specialty)
    if not base_name:
        _icon_cache[key] = None
        return None
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "assets" / "items"    # type: ignore
    else:
        base = Path(__file__).parent.parent.parent / "assets" / "items"
    path = base / f"{base_name}.png"
    if path.exists():
        try:
            raw  = pygame.image.load(str(path)).convert_alpha()
            surf = pygame.transform.smoothscale(raw, (size, size))
            _icon_cache[key] = surf
            return surf
        except Exception:
            pass
    _icon_cache[key] = None
    return None


def _draw_building(surf, px, py, pal, seed=0, specialty=""):
    """Draw a full merchant building facade centered at (px, py)."""
    BW, BH = BUILDING_W, BUILDING_H
    bx = px - BW // 2
    by = py - BH // 2 - 20   # shifted up so merchant stands in front

    # ── Drop shadow ──────────────────────────────────────────────────────────
    sh_surf = pygame.Surface((BW + 12, BH + 16), pygame.SRCALPHA)
    sh_surf.fill((0, 0, 0, 80))
    surf.blit(sh_surf, (bx + 6, by + 6))

    # ── Wall: try PNG facade first, fall back to procedural ──────────────────
    facade = _load_facade(specialty, BW, BH) if specialty else None
    if facade is not None:
        surf.blit(facade, (bx, by))
    else:
        # Procedural stone base + timber-frame wall
        base_r = pygame.Rect(bx, by + BH - 40, BW, 40)
        _draw_stone_blocks(surf, base_r, 28, 14, seed=seed)
        pygame.draw.rect(surf, _MORTAR, base_r, 1)

        wall_r = pygame.Rect(bx, by, BW, BH - 40)
        pygame.draw.rect(surf, _PL_BASE, wall_r)
        _grad_rect(surf, wall_r, _PL_SHD, _PL_BASE)
        for beam_x in range(bx, bx + BW + 1, BW // 3):
            pygame.draw.rect(surf, _WD_DARK, (beam_x - 3, by, 6, BH - 40))
            pygame.draw.line(surf, _WD_MID, (beam_x - 2, by), (beam_x - 2, by + BH - 40))
        for beam_y in [by, by + (BH - 40) // 2, by + BH - 40]:
            pygame.draw.rect(surf, _WD_DARK, (bx, beam_y - 3, BW, 6))
            pygame.draw.line(surf, _WD_MID, (bx, beam_y - 2), (bx + BW, beam_y - 2))
        panel_w = BW // 3
        for pi in range(3):
            px1 = bx + pi * panel_w
            py1 = by
            py2 = by + (BH - 40)
            pygame.draw.line(surf, _WD_DARK, (px1 + 4, py1 + 4), (px1 + panel_w - 4, py2 - 4), 2)
            pygame.draw.line(surf, _WD_DARK, (px1 + panel_w - 4, py1 + 4), (px1 + 4, py2 - 4), 2)

    # ── Specialty item icon on facade ─────────────────────────────────────────
    if specialty:
        icon = _load_item_icon(specialty, 44)
        if icon is not None:
            ix = bx + BW // 2 - 22
            iy = by + 14
            bg_circ = pygame.Surface((48, 48), pygame.SRCALPHA)
            pygame.draw.circle(bg_circ, (0, 0, 0, 140), (24, 24), 24)
            surf.blit(bg_circ, (ix - 2, iy - 2))
            surf.blit(icon, (ix, iy))
            ring_col = pal.get("hi", (180, 180, 180))
            pygame.draw.circle(surf, ring_col, (bx + BW // 2, iy + 22), 24, 2)

    # ── Pitched roof ─────────────────────────────────────────────────────────
    roof_pts = [
        (bx - 8,      by),
        (bx + BW + 8, by),
        (bx + BW + 14, by - 10),
        (bx + BW // 2, by - 48),
        (bx - 14,     by - 10),
    ]
    pygame.draw.polygon(surf, _RF_MID, roof_pts)
    pygame.draw.polygon(surf, _RF_DARK, roof_pts, 3)
    # roof ridge highlight
    pygame.draw.line(surf, _RF_LGT,
                     (bx - 14, by - 10), (bx + BW // 2, by - 48))
    pygame.draw.line(surf, _RF_LGT,
                     (bx + BW // 2, by - 48), (bx + BW + 14, by - 10))
    # roof tiles (horizontal lines)
    for ry in range(by - 8, by, 4):
        t_ = (by - ry) / 48.0
        tile_w = int((BW + 28) * (1.0 - t_ * 0.5))
        pygame.draw.line(surf, _RF_DARK,
                         (bx + BW // 2 - tile_w // 2, ry),
                         (bx + BW // 2 + tile_w // 2, ry))

    # ── Shop awning / counter ─────────────────────────────────────────────────
    aw_col  = pal["awning"]
    aw_hi   = pal["hi"]
    aw_r    = pygame.Rect(bx - 14, by + BH - 44, BW + 28, 18)
    pygame.draw.rect(surf, aw_col, aw_r)
    # awning stripes
    stripe_col = tuple(min(255, c + 30) for c in aw_col)
    for sx_ in range(aw_r.left + 6, aw_r.right, 16):
        pygame.draw.line(surf, stripe_col,
                         (sx_, aw_r.top), (sx_ - 8, aw_r.bottom), 2)
    pygame.draw.rect(surf, aw_hi, aw_r, 2)
    # awning scalloped bottom edge
    for sx_ in range(aw_r.left, aw_r.right - 10, 14):
        pygame.draw.arc(surf, aw_hi,
                        pygame.Rect(sx_, aw_r.bottom - 4, 14, 10),
                        0, math.pi, 2)

    # ── Hanging sign board ────────────────────────────────────────────────────
    post_x = bx + BW // 2
    post_y = by - 14
    pygame.draw.line(surf, _WD_DARK, (post_x, post_y), (post_x, post_y - 22), 3)
    sign_r = pygame.Rect(post_x - 36, post_y - 42, 72, 20)
    pygame.draw.rect(surf, _WD_MID, sign_r)
    pygame.draw.rect(surf, _WD_DARK, sign_r, 2)
    pygame.draw.line(surf, _WD_LGT, (sign_r.left, sign_r.top), (sign_r.right, sign_r.top))
    # thin rope lines from sign to beam
    pygame.draw.line(surf, _WD_DARK,
                     (sign_r.left + 6, sign_r.top), (post_x - 8, post_y - 22), 1)
    pygame.draw.line(surf, _WD_DARK,
                     (sign_r.right - 6, sign_r.top), (post_x + 8, post_y - 22), 1)

    # ── Outline ───────────────────────────────────────────────────────────────
    pygame.draw.rect(surf, _WD_DARK, (bx, by, BW, BH), 2)


def _draw_tree(surf, cx, cy, seed=0):
    """Draw a layered foliage tree with trunk and shadow."""
    rng = random.Random(seed)
    trunk_w = 14
    trunk_h = 38
    # shadow
    sh = pygame.Surface((60, 20), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 60), (0, 0, 60, 20))
    surf.blit(sh, (cx - 30, cy + trunk_h // 2 - 6))
    # trunk
    _grad_rect(surf, pygame.Rect(cx - trunk_w // 2, cy - trunk_h // 2,
                                 trunk_w, trunk_h), _WD_DARK, _WD_MID)
    pygame.draw.line(surf, _WD_LGT,
                     (cx - trunk_w // 2 + 2, cy - trunk_h // 2),
                     (cx - trunk_w // 2 + 2, cy + trunk_h // 2))
    # foliage — 3 overlapping circles
    for r_, col, dy_ in [
        (36, _LF_DARK, 0),
        (30, _LF_MID,  -8 + rng.randint(-4, 4)),
        (22, _LF_LGT,  -18 + rng.randint(-4, 4)),
    ]:
        foliage_s = pygame.Surface((r_ * 2, r_ * 2), pygame.SRCALPHA)
        pygame.draw.circle(foliage_s, (*col, 230), (r_, r_), r_)
        # highlight
        pygame.draw.circle(foliage_s, (min(255, col[0]+12),
                                       min(255, col[1]+20),
                                       min(255, col[2]+8), 100),
                           (r_ - 4, r_ - 6), r_ // 3)
        surf.blit(foliage_s, (cx - r_, cy - trunk_h // 2 + dy_ - r_))


def _draw_barrel(surf, bx, by):
    """Draw a decorative barrel."""
    bw, bh = 22, 30
    _grad_rect(surf, pygame.Rect(bx, by, bw, bh), _WD_MID, _WD_DARK)
    # top ellipse (curved top)
    pygame.draw.ellipse(surf, _WD_LGT, (bx, by - 5, bw, 10))
    pygame.draw.ellipse(surf, _WD_MID, (bx, by - 4, bw, 8))
    # iron hoops
    for hy in [by + bh // 4, by + bh * 3 // 4]:
        pygame.draw.rect(surf, _IR_MID, (bx - 1, hy - 2, bw + 2, 4))
        pygame.draw.line(surf, _IR_LGT, (bx, hy - 2), (bx + bw, hy - 2))
    pygame.draw.rect(surf, _WD_DARK, (bx, by, bw, bh), 1)


def _draw_crate(surf, bx, by):
    """Draw a decorative wooden crate."""
    cw, ch = 28, 26
    _grad_rect(surf, pygame.Rect(bx, by, cw, ch), _WD_LGT, _WD_MID)
    # cross-hatch planks
    pygame.draw.line(surf, _WD_DARK, (bx, by), (bx + cw, by + ch), 1)
    pygame.draw.line(surf, _WD_DARK, (bx + cw, by), (bx, by + ch), 1)
    pygame.draw.rect(surf, _WD_DARK, (bx, by + ch // 2 - 1, cw, 2))
    pygame.draw.rect(surf, _WD_DARK, (bx + cw // 2 - 1, by, 2, ch))
    pygame.draw.rect(surf, _WD_DARK, (bx, by, cw, ch), 2)
    pygame.draw.line(surf, _WD_LGT, (bx + 1, by + 1), (bx + cw - 1, by + 1))


def _draw_fountain(surf, cx, cy):
    """Draw a multi-layered stone fountain with iron fence posts."""
    # outer stone ring — multiple passes for depth
    for rad, col, thick in [
        (56, _ST_DARK, 0),   # filled base disc
        (52, _ST_MID,  14),
        (52, _ST_LGT,  3),
        (52, _ST_HI,   1),
    ]:
        if thick == 0:
            pygame.draw.circle(surf, col, (cx, cy), rad)
        else:
            pygame.draw.circle(surf, col, (cx, cy), rad, thick)
    # inner stone rim
    pygame.draw.circle(surf, _ST_MID, (cx, cy), 38, 10)
    pygame.draw.circle(surf, _ST_HI,  (cx, cy), 38, 1)
    # water pool
    water_s = pygame.Surface((56, 56), pygame.SRCALPHA)
    pygame.draw.circle(water_s, (*_WA_MID, 220), (28, 28), 28)
    # ripple
    pygame.draw.circle(water_s, (*_WA_DARK, 140), (28, 28), 18, 2)
    pygame.draw.circle(water_s, (*_WA_DARK, 80),  (28, 28), 10, 1)
    surf.blit(water_s, (cx - 28, cy - 28))
    # central pillar
    pygame.draw.circle(surf, _ST_MID, (cx, cy), 8)
    pygame.draw.circle(surf, _ST_HI,  (cx, cy), 8, 1)
    # iron fence posts (8 posts at radius 68)
    for i in range(8):
        ang = i * math.pi * 2 / 8
        fx = int(cx + math.cos(ang) * 68)
        fy = int(cy + math.sin(ang) * 68)
        # post
        pygame.draw.rect(surf, _IR_DARK, (fx - 3, fy - 12, 6, 24))
        pygame.draw.rect(surf, _IR_MID,  (fx - 2, fy - 11, 4, 22))
        pygame.draw.line(surf, _IR_LGT,  (fx - 1, fy - 10), (fx - 1, fy + 10))
        # spear tip
        pts = [(fx, fy - 16), (fx - 3, fy - 12), (fx + 3, fy - 12)]
        pygame.draw.polygon(surf, _IR_MID, pts)
        pygame.draw.polygon(surf, _IR_LGT, pts, 1)
    # iron fence rails connecting posts
    for i in range(8):
        ang1 = i * math.pi * 2 / 8
        ang2 = (i + 1) * math.pi * 2 / 8
        x1 = int(cx + math.cos(ang1) * 68)
        y1 = int(cy + math.sin(ang1) * 68)
        x2 = int(cx + math.cos(ang2) * 68)
        y2 = int(cy + math.sin(ang2) * 68)
        pygame.draw.line(surf, _IR_MID, (x1, y1 - 6), (x2, y2 - 6), 2)
        pygame.draw.line(surf, _IR_MID, (x1, y1 + 4), (x2, y2 + 4), 1)


def _draw_dungeon_gate(surf, ex, ey):
    """Draw a tall stone gate with portcullis at the dungeon entrance."""
    col_w, col_h = 30, 108
    gate_w = 80   # inner opening width
    arch_h = 56   # height of pointed arch above opening

    # columns
    for cx_, cy_ in [(ex - gate_w // 2 - col_w, ey - col_h // 2),
                     (ex + gate_w // 2,          ey - col_h // 2)]:
        col_r = pygame.Rect(cx_, cy_, col_w, col_h)
        _draw_stone_blocks(surf, col_r, 16, 12, seed=hash((cx_, cy_)))
        pygame.draw.rect(surf, _MORTAR, col_r, 2)
        # column cap
        cap_r = pygame.Rect(cx_ - 4, cy_ - 8, col_w + 8, 10)
        pygame.draw.rect(surf, _ST_HI, cap_r)
        pygame.draw.rect(surf, _MORTAR, cap_r, 1)
        # torch bracket
        torch_x = cx_ + col_w // 2
        torch_y = cy_ + col_h // 3
        pygame.draw.rect(surf, _IR_DARK, (torch_x - 2, torch_y - 12, 4, 14))
        pygame.draw.rect(surf, _IR_MID,  (torch_x - 4, torch_y - 4, 8, 6))

    # pointed arch stone lintel
    arch_top_y = ey - col_h // 2 - arch_h
    arch_pts = [
        (ex - gate_w // 2 - col_w, ey - col_h // 2),
        (ex - gate_w // 2 - col_w, ey - col_h // 2 + 10),
        (ex - gate_w // 2,         ey - col_h // 2 + 10),
        (ex - gate_w // 2,         ey - col_h // 2 - 20),
        (ex,                        arch_top_y),
        (ex + gate_w // 2,         ey - col_h // 2 - 20),
        (ex + gate_w // 2,         ey - col_h // 2 + 10),
        (ex + gate_w // 2 + col_w, ey - col_h // 2 + 10),
        (ex + gate_w // 2 + col_w, ey - col_h // 2),
    ]
    pygame.draw.polygon(surf, _ST_MID, arch_pts)
    pygame.draw.polygon(surf, _ST_HI,  arch_pts, 2)
    # keystone
    ks_r = pygame.Rect(ex - 10, arch_top_y - 8, 20, 14)
    pygame.draw.rect(surf, _ST_HI, ks_r)
    pygame.draw.rect(surf, _MORTAR, ks_r, 1)

    # inner void (dark passage)
    void_r = pygame.Rect(ex - gate_w // 2, ey - col_h // 2,
                         gate_w, col_h // 2 + 20)
    pygame.draw.rect(surf, (14, 8, 24), void_r)
    # pointed arch void cutout
    void_arch_pts = [
        (ex - gate_w // 2, ey - col_h // 2),
        (ex - gate_w // 2, ey - col_h // 2 - 18),
        (ex,               ey - col_h // 2 - arch_h + 16),
        (ex + gate_w // 2, ey - col_h // 2 - 18),
        (ex + gate_w // 2, ey - col_h // 2),
    ]
    pygame.draw.polygon(surf, (14, 8, 24), void_arch_pts)

    # iron portcullis bars (vertical)
    bar_top    = ey - col_h // 2 - 14
    bar_bottom = ey - col_h // 2 + 18
    for bx_ in range(ex - gate_w // 2 + 6, ex + gate_w // 2 - 4, 12):
        pygame.draw.line(surf, _IR_DARK,  (bx_, bar_top), (bx_, bar_bottom), 3)
        pygame.draw.line(surf, _IR_MID,   (bx_, bar_top), (bx_, bar_bottom), 1)
        # pointed bar tips
        pts = [(bx_, bar_bottom + 6), (bx_ - 3, bar_bottom), (bx_ + 3, bar_bottom)]
        pygame.draw.polygon(surf, _IR_MID, pts)
    # horizontal bars
    for hy_ in [bar_top + 8, bar_top + (bar_bottom - bar_top) // 2]:
        pygame.draw.line(surf, _IR_DARK,
                         (ex - gate_w // 2 + 6, hy_),
                         (ex + gate_w // 2 - 6, hy_), 3)
        pygame.draw.line(surf, _IR_MID,
                         (ex - gate_w // 2 + 6, hy_),
                         (ex + gate_w // 2 - 6, hy_), 1)


def _draw_tower(surf, cx, cy, radius, n_sides=10):
    """Draw a stone tower centered at (cx,cy), clipped naturally at screen edges."""
    # Fill layers: dark → mid → light for a rounded 3D look
    for shrink, col in [(0, _ST_DARK), (5, _ST_MID), (12, _ST_LGT), (18, _ST_HI)]:
        r = radius - shrink
        pts = []
        for i in range(n_sides):
            ang = i * 2 * math.pi / n_sides - math.pi / n_sides
            pts.append((int(cx + math.cos(ang) * r), int(cy + math.sin(ang) * r)))
        if shrink < 18:
            pygame.draw.polygon(surf, col, pts)
        else:
            pygame.draw.polygon(surf, col, pts, 2)

    # Battlements around tower perimeter
    for i in range(n_sides * 2):
        ang = i * math.pi / n_sides
        if i % 2 == 0:
            inner_r = radius - 2
            outer_r = radius + 10
            ang_w   = math.pi / (n_sides * 1.8)
            pts = [
                (int(cx + math.cos(ang - ang_w) * inner_r),
                 int(cy + math.sin(ang - ang_w) * inner_r)),
                (int(cx + math.cos(ang + ang_w) * inner_r),
                 int(cy + math.sin(ang + ang_w) * inner_r)),
                (int(cx + math.cos(ang + ang_w) * outer_r),
                 int(cy + math.sin(ang + ang_w) * outer_r)),
                (int(cx + math.cos(ang - ang_w) * outer_r),
                 int(cy + math.sin(ang - ang_w) * outer_r)),
            ]
            pygame.draw.polygon(surf, _ST_MID, pts)
            pygame.draw.polygon(surf, _ST_HI,  pts, 1)

    # Stone texture ring
    pygame.draw.circle(surf, _MORTAR, (cx, cy), radius, 2)


def _draw_house(surf, px, py):
    """Draw the player's cozy timber-frame cottage — door, windows, chimney, fence."""
    BW, BH = 180, 128
    bx = px - BW // 2
    by = py - BH // 2 - 15   # shift up so player stands in front

    # ── Drop shadow ───────────────────────────────────────────────────────────
    sh = pygame.Surface((BW + 16, BH + 20), pygame.SRCALPHA)
    sh.fill((0, 0, 0, 90))
    surf.blit(sh, (bx + 7, by + 7))

    # ── Stone base (lower 32px) ───────────────────────────────────────────────
    base_r = pygame.Rect(bx, by + BH - 32, BW, 32)
    _draw_stone_blocks(surf, base_r, 24, 12, seed=9001)
    pygame.draw.rect(surf, _MORTAR, base_r, 1)

    # ── Warm plaster wall (upper portion) ─────────────────────────────────────
    _PL_WARM     = (172, 156, 124)
    _PL_WARM_SHD = (148, 132, 104)
    wall_r = pygame.Rect(bx, by, BW, BH - 32)
    pygame.draw.rect(surf, _PL_WARM, wall_r)
    _grad_rect(surf, wall_r, _PL_WARM_SHD, _PL_WARM)

    # Timber beams — thirds
    for beam_x in [bx, bx + BW // 3, bx + 2 * BW // 3, bx + BW]:
        pygame.draw.rect(surf, _WD_DARK, (beam_x - 3, by, 6, BH - 32))
        pygame.draw.line(surf, _WD_MID,
                         (beam_x - 2, by), (beam_x - 2, by + BH - 32))
    for beam_y in [by, by + (BH - 32) // 2, by + BH - 32]:
        pygame.draw.rect(surf, _WD_DARK, (bx, beam_y - 3, BW, 6))
        pygame.draw.line(surf, _WD_MID, (bx, beam_y - 2), (bx + BW, beam_y - 2))

    # ── Windows — left and right of door, upper half ─────────────────────────
    win_w = BW // 5
    win_h = (BH - 32) // 3
    win_y = by + 10
    for wx in [bx + 14, bx + BW - 14 - win_w]:
        # Warm interior glow
        glow_s = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
        glow_s.fill((255, 200, 80, 130))
        surf.blit(glow_s, (wx, win_y))
        # Frame + cross panes
        pygame.draw.rect(surf, _WD_DARK, (wx, win_y, win_w, win_h), 3)
        pygame.draw.line(surf, _WD_DARK,
                         (wx + win_w // 2, win_y), (wx + win_w // 2, win_y + win_h), 2)
        pygame.draw.line(surf, _WD_DARK,
                         (wx, win_y + win_h // 2), (wx + win_w, win_y + win_h // 2), 2)

    # ── Front door (bottom-centre of plaster wall) ────────────────────────────
    door_w = 36
    door_h = 64
    door_x = px - door_w // 2
    door_y = by + (BH - 32) - door_h
    # Door body — warm wood gradient
    _grad_rect(surf, pygame.Rect(door_x, door_y, door_w, door_h),
               (60, 36, 12), (44, 26, 8))
    # Arched top
    pygame.draw.ellipse(surf, (52, 30, 10), (door_x, door_y - 8, door_w, 20))
    pygame.draw.ellipse(surf, _WD_DARK,    (door_x, door_y - 8, door_w, 20), 2)
    # Vertical centre divide
    pygame.draw.line(surf, _WD_DARK, (px, door_y), (px, door_y + door_h), 1)
    # Four recessed panels
    panel_w = door_w // 2 - 6
    for pdx in [door_x + 4, door_x + door_w // 2 + 2]:
        for pdy in [door_y + 4, door_y + 34]:
            pygame.draw.rect(surf, (48, 28, 8), (pdx, pdy, panel_w, 26))
    # Brass knob
    pygame.draw.circle(surf, (190, 150, 30),
                       (door_x + door_w - 6, door_y + door_h // 2), 3)
    # Iron hinges
    for hy_ in [door_y + 10, door_y + door_h - 14]:
        pygame.draw.rect(surf, _IR_MID, (door_x + 2, hy_ - 3, 8, 5))
    pygame.draw.rect(surf, _WD_DARK, (door_x, door_y, door_w, door_h), 2)

    # ── Door-side torch brackets ──────────────────────────────────────────────
    for tx_ in [door_x - 14, door_x + door_w + 8]:
        pygame.draw.rect(surf, _IR_DARK, (tx_ - 2, door_y - 14, 4, 14))
        pygame.draw.rect(surf, _IR_MID,  (tx_ - 4, door_y - 6, 8, 6))
        pygame.draw.rect(surf, _WD_DARK, (tx_ - 2, door_y - 4, 4, 8))

    # ── Chimney (drawn BEFORE roof so roof polygon overlaps its base) ─────────
    ch_w = 20
    ch_x = bx + int(BW * 0.70) - ch_w // 2
    ch_top = by - 58
    ch_h   = 50
    ch_r   = pygame.Rect(ch_x, ch_top, ch_w, ch_h)
    _draw_stone_blocks(surf, ch_r, 10, 8, seed=5678)
    pygame.draw.rect(surf, _MORTAR, ch_r, 1)

    # ── Pitched roof (covers lower chimney) ───────────────────────────────────
    roof_pts = [
        (bx - 10,      by),
        (bx + BW + 10, by),
        (bx + BW + 14, by - 8),
        (bx + BW // 2, by - 44),
        (bx - 14,      by - 8),
    ]
    pygame.draw.polygon(surf, _RF_MID, roof_pts)
    pygame.draw.polygon(surf, _RF_DARK, roof_pts, 3)
    pygame.draw.line(surf, _RF_LGT, (bx - 14,      by - 8), (bx + BW // 2, by - 44))
    pygame.draw.line(surf, _RF_LGT, (bx + BW // 2, by - 44), (bx + BW + 14, by - 8))
    for ry in range(by - 6, by, 4):
        t_ = (by - ry) / 44.0
        tile_w = int((BW + 28) * (1.0 - t_ * 0.5))
        pygame.draw.line(surf, _RF_DARK,
                         (bx + BW // 2 - tile_w // 2, ry),
                         (bx + BW // 2 + tile_w // 2, ry))

    # ── Chimney cap on top of roof ────────────────────────────────────────────
    pygame.draw.rect(surf, _ST_HI, (ch_x - 3, ch_top - 4, ch_w + 6, 6))

    # ── Hanging sign board ────────────────────────────────────────────────────
    post_x = px
    post_y = by - 14
    pygame.draw.line(surf, _WD_DARK, (post_x, post_y), (post_x, post_y - 22), 3)
    sign_r = pygame.Rect(post_x - 36, post_y - 42, 72, 20)
    pygame.draw.rect(surf, _WD_MID, sign_r)
    pygame.draw.rect(surf, _WD_DARK, sign_r, 2)
    pygame.draw.line(surf, _WD_LGT, (sign_r.left, sign_r.top), (sign_r.right, sign_r.top))
    pygame.draw.line(surf, _WD_DARK,
                     (sign_r.left + 6, sign_r.top), (post_x - 8, post_y - 22), 1)
    pygame.draw.line(surf, _WD_DARK,
                     (sign_r.right - 6, sign_r.top), (post_x + 8, post_y - 22), 1)

    # ── Picket fence ──────────────────────────────────────────────────────────
    fence_y = by + BH + 6
    for fx in range(bx - 14, bx + BW + 18, 18):
        # Pointed picket
        pts = [(fx + 1, fence_y - 5), (fx - 2, fence_y), (fx + 4, fence_y)]
        pygame.draw.polygon(surf, _WD_LGT, pts)
        pygame.draw.rect(surf, _WD_MID, (fx - 2, fence_y, 5, 18))
        pygame.draw.line(surf, _WD_LGT, (fx - 1, fence_y), (fx - 1, fence_y + 15))
    pygame.draw.line(surf, _WD_DARK,
                     (bx - 14, fence_y + 8), (bx + BW + 14, fence_y + 8), 2)
    pygame.draw.line(surf, _WD_DARK,
                     (bx - 14, fence_y + 15), (bx + BW + 14, fence_y + 15), 1)

    # ── Building outline ──────────────────────────────────────────────────────
    pygame.draw.rect(surf, _WD_DARK, (bx, by, BW, BH), 2)


def _draw_outer_walls(surf):
    """Draw irregular stone outer walls: thin bands with large corner towers
    and mid-wall towers that break up every straight run."""
    B  = 50   # wall band thickness
    CR = 96   # corner tower radius  (centred at map corners, curves inward)
    MR = 62   # mid-wall tower radius

    # ── 1. Wall bands (thin rectangular stone sections) ───────────────────────
    for wr in [
        pygame.Rect(0,           0,           TOWN_W, B),
        pygame.Rect(0,           TOWN_H - B,  TOWN_W, B),
        pygame.Rect(0,           B,           B,      TOWN_H - B * 2),
        pygame.Rect(TOWN_W - B,  B,           B,      TOWN_H - B * 2),
    ]:
        _draw_stone_blocks(surf, wr, 20, 13, seed=hash(str(wr)))
        pygame.draw.rect(surf, _MORTAR, wr, 1)

    # Thin inner-edge highlight so the wall reads as raised
    pygame.draw.rect(surf, _ST_HI,  (B, B, TOWN_W - B * 2, TOWN_H - B * 2), 2)
    pygame.draw.rect(surf, _ST_MID, (B + 3, B + 3, TOWN_W - B * 2 - 6, TOWN_H - B * 2 - 6), 1)

    # ── 2. Battlements along wall outer edges ─────────────────────────────────
    mw, mh, cw = 20, 16, 12
    step = mw + cw
    # Top / bottom
    for mx in range(CR // 2, TOWN_W - CR // 2 - mw, step):
        for my_, flip in [(0, False), (TOWN_H - mh, True)]:
            mr = pygame.Rect(mx, my_, mw, mh)
            pygame.draw.rect(surf, _ST_MID, mr)
            pygame.draw.rect(surf, _ST_HI,  mr, 1)
    # Left / right
    for my in range(CR // 2, TOWN_H - CR // 2 - mw, step):
        for mx_ in [(0, mh), (TOWN_W - mh, mh)]:
            mr = pygame.Rect(mx_[0], my, mx_[1], mw)
            pygame.draw.rect(surf, _ST_MID, mr)
            pygame.draw.rect(surf, _ST_HI,  mr, 1)

    # ── 3. Corner towers — centred at screen corners, protrude inward ─────────
    for cx, cy in [(0, 0), (TOWN_W, 0), (0, TOWN_H), (TOWN_W, TOWN_H)]:
        _draw_tower(surf, cx, cy, CR, n_sides=12)

    # ── 4. Mid-wall towers — break up the long straight runs ──────────────────
    ex = DUNGEON_ENTRANCE_POS[0]
    mid_towers = [
        # top wall: flank gate on both sides
        (ex - 400, 0), (ex + 400, 0),
        # bottom wall: three evenly spaced
        (TOWN_W // 4, TOWN_H), (TOWN_W // 2, TOWN_H), (3 * TOWN_W // 4, TOWN_H),
        # left wall: three
        (0, TOWN_H // 4), (0, TOWN_H // 2), (0, 3 * TOWN_H // 4),
        # right wall: three
        (TOWN_W, TOWN_H // 4), (TOWN_W, TOWN_H // 2), (TOWN_W, 3 * TOWN_H // 4),
    ]
    for cx, cy in mid_towers:
        _draw_tower(surf, cx, cy, MR, n_sides=10)

    # ── 5. Gate gap in top wall ────────────────────────────────────────────────
    ex, ey = DUNGEON_ENTRANCE_POS
    gap = 94
    pygame.draw.rect(surf, _GR_DARK, (ex - gap // 2, 0, gap, B + 2))


def _draw_ground(surf):
    """Draw earth base, gravel scatter, central plaza, and paved paths."""
    rng = random.Random(42)

    # ── Dark earth base ───────────────────────────────────────────────────────
    surf.fill(_GR_DARK)

    # ── Soil texture patches ──────────────────────────────────────────────────
    for _ in range(620):
        px_ = rng.randint(0, TOWN_W - 1)
        py_ = rng.randint(0, TOWN_H - 1)
        r_  = rng.randint(12, 40)
        shade = rng.choice([_GR_MID, _GR_LGT, _GR_DARK])
        alpha = rng.randint(40, 90)
        patch = pygame.Surface((r_ * 2, r_ * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(patch, (*shade, alpha), (0, 0, r_ * 2, r_ * 2))
        surf.blit(patch, (px_ - r_, py_ - r_))

    # ── Pebble/gravel scatter ─────────────────────────────────────────────────
    for _ in range(3600):
        px_ = rng.randint(0, TOWN_W - 1)
        py_ = rng.randint(0, TOWN_H - 1)
        shade = rng.choice([_GR_MID, _GR_LGT, (55, 45, 32), (40, 32, 20)])
        pygame.draw.circle(surf, shade, (px_, py_), rng.randint(1, 3))

    def _pave(r, slab_w, slab_h, col_dark, col_lgt, mort):
        pygame.draw.rect(surf, mort, r)
        for row in range(r.top - slab_h, r.bottom + slab_h, slab_h):
            off = (slab_w // 2) if ((row - r.top) // slab_h) % 2 == 0 else 0
            for col in range(r.left - slab_w, r.right + slab_w, slab_w):
                sx = col + off
                x1 = max(r.left, sx + 2);   x2 = min(r.right, sx + slab_w - 2)
                y1 = max(r.top,  row + 2);   y2 = min(r.bottom, row + slab_h - 2)
                if x2 <= x1 + 2 or y2 <= y1 + 2:
                    continue
                v = ((sx // slab_w + row // slab_h) * 17) % 18
                shade = (col_dark[0] + v, col_dark[1] + v // 2, col_dark[2] + v // 3)
                pygame.draw.rect(surf, shade, (x1, y1, x2 - x1, y2 - y1))
                pygame.draw.line(surf, col_lgt, (x1, y1), (x2, y1))
                pygame.draw.line(surf, col_lgt, (x1, y1), (x1, y2))
                pygame.draw.line(surf, mort, (x1, y2 - 1), (x2, y2 - 1))
                pygame.draw.line(surf, mort, (x2 - 1, y1), (x2 - 1, y2))

    B_INNER = 50
    PATH_W  = 100

    # ── Central plaza — wide lighter cobblestone square ───────────────────────
    PZ_W, PZ_H = 700, 480
    plaza_r = pygame.Rect(PLAZA_CX - PZ_W // 2, PLAZA_CY - PZ_H // 2, PZ_W, PZ_H)
    _pave(plaza_r, 62, 42,
          (_PA_MID[0] + 6, _PA_MID[1] + 6, _PA_MID[2] + 4),
          _PA_LGT, _PA_MORT)
    # Stone curb around plaza
    pygame.draw.rect(surf, _ST_MID, plaza_r, 5)
    pygame.draw.rect(surf, _ST_HI,  (plaza_r.x + 1, plaza_r.y + 1, plaza_r.w - 2, 3))
    pygame.draw.rect(surf, _ST_HI,  (plaza_r.x + 1, plaza_r.y + 1, 3, plaza_r.h - 2))

    # ── Paths (drawn on top so they visually cut through the plaza) ───────────
    # Vertical spine: gate → bottom wall
    vpath_r  = pygame.Rect(PLAZA_CX - PATH_W // 2, 62, PATH_W, TOWN_H - 62)
    # Upper cross: Blacksmith ↔ Armourer
    hpath1_r = pygame.Rect(B_INNER, 340 - PATH_W // 2, TOWN_W - 2 * B_INNER, PATH_W)
    # Middle cross: Craftsman ↔ Enchanter (through plaza)
    hpath2_r = pygame.Rect(B_INNER, 820 - PATH_W // 2, TOWN_W - 2 * B_INNER, PATH_W)
    # Lower cross: Jeweler ↔ House
    hpath3_r = pygame.Rect(B_INNER, 1300 - PATH_W // 2, TOWN_W - 2 * B_INNER, PATH_W)

    for path_r in [vpath_r, hpath1_r, hpath2_r, hpath3_r]:
        _pave(path_r, 52, 36, _PA_DARK, _PA_LGT, _PA_MORT)


# ── TownRenderer — draws the static and dynamic town scene ────────────────────

class TownRenderer:
    """
    Renders the town background (cached) plus animated elements
    (dungeon entrance glow, merchant interaction hints).
    """

    def __init__(self):
        self._bg:   pygame.Surface | None = None
        self._font: pygame.font.Font | None = None
        self._font_sm: pygame.font.Font | None = None
        # Torch positions for animation (filled by _build_bg)
        self._torch_positions: list[tuple[int, int]] = []
        # Random phases so torches flicker independently
        self._torch_phases: list[float] = []

    # ── Init ──────────────────────────────────────────────────────────────────

    def _ensure_fonts(self):
        if self._font is None:
            self._font    = pygame.font.SysFont("monospace", 28, bold=True)
            self._font_sm = pygame.font.SysFont("monospace", 25)

    def _build_bg(self) -> pygame.Surface:
        """Build the static background surface — rich medieval town."""
        surf = pygame.Surface((TOWN_W, TOWN_H))

        # ── 1. Ground (must be first — everything paints on top) ──────────────
        _draw_ground(surf)

        # ── 2. Outer walls ────────────────────────────────────────────────────
        _draw_outer_walls(surf)

        # ── 3. Central fountain (plaza centrepiece) ───────────────────────────
        _draw_fountain(surf, PLAZA_CX, PLAZA_CY)

        # ── 4. Trees — corners + plaza corners + upper flanks ─────────────────
        B = 50
        tree_positions = [
            # Far wall corners
            (B + 100,          B + 100),
            (TOWN_W - B - 100, B + 100),
            (B + 100,          TOWN_H - B - 100),
            (TOWN_W - B - 100, TOWN_H - B - 100),
            # Flanking left/right mid-wall towers
            (B + 80,           TOWN_H // 4 + 60),
            (TOWN_W - B - 80,  TOWN_H // 4 + 60),
            (B + 80,           3 * TOWN_H // 4 - 60),
            (TOWN_W - B - 80,  3 * TOWN_H // 4 - 60),
            # Plaza corners — frame the open square
            (PLAZA_CX - 400,   PLAZA_CY - 280),
            (PLAZA_CX + 400,   PLAZA_CY - 280),
            (PLAZA_CX - 400,   PLAZA_CY + 280),
            (PLAZA_CX + 400,   PLAZA_CY + 280),
            # Upper area between gate and upper-row merchants
            (PLAZA_CX - 210,   210),
            (PLAZA_CX + 210,   210),
        ]
        for i, (tx, ty) in enumerate(tree_positions):
            _draw_tree(surf, tx, ty, seed=i * 37)

        # ── 5. Merchant buildings ─────────────────────────────────────────────
        for title, specialty, px, py in MERCHANT_SPECS:
            pal = _STALL[specialty]
            _draw_building(surf, px, py, pal, seed=hash(title), specialty=specialty)

        # ── 5b. Player house ──────────────────────────────────────────────────
        _draw_house(surf, HOUSE_POS[0], HOUSE_POS[1])

        # ── 6. Barrels and crates near buildings ─────────────────────────────
        rng = random.Random(77)
        for title, specialty, px, py in MERCHANT_SPECS:
            for _ in range(rng.randint(2, 3)):
                ox = px + rng.randint(-110, 110)
                oy = py + rng.randint(48, 82)
                if rng.random() < 0.5:
                    _draw_barrel(surf, ox - 11, oy - 15)
                else:
                    _draw_crate(surf, ox - 14, oy - 13)

        # ── 7. Dungeon entrance gate ──────────────────────────────────────────
        ex, ey = DUNGEON_ENTRANCE_POS
        _gate_drawn = False
        try:
            import pathlib
            _gp = pathlib.Path("assets/dungeon_entrance.png")
            if _gp.exists():
                _raw = pygame.image.load(str(_gp)).convert_alpha()
                _SZ  = 160
                _spr = pygame.transform.smoothscale(_raw, (_SZ, _SZ))
                surf.blit(_spr, (ex - _SZ // 2, ey - _SZ + 60))
                _gate_drawn = True
        except Exception:
            pass
        if not _gate_drawn:
            _draw_dungeon_gate(surf, ex, ey)

        # ── 8. DCSS decorations ───────────────────────────────────────────────
        try:
            from src.world.decorations import blit_town_decoration, _TOWN_STATUE_POOL, _TREE_VARIANTS, _FOUNTAIN_SPRITES
            import random as _rnd

            # Statues flanking dungeon entrance (left and right of gate columns)
            _gate_x, _gate_y = DUNGEON_ENTRANCE_POS
            for _sx, _sy, _statue in [
                (_gate_x - 76, _gate_y + 62, _TOWN_STATUE_POOL[0]),
                (_gate_x + 76, _gate_y + 62, _TOWN_STATUE_POOL[1]),
            ]:
                blit_town_decoration(surf, _statue, _sx, _sy, size=72, shadow=True)

            # DCSS fountain at plaza centre (drawn over procedural one)
            blit_town_decoration(surf, _FOUNTAIN_SPRITES[0], PLAZA_CX, PLAZA_CY,
                                 size=96, shadow=False)

            # DCSS trees at the same tree_positions used for procedural trees
            # Use a deterministic rng so the build is reproducible
            _trng = _rnd.Random(99)
            _dcss_tree_variants = [v for v in _TREE_VARIANTS if not v.startswith("trees/mangrove")]
            for _i, (_tx, _ty) in enumerate(tree_positions):
                _trel = _dcss_tree_variants[_i % len(_dcss_tree_variants)]
                blit_town_decoration(surf, _trel, _tx, _ty, size=80, shadow=True)

            # A few decorative statues near lower-area merchants (jeweler/alchemist)
            _extra_statues = [
                (650,  1170, _TOWN_STATUE_POOL[2]),
                (1300, 1170, _TOWN_STATUE_POOL[3]),
            ]
            for _sx, _sy, _srel in _extra_statues:
                blit_town_decoration(surf, _srel, _sx, _sy, size=64, shadow=True)
        except Exception:
            pass

        # ── 9. Wall torch sconces (static bracket; flame animated in draw()) ──
        torch_rng = random.Random(31)
        wall_torches = []
        ex_ = DUNGEON_ENTRANCE_POS[0]
        # Top wall — skip gate gap
        for wx in range(160, TOWN_W - 160, 190):
            if abs(wx - ex_) > 130:
                wall_torches.append((wx, B - 2))
        # Left / right walls
        for wy in range(140, TOWN_H - 140, 190):
            wall_torches.append((B - 2,          wy))
            wall_torches.append((TOWN_W - B + 2, wy))
        # Bottom wall
        for wx in range(160, TOWN_W - 160, 220):
            wall_torches.append((wx, TOWN_H - B + 2))

        for tx, ty in wall_torches:
            pygame.draw.rect(surf, _IR_DARK, (tx - 4, ty - 2, 8, 14))
            pygame.draw.rect(surf, _IR_MID,  (tx - 3, ty - 1, 6, 12))
            pygame.draw.line(surf, _IR_LGT,  (tx - 2, ty - 1), (tx - 2, ty + 10))
            pygame.draw.rect(surf, _WD_DARK, (tx - 2, ty + 2, 4, 8))
            pygame.draw.line(surf, _WD_LGT,  (tx - 1, ty + 2), (tx - 1, ty + 9))

        self._torch_positions = [(tx, ty - 4) for tx, ty in wall_torches]

        # Building torch positions (use module-level building dims)
        for title, specialty, px, py in MERCHANT_SPECS:
            bx = px - BUILDING_W // 2
            by = py - BUILDING_H // 2 - 20
            for side_x in [bx - 10, bx + BUILDING_W + 10]:
                self._torch_positions.append((side_x, by + 20))

        # House door torches
        _h_bw, _h_bh = 180, 128
        _h_door_w = 36
        _h_bx = HOUSE_POS[0] - _h_bw // 2
        _h_by = HOUSE_POS[1] - _h_bh // 2 - 15
        _h_door_y = _h_by + (_h_bh - 32) - 64
        _h_door_x = HOUSE_POS[0] - _h_door_w // 2
        for _tx in [_h_door_x - 14, _h_door_x + _h_door_w + 8]:
            self._torch_positions.append((_tx, _h_door_y - 4))

        self._torch_phases = [
            torch_rng.uniform(0, math.pi * 2)
            for _ in self._torch_positions
        ]

        self._bg = surf
        return surf

    # ── Public draw ───────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time: float,
             near_entrance: bool, near_house: bool = False,
             cam_x: int = 0, cam_y: int = 0):
        """Draw background + animated dungeon entrance portal and torches."""
        self._ensure_fonts()
        if self._bg is None:
            self._build_bg()
        surface.blit(self._bg, (-cam_x, -cam_y))

        sw = surface.get_width()
        sh = surface.get_height()

        # ── Animated torch flames ─────────────────────────────────────────────
        for (tx, ty), phase in zip(self._torch_positions, self._torch_phases):
            sx, sy = tx - cam_x, ty - cam_y
            if not (-20 <= sx <= sw + 20 and -20 <= sy <= sh + 20):
                continue
            flicker = 0.65 + 0.35 * math.sin(time * 9.4 + phase)
            r_ = int(6 + 4 * flicker)
            glow_s = pygame.Surface((r_ * 4, r_ * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 120, 20, int(40 * flicker)),
                               (r_ * 2, r_ * 2), r_ * 2)
            surface.blit(glow_s, (sx - r_ * 2, sy - r_ * 2))
            flame_s = pygame.Surface((r_ * 2 + 4, r_ * 2 + 4), pygame.SRCALPHA)
            col_inner = (255, int(180 + 60 * flicker), 20, int(200 * flicker))
            col_tip   = (255, 220, 80, int(160 * flicker))
            pygame.draw.circle(flame_s, col_inner, (r_ + 2, r_ + 2), r_)
            pygame.draw.circle(flame_s, col_tip,   (r_ + 2, r_ + 2), r_ // 2)
            surface.blit(flame_s, (sx - r_ - 2, sy - r_ - 2))

        # ── Animated portal glow inside the archway ───────────────────────────
        ex, ey   = DUNGEON_ENTRANCE_POS
        sex, sey = ex - cam_x, ey - cam_y
        pulse = 0.65 + 0.35 * math.sin(time * 2.8)
        glow  = (80, 30, 140) if near_entrance else (40, 12, 80)
        for r in range(34, 6, -5):
            a  = int(70 * pulse * (r / 34))
            gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*glow, a), (r, r), r)
            surface.blit(gs, (sex - r, sey + 12 - r))

        # ── House label and interaction hint ──────────────────────────────────
        hpx, hpy    = HOUSE_POS
        shx, shy    = hpx - cam_x, hpy - cam_y
        _h_bh = 128
        _h_by = shy - _h_bh // 2 - 15
        home_col = (220, 185, 80) if near_house else (160, 130, 55)
        home_lbl = self._font.render(t("town.your_home"), True, home_col)
        _blit_shadowed(surface, home_lbl,
                       home_lbl.get_rect(centerx=shx, centery=_h_by - 70).topleft)
        if near_house:
            _draw_interaction_badge(surface, self._font_sm,
                                     "[F]", t("town.enter_house"),
                                     shx, shy + 80, (220, 185, 80))

        # ── Stall names with drop shadows ─────────────────────────────────────
        for title, specialty, px, py in MERCHANT_SPECS:
            pal   = _STALL[specialty]
            spx   = px - cam_x
            spy   = py - cam_y
            display_name = t(f"merchant.{title.lower()}")
            name_s = self._font.render(display_name, True, pal["hi"])
            nrect  = name_s.get_rect(centerx=spx, centery=spy - 115)
            _blit_shadowed(surface, name_s, nrect.topleft, shadow_off=(2, 2))

        # ── Dungeon entrance sign with shadow ─────────────────────────────────
        lbl_col = (200, 160, 255) if near_entrance else (140, 100, 200)
        lbl   = self._font.render(t("town.dungeon_sign"), True, lbl_col)
        lrect = lbl.get_rect(centerx=sex, centery=sey - 66)
        _blit_shadowed(surface, lbl, lrect.topleft, shadow_off=(2, 2))

        if near_entrance:
            _draw_interaction_badge(surface, self._font_sm,
                                     "[E]", t("town.enter_dungeon"),
                                     sex, sey + 46, (180, 140, 255))

    def draw_return_notice(self, surface: pygame.Surface, msg: str):
        """Short-lived 'Rested' banner after returning from the dungeon."""
        self._ensure_fonts()
        cx = SCREEN_WIDTH // 2
        cy = (SCREEN_HEIGHT - HUD_HEIGHT) // 2 - 80
        s  = self._font.render(msg, True, (120, 240, 120))
        bg = pygame.Surface((s.get_width() + 24, s.get_height() + 10), pygame.SRCALPHA)
        bg.fill((0, 40, 0, 200))
        surface.blit(bg, bg.get_rect(center=(cx, cy)))
        _blit_shadowed(surface, s, s.get_rect(center=(cx, cy)).topleft)
